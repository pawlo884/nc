from importlib import import_module, reload
from celery import shared_task, chain
from celery.utils.log import get_task_logger
from django.db import connections, transaction
from matterhorn.defs_import import clean_update_log
from matterhorn.models import Products, OtherColors
from django.utils.timezone import now, timedelta
from django.core.cache import cache
from django.db import connection
from celery.exceptions import Ignore
from nc.celery import app

logger = get_task_logger(__name__)


def dynamic_import(module_name, function_name):
    """
    Dynamiczne importuje funkcję i danego modułu.
    """
    module = import_module(module_name)
    reload(module)
    return getattr(module, function_name)


@shared_task(name="run_import_all", rate_limit='1/s', queue='import_queue')
def run_import_all():
    logger.info("Rozpoczynam import...")
    import_all_by_one = dynamic_import('matterhorn.defs_import', 'import_all_by_one')
    for item in import_all_by_one():
        logger.info(f"Importuję: {item}")
    logger.info("Import zakończony.")
    return "Import zakończony."


@shared_task(name='run_update_inventory', rate_limit='1/s', time_limit=99590, soft_time_limit=99580, queue='import_queue')
def run_update_inventory(*args):
    logger.info("Rozpoczynam aktualizację...")
    update_inventory_v3 = dynamic_import('matterhorn.defs_import', 'update_inventory_v3')
    update_inventory_v3()
    logger.info("Aktualizacja zakończona.")
    return "Aktualizacja zakończona."


@shared_task(name='run_import_all_then_update_inventory', bind=True, queue='import_queue')
def run_import_all_then_update_inventory(self):
    logger.info(f"Task {self.request.id} rozpoczyna sprawdzanie stanu...")
    
    # Klucz dla blokady
    lock_id = 'import_and_update_lock'
    lock_timeout = 1800  # 30 minut
    
    # Próba uzyskania blokady
    acquired = cache.add(lock_id, self.request.id, lock_timeout)
    
    if not acquired:
        current_lock = cache.get(lock_id)
        logger.info(f"Zadanie jest już w trakcie wykonywania (lock: {current_lock}). Task {self.request.id} czeka.")
        raise self.retry(countdown=60, max_retries=30)

    try:
        logger.info(f"Task {self.request.id} rozpoczyna łańcuch zadań...")
        
        # Tworzymy łańcuch zadań z dodatkowym callbackiem do zwolnienia blokady
        task_chain = chain(
            run_import_all.si(),
            run_update_inventory.si(),
            release_lock.si(lock_id=lock_id, task_id=self.request.id)
        ).apply_async(queue='import_queue', link_error=release_lock.si(lock_id=lock_id, task_id=self.request.id))
        
        logger.info(f"Task {self.request.id} uruchomił łańcuch zadań z ID: {task_chain.id}")
        
        return {
            'chain_id': task_chain.id,
            'status': 'started',
            'task_id': self.request.id
        }
        
    except Exception as e:
        logger.error(f"Błąd podczas uruchamiania łańcucha zadań: {str(e)}")
        # W przypadku błędu zwalniamy blokadę
        if cache.get(lock_id) == self.request.id:
            cache.delete(lock_id)
        raise


@shared_task(name='release_lock', queue='import_queue')
def release_lock(lock_id, task_id):
    """
    Task do zwalniania blokady po zakończeniu łańcucha zadań.
    """
    logger.info(f"Próba zwolnienia blokady {lock_id} dla taska {task_id}")
    current_lock = cache.get(lock_id)
    
    if current_lock == task_id:
        cache.delete(lock_id)
        logger.info(f"Blokada {lock_id} została zwolniona przez task {task_id}")
        return True
    else:
        logger.warning(f"Nie można zwolnić blokady {lock_id} - należy do innego taska (current: {current_lock}, requested: {task_id})")
        return False


@shared_task(name='matterhorn.tasks.run_clean_update_log')
def run_clean_update_log():
    """
    Zadanie Celery do czyszczenia logu aktualizacji.
    """
    result = clean_update_log()
    return result


