import time
from celery import shared_task
from celery.utils.log import get_task_logger
from django.conf import settings
from django.core.cache import cache
from .stock_tracker import track_stock_change, track_bulk_stock_changes, sync_stock_changes_from_api

logger = get_task_logger(__name__)


@shared_task(bind=True, name='matterhorn1.tasks.full_import_and_update', queue='import')
def full_import_and_update(self, start_id=None, max_products=200000,
                           api_url=None, username=None, password=None,
                           batch_size=100, dry_run=False, auto_continue=True):
    """
    GŁÓWNY Celery task - import produktów z ITEMS + aktualizacja INVENTORY

    Logika:
    1. Importuje produkty z ITEMS (od ostatniego ID lub podanego start_id)
    2. Po zakończeniu importu ITEMS automatycznie uruchamia aktualizację INVENTORY
    3. Jeśli auto_continue=True, kontynuuje import aż skończą się produkty

    Args:
        start_id: ID produktu od którego rozpocząć import (domyślnie ostatni w bazie)
        max_products: Maksymalna liczba produktów na jedną iterację
        api_url: URL API Matterhorn
        username: Nazwa użytkownika API
        password: Hasło API
        batch_size: Rozmiar batcha
        dry_run: Tryb testowy
        auto_continue: Kontynuuj import aż skończą się produkty
    """
    # SPRAWDŹ DOSTĘPNOŚĆ BAZY DANYCH PRZED ROZPOCZĘCIEM
    if not _check_database_connection():
        logger.error("❌ Baza danych nie jest dostępna - przerywam import")
        return {
            'status': 'error',
            'error': 'Database connection failed - cannot start import',
            'task_id': getattr(getattr(self, 'request', None), 'id', 'direct_call')
        }

    # BLOKADA - zapobiega równoległemu wykonaniu (działa dla Celery i bezpośrednich wywołań)
    lock_id = 'matterhorn1_full_import_lock'
    lock_timeout = 3600  # 1 godzina

    # Użyj task_id jeśli dostępny (Celery), w przeciwnym razie 'direct_call'
    task_identifier = getattr(self, 'request', None)
    task_id_value = task_identifier.id if task_identifier else 'direct_call'

    # CZYŚĆ STARE RUNNING REKORDY (starsze niż 2 godziny)
    _cleanup_old_running_imports()

    # CZYŚĆ WSZYSTKIE RUNNING REKORDY (rozwiązuje problem z ręcznym przerywaniem)
    _cleanup_all_running_imports()

    # ATOMOWA OPERACJA BLOKADY - zapobiega race condition
    # Sprawdź czy blokada istnieje i ustaw ją w jednej operacji
    acquired = cache.add(lock_id, task_id_value, lock_timeout)

    if not acquired:
        current_lock = cache.get(lock_id)
        logger.warning(
            f"❌ Import już w trakcie wykonywania (lock: {current_lock}). Pominięty.")
        return {
            'status': 'skipped',
            'reason': 'already_running',
            'current_lock': current_lock,
            'task_id': task_id_value
        }

    task_completed_successfully = False
    total_imported = 0
    total_updated = 0
    iteration = 0

    try:
        logger.info(
            f"🚀 ROZPOCZYNAM PEŁNY IMPORT I AKTUALIZACJĘ (task_id: {task_id_value})")
        logger.info(
            f"📊 Parametry: start_id={start_id}, max_products={max_products}, api_url={api_url}")

        # Pobierz parametry z settings jeśli nie podano
        if not api_url:
            api_url = getattr(settings, 'MATTERHORN_API_URL',
                              'https://matterhorn.pl')
        if not username:
            username = getattr(settings, 'MATTERHORN_API_USERNAME', '')
        if not password:
            password = getattr(settings, 'MATTERHORN_API_PASSWORD', '')

        while True:
            iteration += 1
            logger.info(f"🔄 ITERACJA {iteration} - Import produktów z ITEMS")

            # KROK 1: Import produktów z ITEMS
            items_result = _import_products_from_items(
                start_id=start_id,
                max_products=max_products,
                api_url=api_url,
                username=username,
                password=password,
                batch_size=batch_size,
                dry_run=dry_run
            )

            # Aktualizuj total_imported PRZED sprawdzeniem statusu
            imported_count = items_result.get('imported_count', 0)
            total_imported += imported_count

            if items_result['status'] == 'completed':
                logger.info(
                    f"✅ Import ITEMS zakończony - {items_result.get('reason')}")
                # Wykonaj ostatnią aktualizację INVENTORY przed zakończeniem
                logger.info(
                    f"🔄 ITERACJA {iteration} - Ostatnia aktualizacja INVENTORY")

                inventory_result = _update_inventory_from_api(
                    api_url=api_url,
                    username=username,
                    password=password,
                    batch_size=batch_size,
                    dry_run=dry_run
                )

                if inventory_result['status'] == 'success':
                    updated_count = inventory_result.get('updated_count', 0)
                    total_updated += updated_count
                    logger.info(
                        f"✅ Iteracja {iteration} - Zaktualizowano {updated_count} produktów w INVENTORY")
                else:
                    logger.warning(
                        f"⚠️ Błąd aktualizacji INVENTORY w iteracji {iteration}: {inventory_result.get('error')}")
                break
            elif items_result['status'] != 'success':
                logger.error(
                    f"❌ Błąd importu ITEMS w iteracji {iteration}: {items_result.get('error')}")
                break

            logger.info(
                f"✅ Iteracja {iteration} - Zaimportowano {imported_count} produktów")

            # KROK 2: Aktualizacja INVENTORY - ITEMS API nie pokazuje stanów 0, więc INVENTORY musi je zaktualizować
            logger.info(f"🔄 ITERACJA {iteration} - Aktualizacja INVENTORY")

            inventory_result = _update_inventory_from_api(
                api_url=api_url,
                username=username,
                password=password,
                batch_size=batch_size,
                dry_run=dry_run
            )

            if inventory_result['status'] == 'success':
                updated_count = inventory_result.get('updated_count', 0)
                total_updated += updated_count
                logger.info(
                    f"✅ Iteracja {iteration} - Zaktualizowano {updated_count} produktów w INVENTORY")
            else:
                logger.warning(
                    f"⚠️ Błąd aktualizacji INVENTORY w iteracji {iteration}: {inventory_result.get('error')}")

            # Jeśli nie zaimportowano żadnych produktów, zakończ po aktualizacji INVENTORY
            if imported_count == 0:
                logger.info(
                    "📊 Brak nowych produktów do importu - kończę import ITEMS")
                break

            # Jeśli nie ma auto_continue, zakończ po pierwszej iteracji
            if not auto_continue:
                logger.info(
                    "📊 Auto-continue wyłączone - kończę po pierwszej iteracji")
                break

            # Kontynuuj import od następnej strony
            # (start_id nie jest już potrzebny bo używamy page)

            # Sprawdź czy nie przekraczamy maksymalnej liczby iteracji
            if iteration >= 100:  # Bezpiecznik
                logger.warning(
                    "⚠️ Osiągnięto maksymalną liczbę iteracji (100) - kończę")
                break

            logger.info("🎉 PEŁNY IMPORT ZAKOŃCZONY!")
            logger.info("📊 Łącznie zaimportowano: %s produktów",
                        total_imported)
            logger.info(
                "📊 Łącznie zaktualizowano: %s produktów w INVENTORY", total_updated)

        task_completed_successfully = True

        return {
            'status': 'success',
            'total_imported': total_imported,
            'total_updated': total_updated,
            'iterations': iteration,
            'task_id': task_id_value
        }

    except Exception as e:
        logger.error(f"❌ Błąd pełnego importu: {e}")
        # 5 minut przerwy, max 2 retry
        self.retry(countdown=300, max_retries=2)
        return {
            'status': 'error',
            'error': str(e),
            'task_id': task_id_value
        }

    finally:
        # Zawsze zwalniaj blokadę i zaktualizuj status
        if cache.get(lock_id) == task_id_value:
            cache.delete(lock_id)
            logger.info(f"🔓 Blokada zwolniona dla {task_id_value}")

        # Aktualizuj status na podstawie tego czy task się zakończył sukcesem
        try:
            if task_completed_successfully:
                _update_items_import_status(
                    'completed', total_imported, updated_count=total_updated, processed_count=total_imported + total_updated)
                logger.info("✅ Task zakończony jako 'completed'")
            else:
                _update_items_import_status(
                    'error', total_imported, updated_count=total_updated, processed_count=total_imported + total_updated)
                logger.info("❌ Task zakończony jako 'error'")
        except Exception as e:
            logger.error(f"❌ Błąd podczas aktualizacji statusu na końcu: {e}")


def _import_products_from_items(start_id, max_products, api_url, username, password, batch_size, dry_run):
    """Pomocnicza funkcja do importu produktów z ITEMS używając last_update"""
    try:
        # Pobierz ostatni czas importu lub użyj domyślnego
        last_update = _get_last_items_update_time()

        # Jeśli nie można pobrać daty ostatniego importu, przerwij
        if last_update is None:
            logger.error(
                "❌ Nie można pobrać daty ostatniego importu - przerywam import")
            return {
                'status': 'error',
                'error': 'Cannot get last import date - database unavailable'
            }

        logger.info(f"📅 Używam last_update: {last_update}")

        # Pobierz ostatnią stronę z przerwanego importu
        start_page = _get_last_items_page()
        logger.info(f"🔄 Kontynuuję od strony: {start_page}")

        # WAŻNE: Zapisz czas ROZPOCZĘCIA importu PRZED rozpoczęciem
        if not dry_run:
            _save_items_import_start_time()

        # Użyj bulk API z last_update
        imported_count = 0
        page = start_page
        limit = 1000  # Limit 1000 dla importu ITEMS

        logger.info(f"🔍 Używam bulk API ITEMS z last_update i limit={limit}")

        while imported_count < max_products:
            max_attempts = 10
            attempt = 1

            while attempt <= max_attempts:
                try:
                    # Pobierz dane uwierzytelniające
                    from django.conf import settings
                    import requests
                    api_key = getattr(settings, 'MATTERHORN_API_KEY', '')
                    if not api_key:
                        api_key = f"{username}:{password}"

                    headers = {
                        "Content-Type": "application/json",
                        "Authorization": api_key
                    }

                    # Użyj bulk API z last_update
                    url = f"{api_url}/B2BAPI/ITEMS/?page={page}&limit={limit}&last_update={last_update}"
                    logger.info(f"🔗 Request URL: {url}")
                    # Zwiększony timeout do 120s
                    response = requests.get(url, headers=headers, timeout=120)
                    time.sleep(1.0)  # Ograniczenie API: 1 request/sekundę

                    logger.info(
                        f"🔍 Bulk API Response strona {page}: status={response.status_code}, content_length={len(response.text)}")

                    if response.status_code == 200:
                        if not response.text.strip():
                            logger.info("📊 Pusta odpowiedź - koniec danych")
                            return {
                                'status': 'completed',
                                'imported_count': imported_count,
                                'reason': 'empty_response'
                            }

                        try:
                            items = response.json()
                            if not items:
                                logger.info(
                                    "📊 Brak produktów na stronie - koniec danych")
                                return {
                                    'status': 'completed',
                                    'imported_count': imported_count,
                                    'reason': 'no_more_products'
                                }

                            logger.info(
                                f"📥 Pobrano {len(items)} produktów ze strony {page}")

                            # Bulk import/update
                            if not dry_run:
                                bulk_result = _bulk_import_products(items)
                                imported_count += bulk_result['imported_count']
                            else:
                                # Dry run - tylko zlicz
                                for item in items:
                                    if imported_count >= max_products:
                                        break
                                    if item.get("creation_date") is not None:
                                        imported_count += 1

                            page += 1
                            # Aktualizuj current_page w bazie danych
                            if not dry_run:
                                _update_items_import_status(
                                    'running', imported_count, page, updated_count=bulk_result.get('updated_count', 0), processed_count=imported_count)
                            break  # Sukces - wyjdź z retry loop

                        except Exception as e:
                            logger.error(f"❌ Błąd parsowania JSON: {e}")
                            if attempt < max_attempts:
                                logger.warning(
                                    f"⚠️ Próba {attempt}/{max_attempts} - ponawiam za 20 sekund...")
                                time.sleep(20)
                                attempt += 1
                                continue
                            else:
                                logger.error(
                                    "❌ Osiągnięto maksymalną liczbę prób parsowania JSON")
                                break

                    elif response.status_code == 404:
                        logger.info("📊 Strona nie istnieje - koniec danych")
                        break
                    else:
                        logger.warning(f"⚠️ Błąd API {response.status_code}")
                        if attempt < max_attempts:
                            logger.warning(
                                f"⚠️ Próba {attempt}/{max_attempts} - ponawiam za 20 sekund...")
                            time.sleep(20)
                            attempt += 1
                            continue
                        else:
                            logger.error(
                                "❌ Osiągnięto maksymalną liczbę prób API")
                            break

                except Exception as e:
                    logger.error(
                        f"❌ Błąd podczas pobierania strony {page}: {e}")
                    logger.error(f"❌ Typ błędu: {type(e).__name__}")
                    if "timeout" in str(e).lower():
                        logger.warning(
                            f"⚠️ Timeout - API może być wolne, zwiększam timeout")
                    if attempt < max_attempts:
                        logger.warning(
                            f"⚠️ Próba {attempt}/{max_attempts} - ponawiam za 20 sekund...")
                        time.sleep(20)
                        attempt += 1
                        continue
                    else:
                        logger.error(
                            "❌ Osiągnięto maksymalną liczbę prób połączenia")
                        break

            # Jeśli osiągnięto maksymalną liczbę prób, przerwij główną pętlę
            if attempt > max_attempts:
                break

        # Zaktualizuj status importu na 'success' po zakończeniu
        if not dry_run:
            _update_items_import_status(
                'success', imported_count, updated_count=0, processed_count=imported_count)

        logger.info(
            f"📊 Import zakończony: {imported_count} nowych produktów")

        return {
            'status': 'success',
            'imported_count': imported_count
        }

    except Exception as e:
        logger.error(f"❌ Błąd importu ITEMS: {e}")
        # Zaktualizuj status na 'error' jeśli nie dry_run
        if not dry_run:
            _update_items_import_status('error', 0)
        return {
            'status': 'error',
            'error': str(e)
        }