@shared_task(name='update_is_mapped_status')
def update_is_mapped_status():
    """
    Aktualizuje `is_mapped` dla produktów, które zmieniły się w ciągu ostatniej godziny.
    Jeśli produkt ma `mapped_product_id`, uznajemy go za poprawnie zmapowany.
    Jeśli produkt ma `other_colors`, to `is_mapped = True` tylko, jeśli wszystkie `other_colors` mają `mapped_product_id`.
    """
    print("Celery task: Aktualizacja `is_mapped` rozpoczęta...")

    time_threshold = now() - timedelta(hours=1)  # Pobieramy tylko zmiany z ostatniej godziny
    products = Products.objects.filter(last_updated__gte=time_threshold)

    if not products.exists():
        print("Brak produktów do aktualizacji.")
        return

    updated_count = 0

    for product in products:
        all_mapped = False  # Domyślnie produkt nie jest zmapowany

        # **DEBUG: Sprawdzamy wartości mapped_product_id**
        print(f"🔍 Produkt ID={product.id}, mapped_product_id={product.mapped_product_id}, is_mapped={product.is_mapped}")

        # **Jeśli produkt ma mapped_product_id i nie ma other_colors, uznajemy go za zmapowany**
        if product.mapped_product_id and isinstance(product.mapped_product_id, int) and product.mapped_product_id > 0:
            print(f"✅ Produkt {product.id} ma poprawny mapped_product_id ({product.mapped_product_id}), ustawiamy is_mapped = True")
            all_mapped = True

        # **Jeśli produkt ma other_colors, wszystkie muszą być zmapowane, aby is_mapped = True**
        other_colors = OtherColors.objects.filter(product=product)

        if other_colors.exists():
            print(f"🔍 Produkt {product.id} ma powiązane kolory. Sprawdzamy ich mapped_product_id...")
            product_ids = {
                color.color_product.id for color in other_colors 
                if color.color_product and color.color_product.id != product.id
            }

            if product_ids:
                # **Jeśli choć jeden powiązany produkt nie ma mapped_product_id, to is_mapped = False**
                all_mapped = all(
                    Products.objects.filter(id=prod_id, mapped_product_id__isnull=False).exists()
                    for prod_id in product_ids
                )

                if all_mapped:
                    print(f"✅ Wszystkie powiązane produkty dla {product.id} są zmapowane. Ustawiamy is_mapped = True")
                else:
                    print(f"❌ Nie wszystkie powiązane produkty dla {product.id} są zmapowane. Ustawiamy is_mapped = False")

        # **Aktualizujemy `is_mapped` tylko jeśli wartość się zmieniła**
        if product.is_mapped != all_mapped:
            print(f"🔄 Aktualizacja: Produkt {product.id} zmienia is_mapped z {product.is_mapped} na {all_mapped}")
            product.is_mapped = all_mapped
            product.save(update_fields=['is_mapped'])
            updated_count += 1
        else:
            print(f"✅ Produkt {product.id} nie wymaga zmiany (is_mapped={product.is_mapped})")

    print(f"✅ Celery task zakończony. Zaktualizowano {updated_count} rekordów.")


@shared_task(name='update_stock_from_matterhorn')
def update_stock_matterhorn():
    """
    Aktualizuje stock z Matterhorn
    """
    try:
        # Ustawienie czasu (ostatnie 8 minut)
        threshold_time = now() - timedelta(minutes=8)

        with connections['matterhorn'].cursor() as source_cursor, connections['MasterProductDatabase'].cursor() as destination_cursor:
            # Pobranie zmienionych stanów magazynowych z matterhorn
            source_cursor.execute(
                """
                SELECT variant_uid, stock
                FROM variants
                WHERE last_updated >= %s
                """, [threshold_time])

            variants = source_cursor.fetchall()

            if not variants:
                return "Brak zmian w stanie magazynowym"

            # Mapa variant_uid --> stock
            stock_map = {variant[0]: variant[1] for variant in variants}

            # Pobranie odpowiadających variant_id z MasterProductDatabase
            variants_uids = tuple(stock_map.keys())
            destination_cursor.execute(
                """
                SELECT variant_id, variant_uid
                FROM product_variants
                WHERE variant_uid IN %s
                """, [variants_uids])

            variant_mapping = {row[1]: row[0] for row in destination_cursor.fetchall()}  # Mapa variant_uid --> variant_id

            # Aktualizacja stock w 'stock_and_prices'
            updates = [(stock_map[uid], variant_mapping[uid]) for uid in variant_mapping if uid in stock_map]

            if updates:
                with transaction.atomic(using='MasterProductDatabase'):
                    destination_cursor.executemany(
                        """
                        UPDATE stock_and_prices
                        SET stock = %s
                        WHERE variant_id = %s
                        """, updates)

        return f"Zaktualizowano {len(updates)} rekordów."
    except Exception as e:
        return f"Błąd w update_stock: {str(e)}"


@shared_task(name='check_queue_status')
def check_queue_status():
    """
    Sprawdza stan kolejek i zadań.
    """
    inspector = app.control.inspect()
    
    # Sprawdź aktywne zadania
    active = inspector.active()
    logger.info("Aktywne zadania:")
    if active:
        for worker, tasks in active.items():
            for task in tasks:
                logger.info(f"Worker: {worker}, Task: {task['name']}, ID: {task['id']}")
    else:
        logger.info("Brak aktywnych zadań")
    
    # Sprawdź zadania w kolejce
    reserved = inspector.reserved()
    logger.info("\nZadania w kolejce:")
    if reserved:
        for worker, tasks in reserved.items():
            for task in tasks:
                logger.info(f"Worker: {worker}, Task: {task['name']}, ID: {task['id']}")
    else:
        logger.info("Brak zadań w kolejce")
    
    # Sprawdź zaplanowane zadania
    scheduled = inspector.scheduled()
    logger.info("\nZaplanowane zadania:")
    if scheduled:
        for worker, tasks in scheduled.items():
            for task in tasks:
                logger.info(f"Worker: {worker}, Task: {task['name']}, ID: {task['id']}")
    else:
        logger.info("Brak zaplanowanych zadań")
    
    return {
        'active': active,
        'reserved': reserved,
        'scheduled': scheduled
    }