def _check_database_connection():
    """Sprawdza czy baza danych jest dostępna"""
    max_retries = 3
    retry_delay = 5  # 5 sekund między próbami

    for attempt in range(max_retries):
        try:
            from django.db import connection
            from matterhorn1.models import ApiSyncLog

            # Sprawdź połączenie z bazą danych
            connection.ensure_connection()

            # Spróbuj wykonać prostą kwerendę
            ApiSyncLog.objects.using('matterhorn1').exists()

            logger.info("✅ Połączenie z bazą danych działa poprawnie")
            return True

        except Exception as e:
            logger.error(
                f"❌ Błąd połączenia z bazą danych (próba {attempt + 1}/{max_retries}): {e}")

            if attempt < max_retries - 1:
                logger.warning(
                    f"⏳ Czekam {retry_delay} sekund przed ponowną próbą...")
                time.sleep(retry_delay)
            else:
                logger.error(
                    "❌ Baza danych nie jest dostępna po wszystkich próbach")
                return False

    return False


def _get_last_items_update_time():
    """Pobiera ostatni czas importu ITEMS z retry logic lub zwraca None jeśli baza niedostępna"""
    max_retries = 3
    retry_delay = 10  # 10 sekund między próbami

    for attempt in range(max_retries):
        try:
            from matterhorn1.models import ApiSyncLog
            import pytz

            last_sync = ApiSyncLog.objects.using('matterhorn1').filter(
                sync_type__in=['items_import', 'items_sync'],
                status__in=['success', 'partial', 'completed']
            ).order_by('-started_at').first()

            if last_sync and last_sync.started_at:
                # Konwertuj na strefę czasową Polski (UTC+1/UTC+2)
                poland_tz = pytz.timezone('Europe/Warsaw')
                if last_sync.started_at.tzinfo is None:
                    # Jeśli data jest naive, załóż że to UTC
                    utc_dt = pytz.utc.localize(last_sync.started_at)
                else:
                    utc_dt = last_sync.started_at.astimezone(pytz.utc)

                # Konwertuj na strefę czasową Polski
                poland_dt = utc_dt.astimezone(poland_tz)
                logger.info(
                    f"✅ Pobrano last_update z bazy danych: {poland_dt.strftime('%Y-%m-%d %H:%M:%S')}")
                return poland_dt.strftime("%Y-%m-%d %H:%M:%S")
            else:
                # Brak poprzednich importów - zwróć None zamiast 2015-01-01
                logger.info(
                    "📅 Brak poprzednich importów - nie można określić daty startu")
                return None

        except Exception as e:
            logger.error(
                f"❌ Błąd podczas pobierania ostatniego czasu importu ITEMS (próba {attempt + 1}/{max_retries}): {e}")

            if attempt < max_retries - 1:
                logger.warning(
                    f"⏳ Czekam {retry_delay} sekund przed ponowną próbą połączenia z bazą danych...")
                time.sleep(retry_delay)
            else:
                logger.error(
                    "❌ Osiągnięto maksymalną liczbę prób połączenia z bazą danych")
                logger.error(
                    "❌ Nie można pobrać daty ostatniego importu - przerywam import")
                return None


def _get_last_items_page():
    """Zawsze zaczyna od strony 1 - każdy task zaczyna od początku z last_update"""
    try:
        logger.info(
            "📄 Zaczynam od strony 1 - każdy task zaczyna od początku z last_update")
        return 1
    except Exception as e:
        logger.error(f"Błąd podczas pobierania ostatniej strony: {e}")
        return 1


def _save_items_import_start_time():
    """Zapisuje czas ROZPOCZĘCIA importu ITEMS - to będzie last_update dla następnego importu"""
    max_retries = 5
    retry_delay = 10  # 10 sekund między próbami

    for attempt in range(max_retries):
        try:
            from matterhorn1.models import ApiSyncLog
            from django.utils import timezone

            # Zapisz log rozpoczęcia importu ITEMS
            ApiSyncLog.objects.using('matterhorn1').create(
                sync_type='items_import',
                status='running',  # Status 'running' podczas importu
                started_at=timezone.now(),
                completed_at=None,  # Będzie ustawione po zakończeniu
                records_processed=0,
                records_created=0,
                records_updated=0,
                records_errors=0,
                current_page=1  # Rozpoczynamy od strony 1
            )
            logger.info("✅ Zapisano czas ROZPOCZĘCIA importu ITEMS")
            return  # Sukces - wyjdź z funkcji

        except Exception as e:
            logger.error(
                f"❌ Błąd podczas zapisywania czasu rozpoczęcia importu ITEMS (próba {attempt + 1}/{max_retries}): {e}")

            if attempt < max_retries - 1:
                logger.warning(
                    f"⏳ Czekam {retry_delay} sekund przed ponowną próbą...")
                time.sleep(retry_delay)
            else:
                logger.error(
                    "❌ Osiągnięto maksymalną liczbę prób zapisywania czasu rozpoczęcia importu")


def _update_items_import_status(status, imported_count, current_page=None, updated_count=0, processed_count=0):
    """Aktualizuje status ostatniego importu ITEMS z retry logic"""
    max_retries = 5
    retry_delay = 10  # 10 sekund między próbami

    for attempt in range(max_retries):
        try:
            from matterhorn1.models import ApiSyncLog
            from django.utils import timezone

            # Znajdź ostatni rekord z statusem 'running'
            last_running = ApiSyncLog.objects.using('matterhorn1').filter(
                sync_type='items_import',
                status='running'
            ).order_by('-started_at').first()

            if last_running:
                # Aktualizuj status i completed_at
                last_running.status = status
                last_running.completed_at = timezone.now()
                last_running.records_created = imported_count
                last_running.records_updated = updated_count
                last_running.records_processed = processed_count

                # Aktualizuj current_page jeśli podane
                if current_page is not None:
                    last_running.current_page = current_page

                last_running.save()
                logger.info(
                    f"✅ Zaktualizowano status importu ITEMS na: {status}")
            else:
                logger.warning(
                    "⚠️ Nie znaleziono rekordu 'running' do aktualizacji")

            return  # Sukces - wyjdź z funkcji

        except Exception as e:
            logger.error(
                f"❌ Błąd podczas aktualizacji statusu importu ITEMS (próba {attempt + 1}/{max_retries}): {e}")

            if attempt < max_retries - 1:
                logger.warning(
                    f"⏳ Czekam {retry_delay} sekund przed ponowną próbą...")
                time.sleep(retry_delay)
            else:
                logger.error(
                    "❌ Osiągnięto maksymalną liczbę prób aktualizacji statusu importu")


def _save_last_items_update_time():
    """Zapisuje czas ostatniego importu ITEMS"""
    try:
        from matterhorn1.models import ApiSyncLog
        from django.utils import timezone

        # Zapisz log importu ITEMS
        ApiSyncLog.objects.using('matterhorn1').create(
            sync_type='items_import',
            status='success',
            started_at=timezone.now(),
            completed_at=timezone.now(),
            records_processed=0,
            records_created=0,
            records_updated=0,
            records_errors=0
        )
        logger.info("✅ Zapisano czas ostatniego importu ITEMS")
    except Exception as e:
        logger.error(f"Błąd podczas zapisywania czasu importu ITEMS: {e}")


def _parse_creation_date(date_string):
    """Parsuje datę z API i konwertuje na timezone-aware datetime"""
    if not date_string:
        return None

    from django.utils.dateparse import parse_datetime
    from django.utils import timezone
    import pytz

    # Parsuj datę z API
    parsed_date = parse_datetime(date_string)
    if parsed_date:
        # Jeśli data nie ma strefy czasowej, dodaj UTC
        if timezone.is_naive(parsed_date):
            parsed_date = timezone.make_aware(parsed_date, pytz.UTC)
        return parsed_date
    return None


def _bulk_import_products(items):
    """Bulk import/update produktów"""
    try:
        from matterhorn1.models import Product, Brand, Category, ProductVariant, ProductImage, ProductDetails
        from django.utils import timezone
        from django.db import transaction

        imported_count = 0

        # Przygotuj dane do bulk operations
        products_to_create = []
        products_to_update = []

        # Najpierw przygotuj wszystkie dane
        for item in items:
            if item.get("creation_date") is None:
                continue

            product_uid = item.get('id')
            if not product_uid:
                continue

            # Sprawdź czy produkt istnieje - użyj get_or_create dla bezpieczeństwa
            try:
                existing_product = Product.objects.using(
                    'matterhorn1').get(product_uid=int(product_uid))
                # Aktualizuj istniejący
                _prepare_product_update(existing_product, item)
                products_to_update.append(existing_product)
            except Product.DoesNotExist:
                # Utwórz nowy
                product_data = _prepare_product_create(item)
                products_to_create.append(product_data)

            imported_count += 1

        # Bulk operations w transakcji
        with transaction.atomic(using='matterhorn1'):
            # Utwórz nowe produkty
            if products_to_create:
                # Sprawdź które produkty już istnieją
                existing_product_uids = set(Product.objects.using('matterhorn1').filter(
                    product_uid__in=[p.product_uid for p in products_to_create]
                ).values_list('product_uid', flat=True))

                # Filtruj tylko nowe produkty
                new_products = [
                    p for p in products_to_create if p.product_uid not in existing_product_uids]

                if new_products:
                    Product.objects.using('matterhorn1').bulk_create(
                        new_products, batch_size=100)
                    logger.info(
                        f"✅ Utworzono {len(new_products)} nowych produktów")

                    # Pobierz utworzone produkty z bazy (z id)
                    created_product_uids = [
                        p.product_uid for p in new_products]
                    created_products = list(Product.objects.using('matterhorn1').filter(
                        product_uid__in=created_product_uids))

                    # Użyj oryginalnych obiektów (z atrybutami) do tworzenia powiązanych obiektów
                    _create_related_objects_for_products(new_products)
                else:
                    logger.info(
                        "✅ Wszystkie produkty już istnieją - pominięto tworzenie")

            # Aktualizuj istniejące produkty
            if products_to_update:
                Product.objects.using('matterhorn1').bulk_update(
                    products_to_update,
                    ['active', 'name', 'description', 'creation_date', 'color', 'url',
                     'new_collection', 'brand', 'category', 'prices', 'products_in_set',
                     'other_colors', 'last_api_sync'],
                    batch_size=100
                )
                logger.info(
                    f"🔄 Zaktualizowano {len(products_to_update)} produktów")

                # Utwórz/aktualizuj warianty, obrazy i szczegóły dla zaktualizowanych produktów
                _create_related_objects_for_products(products_to_update)

        return {
            'imported_count': imported_count
        }

    except Exception as e:
        logger.error(f"❌ Błąd bulk import: {e}")
        # Nie ma fallback - tylko bulk operations
        return {
            'imported_count': 0
        }


def _create_related_objects_for_products(products):
    """Utwórz warianty, obrazy i szczegóły dla produktów"""
    try:
        logger.info(
            f"🚀 ROZPOCZYNAM _create_related_objects_for_products dla {len(products)} produktów")
        from matterhorn1.models import ProductVariant, ProductImage, ProductDetails

        variants_to_create = []
        variants_to_update = []
        images_to_create = []
        details_to_create = []
        details_to_update = []

        for product in products:
            if hasattr(product, '_variants_to_create') and product._variants_to_create:
                for variant_data in product._variants_to_create:
                    variant_uid = variant_data.get('variant_uid')
                    if not variant_uid:
                        continue

                    try:
                        # Sprawdź czy wariant istnieje
                        existing_variant = ProductVariant.objects.using('matterhorn1').get(
                            variant_uid=variant_uid)
                        # Aktualizuj istniejący
                        existing_variant.name = variant_data.get(
                            'name', existing_variant.name)
                        existing_variant.stock = variant_data.get(
                            'stock', existing_variant.stock)
                        existing_variant.max_processing_time = variant_data.get(
                            'max_processing_time', existing_variant.max_processing_time)
                        existing_variant.ean = variant_data.get(
                            'ean', existing_variant.ean)
                        variants_to_update.append(existing_variant)
                    except ProductVariant.DoesNotExist:
                        # Utwórz nowy
                        variants_to_create.append(ProductVariant(
                            variant_uid=variant_uid,
                            product=product,
                            name=variant_data.get('name', 'Unknown'),
                            stock=variant_data.get('stock', 0),
                            max_processing_time=variant_data.get(
                                'max_processing_time', 0),
                            ean=variant_data.get('ean', '')
                        ))

            # Obsługa obrazków
            if hasattr(product, '_images_to_create') and product._images_to_create:
                for image_data in product._images_to_create:
                    images_to_create.append(ProductImage(
                        product=product,
                        image_url=image_data.get('image_url'),
                        order=image_data.get('order', 0)
                    ))

            # Obsługa szczegółów produktu
            if hasattr(product, '_details_to_create') and product._details_to_create:
                details_data = product._details_to_create
                try:
                    # Sprawdź czy szczegóły istnieją
                    existing_details = ProductDetails.objects.using('matterhorn1').get(
                        product=product)
                    # Aktualizuj istniejące
                    existing_details.weight = details_data.get(
                        'weight', existing_details.weight)
                    existing_details.size_table = details_data.get(
                        'size_table', existing_details.size_table)
                    existing_details.size_table_txt = details_data.get(
                        'size_table_txt', existing_details.size_table_txt)
                    existing_details.size_table_html = details_data.get(
                        'size_table_html', existing_details.size_table_html)
                    details_to_update.append(existing_details)
                except ProductDetails.DoesNotExist:
                    # Utwórz nowe
                    details_to_create.append(ProductDetails(
                        product=product,
                        weight=details_data.get('weight') or None,
                        size_table=details_data.get('size_table') or None,
                        size_table_txt=details_data.get(
                            'size_table_txt') or None,
                        size_table_html=details_data.get(
                            'size_table_html') or None
                    ))

        # Bulk operations dla wariantów
        if variants_to_create:
            ProductVariant.objects.using('matterhorn1').bulk_create(
                variants_to_create, batch_size=100)
            logger.info(
                f"✅ Utworzono {len(variants_to_create)} nowych wariantów")

        if variants_to_update:
            ProductVariant.objects.using('matterhorn1').bulk_update(
                variants_to_update,
                ['name', 'stock', 'max_processing_time', 'ean'],
                batch_size=100
            )
            logger.info(
                f"🔄 Zaktualizowano {len(variants_to_update)} wariantów")

        # Bulk operations dla obrazków - sprawdź duplikaty
        if images_to_create:
            # Filtruj duplikaty - sprawdź które obrazki już istnieją
            unique_images_to_create = []
            for image in images_to_create:
                # Sprawdź czy obrazek już istnieje (product + image_url)
                image_exists = ProductImage.objects.using('matterhorn1').filter(
                    product=image.product,
                    image_url=image.image_url
                ).exists()

                if not image_exists:
                    unique_images_to_create.append(image)

            if unique_images_to_create:
                ProductImage.objects.using('matterhorn1').bulk_create(
                    unique_images_to_create, batch_size=100)
                logger.info(
                    f"✅ Utworzono {len(unique_images_to_create)} nowych obrazków (pominięto {len(images_to_create) - len(unique_images_to_create)} duplikatów)")
            else:
                logger.info(
                    f"ℹ️ Wszystkie {len(images_to_create)} obrazków już istnieją - pominięto")

        # Bulk operations dla szczegółów
        if details_to_create:
            ProductDetails.objects.using('matterhorn1').bulk_create(
                details_to_create, batch_size=100)
            logger.info(
                f"✅ Utworzono {len(details_to_create)} nowych szczegółów")

        if details_to_update:
            ProductDetails.objects.using('matterhorn1').bulk_update(
                details_to_update,
                ['weight', 'size_table', 'size_table_txt', 'size_table_html'],
                batch_size=100
            )
            logger.info(
                f"🔄 Zaktualizowano {len(details_to_update)} szczegółów")

    except Exception as e:
        logger.error(f"❌ Błąd tworzenia powiązanych obiektów: {e}")


def _prepare_product_create(item):
    """Przygotuj dane do utworzenia nowego produktu"""
    from matterhorn1.models import Product
    from django.utils import timezone

    # Marka
    brand_id = item.get('brand_id') or 'unknown'
    brand_name = item.get('brand') or 'Unknown'

    # Kategoria
    category_id = item.get('category_id') or 'unknown'
    category_name = item.get('category_name') or 'Unknown'
    category_path = item.get('category_path') or ''

    # Konwersje
    active_value = item.get('active', True)
    if isinstance(active_value, str):
        active_value = active_value.lower() in ('true', '1', 'yes', 'y')

    new_collection_value = item.get('new_collection', False)
    if isinstance(new_collection_value, str):
        new_collection_value = new_collection_value.upper() in ('Y', 'YES', 'TRUE', '1')

    # Pobierz lub utwórz markę i kategorię
    from matterhorn1.models import Brand, Category

    brand, _ = Brand.objects.using('matterhorn1').get_or_create(
        brand_id=brand_id,
        defaults={'name': brand_name}
    )

    category, _ = Category.objects.using('matterhorn1').get_or_create(
        category_id=category_id,
        defaults={
            'name': category_name,
            'path': category_path
        }
    )

    product = Product(
        product_uid=int(item.get('id')),
        active=active_value,
        name=item.get('name', ''),
        description=item.get('description', ''),
        creation_date=_parse_creation_date(item.get('creation_date')),
        color=item.get('color', ''),
        url=item.get('url', ''),
        new_collection=new_collection_value,
        brand=brand,
        category=category,
        prices=item.get('prices') or {},
        products_in_set=item.get('products_in_set') or [],
        other_colors=item.get('other_colors') or [],
        last_api_sync=timezone.now()
    )

    # Dodaj warianty jeśli są dostępne
    if item.get('variants'):
        product._variants_to_create = []
        for variant_data in item['variants']:
            product._variants_to_create.append({
                'variant_uid': variant_data.get('variant_uid'),
                'name': variant_data.get('name', 'Unknown'),
                'stock': int(variant_data.get('stock', 0)) if str(variant_data.get('stock', '0')).isdigit() else 0,
                'max_processing_time': int(variant_data.get('max_processing_time', 0)) if str(variant_data.get('max_processing_time', '0')).isdigit() else 0,
                'ean': variant_data.get('ean', '')
            })

    # Dodaj obrazy jeśli są dostępne
    if item.get('images'):
        product._images_to_create = []
        for i, image_url in enumerate(item['images']):
            product._images_to_create.append({
                'image_url': image_url,
                'order': i
            })

    # Dodaj szczegóły produktu jeśli są dostępne
    if any(item.get(field) for field in ['weight', 'size_table', 'size_table_txt', 'size_table_html']):
        product._details_to_create = {
            'weight': str(item.get('weight')) if item.get('weight') else None,
            'size_table': item.get('size_table') or None,
            'size_table_txt': item.get('size_table_txt') or None,
            'size_table_html': item.get('size_table_html') or None
        }

    return product


def _prepare_product_update(product, item):
    """Przygotuj dane do aktualizacji istniejącego produktu"""
    from django.utils import timezone

    # Marka
    brand_id = item.get('brand_id') or 'unknown'
    brand_name = item.get('brand') or 'Unknown'

    # Kategoria
    category_id = item.get('category_id') or 'unknown'
    category_name = item.get('category_name') or 'Unknown'
    category_path = item.get('category_path') or ''

    # Konwersje
    active_value = item.get('active', True)
    if isinstance(active_value, str):
        active_value = active_value.lower() in ('true', '1', 'yes', 'y')

    new_collection_value = item.get('new_collection', False)
    if isinstance(new_collection_value, str):
        new_collection_value = new_collection_value.upper() in ('Y', 'YES', 'TRUE', '1')

    # Pobierz lub utwórz markę i kategorię
    from matterhorn1.models import Brand, Category

    brand, _ = Brand.objects.using('matterhorn1').get_or_create(
        brand_id=brand_id,
        defaults={'name': brand_name}
    )

    category, _ = Category.objects.using('matterhorn1').get_or_create(
        category_id=category_id,
        defaults={
            'name': category_name,
            'path': category_path
        }
    )

    # Aktualizuj pola
    product.active = active_value
    product.name = item.get('name', product.name)
    product.description = item.get('description', product.description)
    product.creation_date = _parse_creation_date(
        item.get('creation_date')) or product.creation_date
    product.color = item.get('color', product.color)
    product.url = item.get('url', product.url)
    product.new_collection = new_collection_value
    product.brand = brand
    product.category = category
    product.prices = item.get('prices') or product.prices
    product.products_in_set = item.get(
        'products_in_set') or product.products_in_set
    product.other_colors = item.get('other_colors') or product.other_colors
    product.last_api_sync = timezone.now()

    # Dodaj warianty jeśli są dostępne
    if item.get('variants'):
        product._variants_to_create = []
        for variant_data in item['variants']:
            product._variants_to_create.append({
                'variant_uid': variant_data.get('variant_uid'),
                'name': variant_data.get('name', 'Unknown'),
                'stock': int(variant_data.get('stock', 0)) if str(variant_data.get('stock', '0')).isdigit() else 0,
                'max_processing_time': int(variant_data.get('max_processing_time', 0)) if str(variant_data.get('max_processing_time', '0')).isdigit() else 0,
                'ean': variant_data.get('ean', '')
            })

    # Dodaj obrazy jeśli są dostępne
    if item.get('images'):
        product._images_to_create = []
        for i, image_url in enumerate(item['images']):
            product._images_to_create.append({
                'image_url': image_url,
                'order': i
            })

    # Dodaj szczegóły produktu jeśli są dostępne
    if any(item.get(field) for field in ['weight', 'size_table', 'size_table_txt', 'size_table_html']):
        product._details_to_create = {
            'weight': str(item.get('weight')) if item.get('weight') else None,
            'size_table': item.get('size_table') or None,
            'size_table_txt': item.get('size_table_txt') or None,
            'size_table_html': item.get('size_table_html') or None
        }


# Usunięto funkcje single import - używamy tylko bulk operations


def _update_inventory_from_api(api_url, username, password, batch_size, dry_run):
    """Pomocnicza funkcja do aktualizacji INVENTORY z bulk operations i tą samą datą co ITEMS"""
    try:
        # Użyj tej samej daty startu co ITEMS z poprawnym formatowaniem
        last_update = _get_last_items_update_time()

        # Jeśli nie można pobrać daty ostatniego importu, przerwij
        if last_update is None:
            logger.error(
                "❌ Nie można pobrać daty ostatniego importu dla INVENTORY - przerywam")
            return {
                'status': 'error',
                'error': 'Cannot get last import date for INVENTORY - database unavailable'
            }

        logger.info(
            f"📅 INVENTORY używam tej samej daty co ITEMS: {last_update}")

        # Pobierz dane uwierzytelniające
        from django.conf import settings
        import requests
        api_key = getattr(settings, 'MATTERHORN_API_KEY', '')
        if not api_key:
            api_key = f"{username}:{password}"

        headers = {
            "Content-Type": "application/json",
            "Authorization": api_key
        }

        updated_count = 0
        page = 1
        limit = 1000

        while True:
            try:
                # Pobierz dane z INVENTORY API z last_update
                url = f"{api_url}/B2BAPI/ITEMS/INVENTORY/?page={page}&limit={limit}&last_update={last_update}"
                logger.info(f"🔗 INVENTORY Request URL: {url}")

                response = requests.get(url, headers=headers, timeout=120)
                time.sleep(0.6)  # Ograniczenie API: max 2 requests/sekundę

                logger.info(
                    f"🔍 INVENTORY API Response strona {page}: status={response.status_code}")

                if response.status_code == 200:
                    if not response.text.strip():
                        logger.info(
                            "📊 INVENTORY - pusta odpowiedź - koniec danych")
                        break

                    try:
                        inventory_data = response.json()
                        if not inventory_data:
                            logger.info(
                                "📊 INVENTORY - brak danych na stronie - koniec")
                            break

                        logger.info(
                            f"📥 INVENTORY - pobrano {len(inventory_data)} rekordów ze strony {page}")

                        if not dry_run:
                            # Bulk update stanów magazynowych
                            page_updated = _bulk_update_inventory(
                                inventory_data)
                            updated_count += page_updated
                            logger.info(
                                f"✅ INVENTORY - zaktualizowano {page_updated} produktów na stronie {page}")

                        page += 1

                    except Exception as e:
                        logger.error(f"❌ Błąd parsowania JSON INVENTORY: {e}")
                        break

                elif response.status_code == 404:
                    logger.info(
                        "📊 INVENTORY - strona nie istnieje - koniec danych")
                    break
                else:
                    logger.warning(
                        f"⚠️ Błąd INVENTORY API {response.status_code}")
                    break

            except Exception as e:
                logger.error(
                    f"❌ Błąd podczas pobierania INVENTORY strony {page}: {e}")
                break

        logger.info(
            f"📊 INVENTORY zakończony: {updated_count} zaktualizowanych produktów")

        return {
            'status': 'success',
            'updated_count': updated_count
        }

    except Exception as e:
        logger.error(f"❌ Błąd aktualizacji INVENTORY: {e}")
        return {
            'status': 'error',
            'error': str(e)
        }


def _bulk_update_inventory(inventory_data):
    """Bulk update stanów magazynowych z INVENTORY API"""
    try:
        from matterhorn1.models import Product, ProductVariant
        from django.db import transaction

        # Sprawdź czy dane są dostępne
        if not inventory_data:
            logger.warning("Brak danych inventory do aktualizacji")
            return 0

        updated_count = 0
        variants_to_update = []

        # Przygotuj dane do bulk update
        for i, item in enumerate(inventory_data):
            if item is None:
                logger.warning(f"Pominięto None item na pozycji {i}")
                continue
            if not isinstance(item, dict):
                continue

            product_uid = item.get('id')
            if not product_uid:
                continue

            # Znajdź produkt
            try:
                product = Product.objects.using(
                    'matterhorn1').get(product_uid=int(product_uid))

                # Aktualizuj warianty (w INVENTORY API dane są w 'inventory')
                variants_data = item.get('inventory', [])

                if not variants_data:
                    logger.info(f"Brak wariantów dla produktu {product_uid}")
                    continue

                for j, variant_data in enumerate(variants_data):
                    if variant_data is None:
                        logger.warning(
                            f"Pominięto None variant {j} dla produktu {product_uid}")
                        continue
                    if not isinstance(variant_data, dict):
                        continue

                    variant_uid = variant_data.get('variant_uid')
                    if not variant_uid:
                        continue

                    # Znajdź wariant
                    try:
                        variant = ProductVariant.objects.using('matterhorn1').get(
                            variant_uid=variant_uid,
                            product=product
                        )

                        # Aktualizuj stan magazynowy
                        new_stock = int(variant_data.get('stock', 0)) if variant_data.get(
                            'stock', '0').isdigit() else 0
                        if variant.stock != new_stock:
                            # Śledź zmianę stanu przed aktualizacją
                            track_stock_change(
                                variant_uid=variant.variant_uid,
                                product_uid=variant.product.product_uid,
                                old_stock=variant.stock,
                                new_stock=new_stock,
                                product_name=variant.product.name,
                                variant_name=variant.name
                            )

                            variant.stock = new_stock
                            variants_to_update.append(variant)

                    except ProductVariant.DoesNotExist:
                        # Wariant nie istnieje - pomiń
                        continue

            except Product.DoesNotExist:
                # Produkt nie istnieje - pomiń
                continue

        # Bulk update wariantów
        if variants_to_update:
            with transaction.atomic(using='matterhorn1'):
                ProductVariant.objects.using('matterhorn1').bulk_update(
                    variants_to_update,
                    ['stock'],
                    batch_size=100
                )
                updated_count = len(variants_to_update)
                logger.info(
                    f"✅ INVENTORY bulk update: {updated_count} wariantów")

        return updated_count

    except Exception as e:
        logger.error(f"❌ Błąd bulk update INVENTORY: {e}")
        return 0


@shared_task(bind=True, name='matterhorn1.tasks.get_import_status')
def get_import_status(self, task_id):
    """
    Celery task do sprawdzania statusu importu

    Args:
        task_id: ID zadania do sprawdzenia
    """
    try:
        from celery.result import AsyncResult

        result = AsyncResult(task_id)

        if result.ready():
            if result.successful():
                return {
                    'status': 'completed',
                    'result': result.result,
                    'task_id': task_id
                }
            else:
                return {
                    'status': 'failed',
                    'error': str(result.result),
                    'task_id': task_id
                }
        else:
            return {
                'status': 'running',
                'progress': result.info.get('progress', 0) if result.info else 0,
                'task_id': task_id
            }

    except Exception as e:
        logger.error(f"❌ Błąd sprawdzania statusu: {e}")
        return {
            'status': 'error',
            'error': str(e),
            'task_id': task_id
        }


@shared_task(name='matterhorn1.tasks.test_periodic_task')
def test_periodic_task():
    """
    Prosty task do testowania periodic tasks
    """
    import logging
    import sys
    logger = logging.getLogger(__name__)

    # Log na różne sposoby
    logger.info("🧪 TEST PERIODIC TASK - WYKONANY!")
    logger.error("🧪 TEST PERIODIC TASK - WYKONANY!")  # ERROR będzie widoczny
    print("🧪 TEST PERIODIC TASK - WYKONANY!", file=sys.stderr)
    print("🧪 TEST PERIODIC TASK - WYKONANY!", file=sys.stdout)

    return "Test periodic task completed"


# simple_import_task usunięty - był redundantny z full_import_and_update


def _cleanup_old_running_imports():
    """
    Czyści stare rekordy 'running' starsze niż 2 godziny.
    To zapobiega kumulowaniu się zawieszonych importów.
    Z retry logic dla połączenia z bazą danych.
    """
    max_retries = 5
    retry_delay = 10  # 10 sekund między próbami

    for attempt in range(max_retries):
        try:
            from matterhorn1.models import ApiSyncLog
            from django.utils import timezone
            from datetime import timedelta

            # Znajdź stare running rekordy (starsze niż 2 godziny)
            cutoff_time = timezone.now() - timedelta(hours=2)
            old_running = ApiSyncLog.objects.using('matterhorn1').filter(
                sync_type='items_import',
                status='running',
                started_at__lt=cutoff_time
            )

            count = old_running.count()
            if count > 0:
                logger.warning(
                    f"🧹 Znaleziono {count} starych 'running' rekordów - oznaczam jako 'error'")

                # Oznacz jako 'error' zamiast usuwać
                old_running.update(
                    status='error',
                    completed_at=timezone.now(),
                    error_details='Zawieszone - automatycznie oznaczone jako błąd po 2 godzinach'
                )
                logger.info(
                    f"✅ Oznaczono {count} starych rekordów jako 'error'")
            else:
                logger.info("✅ Brak starych 'running' rekordów do czyszczenia")

            # Jeśli dotarliśmy tutaj, operacja się powiodła
            return

        except Exception as e:
            logger.error(
                f"❌ Błąd podczas czyszczenia starych running rekordów (próba {attempt + 1}/{max_retries}): {e}")

            if attempt < max_retries - 1:
                logger.warning(
                    f"⏳ Czekam {retry_delay} sekund przed ponowną próbą...")
                time.sleep(retry_delay)
            else:
                logger.error(
                    "❌ Osiągnięto maksymalną liczbę prób czyszczenia starych rekordów")


def _cleanup_all_running_imports():
    """
    Sprawdza czy są zawieszone taski i czyści blokadę Redis tylko jeśli task został przerwany.
    NIE czyści aktywnych tasków - tylko sprawdza czy blokada Redis jest spójna z DB.
    Z retry logic dla połączenia z bazą danych.
    """
    max_retries = 5
    retry_delay = 10  # 10 sekund między próbami

    for attempt in range(max_retries):
        try:
            from matterhorn1.models import ApiSyncLog
            from django.utils import timezone
            from django.core.cache import cache

            # Znajdź WSZYSTKIE running rekordy (niezależnie od wieku)
            all_running = ApiSyncLog.objects.using('matterhorn1').filter(
                sync_type='items_import',
                status='running'
            )

            count = all_running.count()

            # Sprawdź blokadę Redis
            lock_id = 'matterhorn1_full_import_lock'
            current_lock = cache.get(lock_id)

            if count > 0 and current_lock:
                # Są running rekordy w DB I blokada Redis - task działa normalnie
                logger.info(
                    f"✅ Znaleziono {count} aktywnych 'running' rekordów - task działa normalnie")
                logger.info(
                    "✅ Blokada Redis pozostaje aktywna - task nie został przerwany")

            elif count > 0 and not current_lock:
                # Są running rekordy w DB ale BRAK blokady Redis - task został przerwany
                logger.warning(
                    f"🧹 Znaleziono {count} 'running' rekordów bez blokady Redis - task został przerwany")

                # Oznacz jako 'error' - task został przerwany
                all_running.update(
                    status='error',
                    completed_at=timezone.now(),
                    error_details='Zawieszone - task został przerwany (restart/stop systemu)'
                )

                logger.info(
                    f"✅ Oznaczono {count} przerwanych rekordów jako 'error'")

            elif count == 0 and current_lock:
                # BRAK running rekordów w DB ale jest blokada Redis - ghost lock
                logger.warning(
                    f"🔒 Znaleziono blokadę Redis bez aktywnych tasków: {current_lock}")
                logger.info("🗑️  Usuwam ghost lock Redis")

                cache.delete(lock_id)

                if not cache.get(lock_id):
                    logger.info("✅ Ghost lock Redis został usunięty")
                else:
                    logger.error("❌ Nie udało się usunąć ghost lock Redis")

            else:
                # Brak running rekordów i brak blokady Redis - wszystko OK
                logger.info("✅ Brak aktywnych tasków - system gotowy")

            # Jeśli dotarliśmy tutaj, operacja się powiodła
            return

        except Exception as e:
            logger.error(
                f"❌ Błąd podczas sprawdzania running rekordów (próba {attempt + 1}/{max_retries}): {e}")

            if attempt < max_retries - 1:
                logger.warning(
                    f"⏳ Czekam {retry_delay} sekund przed ponowną próbą...")
                time.sleep(retry_delay)
            else:
                logger.error(
                    "❌ Osiągnięto maksymalną liczbę prób sprawdzania running rekordów")


@shared_task(bind=True, name='matterhorn1.tasks.track_stock_changes', queue='default')
def track_stock_changes(self, variant_uid, product_uid, old_stock, new_stock, product_name=None, variant_name=None):
    """
    Celery task do śledzenia zmian stanów magazynowych

    Args:
        variant_uid: ID wariantu
        product_uid: ID produktu
        old_stock: Poprzedni stan magazynowy
        new_stock: Nowy stan magazynowy
        product_name: Nazwa produktu (opcjonalne)
        variant_name: Nazwa wariantu (opcjonalne)
    """
    try:
        # logger.info(
        #     f"📊 Śledzenie zmiany stanu: {product_name} - {variant_name}: {old_stock} → {new_stock}")

        stock_history = track_stock_change(
            variant_uid=variant_uid,
            product_uid=product_uid,
            old_stock=old_stock,
            new_stock=new_stock,
            product_name=product_name,
            variant_name=variant_name
        )

        if stock_history:
            # logger.info(
            #     f"✅ Zapisano zmianę stanu w StockHistory (ID: {stock_history.id})")
            return {
                'status': 'success',
                'stock_history_id': stock_history.id,
                'variant_uid': variant_uid,
                'product_uid': product_uid,
                'stock_change': new_stock - old_stock
            }
        else:
            logger.error(
                f"❌ Nie udało się zapisać zmiany stanu dla wariantu {variant_uid}")
            return {
                'status': 'error',
                'error': 'Failed to save stock change'
            }

    except Exception as e:
        logger.error(f"❌ Błąd podczas śledzenia zmiany stanu: {e}")
        return {
            'status': 'error',
            'error': str(e)
        }


@shared_task(bind=True, name='matterhorn1.tasks.track_bulk_stock_changes', queue='default')
def track_bulk_stock_changes_task(self, changes_data):
    """
    Celery task do śledzenia masowych zmian stanów magazynowych

    Args:
        changes_data: Lista słowników z danymi zmian
    """
    try:
        logger.info(
            f"📊 Śledzenie masowych zmian stanów: {len(changes_data)} zmian")

        created_records = track_bulk_stock_changes(changes_data)

        logger.info(
            f"✅ Zapisano {len(created_records)} zmian stanów w StockHistory")
        return {
            'status': 'success',
            'created_count': len(created_records),
            'changes_data': changes_data
        }

    except Exception as e:
        logger.error(f"❌ Błąd podczas śledzenia masowych zmian stanów: {e}")
        return {
            'status': 'error',
            'error': str(e)
        }


@shared_task(bind=True, name='matterhorn1.tasks.sync_stock_changes_from_api', queue='default')
def sync_stock_changes_from_api_task(self):
    """
    Celery task do synchronizacji zmian stanów z API i śledzenia ich w StockHistory
    """
    try:
        logger.info("🔄 Rozpoczynam synchronizację stanów z API")

        changes_count = sync_stock_changes_from_api()

        logger.info(f"✅ Zsynchronizowano {changes_count} zmian stanów z API")
        return {
            'status': 'success',
            'changes_count': changes_count
        }

    except Exception as e:
        logger.error(f"❌ Błąd podczas synchronizacji stanów z API: {e}")
        return {
            'status': 'error',
            'error': str(e)
        }


@shared_task(bind=True, name='matterhorn1.tasks.clean_old_stock_history', queue='default')
def clean_old_stock_history_task(self, days_to_keep=90):
    """
    Celery task do czyszczenia starych rekordów z historii stanów magazynowych

    Args:
        days_to_keep: Liczba dni do zachowania
    """
    try:
        from .stock_tracker import clean_old_stock_history

        logger.info(
            f"🧹 Rozpoczynam czyszczenie historii stanów starszej niż {days_to_keep} dni")

        result = clean_old_stock_history(days_to_keep)

        logger.info(f"✅ {result}")
        return {
            'status': 'success',
            'message': result,
            'days_to_keep': days_to_keep
        }

    except Exception as e:
        logger.error(f"❌ Błąd podczas czyszczenia historii stanów: {e}")
        return {
            'status': 'error',
            'error': str(e)
        }
