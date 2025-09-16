import time
import logging
from datetime import datetime, timedelta
from celery import shared_task
from celery.utils.log import get_task_logger
from django.core.management import call_command
from django.conf import settings

logger = get_task_logger(__name__)


@shared_task(bind=True, name='matterhorn1.tasks.full_import_and_update')
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
    try:
        logger.info(
            f"🚀 ROZPOCZYNAM PEŁNY IMPORT I AKTUALIZACJĘ (task_id: {self.request.id})")

        # Pobierz parametry z settings jeśli nie podano
        if not api_url:
            api_url = getattr(settings, 'MATTERHORN_API_URL',
                              'https://matterhorn.pl')
        if not username:
            username = getattr(settings, 'MATTERHORN_API_USERNAME', '')
        if not password:
            password = getattr(settings, 'MATTERHORN_API_PASSWORD', '')

        total_imported = 0
        total_updated = 0
        iteration = 0

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

            if items_result['status'] != 'success':
                logger.error(
                    f"❌ Błąd importu ITEMS w iteracji {iteration}: {items_result.get('error')}")
                break

            imported_count = items_result.get('imported_count', 0)
            total_imported += imported_count

            logger.info(
                f"✅ Iteracja {iteration} - Zaimportowano {imported_count} produktów")

            # Jeśli nie zaimportowano żadnych produktów, zakończ
            if imported_count == 0:
                logger.info(
                    "📊 Brak nowych produktów do importu - kończę import ITEMS")
                break

            # KROK 2: Aktualizacja INVENTORY po każdej iteracji
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

            # Jeśli nie ma auto_continue, zakończ po pierwszej iteracji
            if not auto_continue:
                logger.info(
                    "📊 Auto-continue wyłączone - kończę po pierwszej iteracji")
                break

            # Ustaw start_id na ostatni zaimportowany + 1
            start_id = items_result.get('last_imported_id', 0) + 1

            # Sprawdź czy nie przekraczamy maksymalnej liczby iteracji
            if iteration >= 100:  # Bezpiecznik
                logger.warning(
                    "⚠️ Osiągnięto maksymalną liczbę iteracji (100) - kończę")
                break

        logger.info(f"🎉 PEŁNY IMPORT ZAKOŃCZONY!")
        logger.info(f"📊 Łącznie zaimportowano: {total_imported} produktów")
        logger.info(
            f"📊 Łącznie zaktualizowano: {total_updated} produktów w INVENTORY")

        return {
            'status': 'success',
            'total_imported': total_imported,
            'total_updated': total_updated,
            'iterations': iteration,
            'task_id': self.request.id
        }

    except Exception as e:
        logger.error(f"❌ Błąd pełnego importu: {e}")
        # 5 minut przerwy, max 2 retry
        self.retry(countdown=300, max_retries=2)
        return {
            'status': 'error',
            'error': str(e),
            'task_id': self.request.id
        }


def _import_products_from_items(start_id, max_products, api_url, username, password, batch_size, dry_run):
    """Pomocnicza funkcja do importu produktów z ITEMS z inteligentnym sprawdzaniem luk w ID"""
    try:
        # Określ start_id jeśli nie podano
        if start_id is None:
            from matterhorn1.models import Product
            last_product = Product.objects.using('matterhorn1').filter(
                name__isnull=False
            ).exclude(
                name__in=['Placeholder Name', '0 Nowy artykul - 0']
            ).order_by('-product_id').first()

            if last_product:
                start_id = int(last_product.product_id) + 1
                logger.info(
                    f"📊 Ostatni ID w bazie: {last_product.product_id}, rozpoczynam od: {start_id}")
            else:
                start_id = 1
                logger.info("📊 Brak produktów w bazie, rozpoczynam od ID: 1")

        # Inteligentne sprawdzanie luk w ID (jak w starym kodzie)
        imported_count = 0
        last_imported_id = start_id - 1
        null_count = 0
        max_null_count = 5  # Po 5 kolejnych NULL kończymy

        logger.info(
            f"🔍 Sprawdzanie luk w ID od {start_id} do {start_id + max_products - 1}")

        for current_id in range(start_id, start_id + max_products):
            try:
                # Sprawdź czy produkt już istnieje w bazie
                from matterhorn1.models import Product
                existing_product = Product.objects.using('matterhorn1').filter(
                    product_id=str(current_id)
                ).first()

                if existing_product:
                    logger.debug(
                        f"⏭️ Produkt ID {current_id} już istnieje w bazie - pomijam")
                    last_imported_id = current_id
                    continue

                # Pobierz dane z API dla konkretnego ID
                import requests
                url = f"{api_url}/B2BAPI/ITEMS/{current_id}"

                # Pobierz dane uwierzytelniające
                from django.conf import settings
                api_key = getattr(settings, 'MATTERHORN_API_KEY', '')
                if not api_key:
                    api_key = f"{username}:{password}"

                headers = {
                    "Content-Type": "application/json",
                    "Authorization": api_key
                }

                response = requests.get(url, headers=headers, timeout=30)
                time.sleep(0.6)  # Ograniczenie API: 2 requesty/sekundę

                if response.status_code == 200:
                    if not response.text.strip():
                        logger.warning(
                            f"⚠️ Pusta odpowiedź dla ID {current_id}")
                        null_count += 1
                        if null_count >= max_null_count:
                            logger.info(
                                f"📊 {max_null_count} kolejnych pustych odpowiedzi - kończę sprawdzanie")
                            break
                        continue

                    try:
                        item = response.json()

                        # Sprawdź czy creation_date jest NULL (jak w starym kodzie)
                        if item.get("creation_date") is None:
                            null_count += 1
                            logger.warning(
                                f"⚠️ creation_date NULL dla ID {current_id} ({null_count}/{max_null_count})")
                            if null_count >= max_null_count:
                                logger.info(
                                    f"📊 {max_null_count} kolejnych NULL creation_date - kończę sprawdzanie")
                                break
                            continue
                        else:
                            null_count = 0  # Reset licznika po znalezieniu prawidłowego produktu

                        logger.info(
                            f"✅ Znaleziono produkt ID {current_id}: {item.get('name', 'Unknown')}")

                        # Importuj produkt używając istniejącej logiki
                        if not dry_run:
                            _import_single_product(item)

                        imported_count += 1
                        last_imported_id = current_id

                    except Exception as e:
                        logger.warning(
                            f"⚠️ Błąd parsowania JSON dla ID {current_id}: {e}")
                        null_count += 1
                        if null_count >= max_null_count:
                            break
                        continue

                elif response.status_code == 404:
                    logger.debug(f"🔍 ID {current_id} nie istnieje w API")
                    null_count += 1
                    if null_count >= max_null_count:
                        logger.info(
                            f"📊 {max_null_count} kolejnych 404 - kończę sprawdzanie")
                        break
                    continue
                else:
                    logger.warning(
                        f"⚠️ Błąd API {response.status_code} dla ID {current_id}")
                    null_count += 1
                    if null_count >= max_null_count:
                        break
                    continue

            except Exception as e:
                logger.error(
                    f"❌ Błąd podczas sprawdzania ID {current_id}: {e}")
                null_count += 1
                if null_count >= max_null_count:
                    break
                continue

        logger.info(
            f"📊 Sprawdzanie zakończone: {imported_count} nowych produktów, ostatni ID: {last_imported_id}")

        return {
            'status': 'success',
            'imported_count': imported_count,
            'last_imported_id': last_imported_id
        }

    except Exception as e:
        logger.error(f"❌ Błąd importu ITEMS: {e}")
        return {
            'status': 'error',
            'error': str(e)
        }


def _import_single_product(item_data):
    """Importuje pojedynczy produkt do bazy danych"""
    try:
        from matterhorn1.models import Product, Brand, Category, ProductVariant, ProductImage, ProductDetails

        # Pobierz lub utwórz markę
        brand, _ = Brand.objects.using('matterhorn1').get_or_create(
            brand_id=item_data.get('brand_id', ''),
            defaults={'name': item_data.get('brand', 'Unknown')}
        )

        # Pobierz lub utwórz kategorię
        category, _ = Category.objects.using('matterhorn1').get_or_create(
            category_id=item_data.get('category_id', ''),
            defaults={
                'name': item_data.get('category_name', 'Unknown'),
                'path': item_data.get('category_path', '')
            }
        )

        # Utwórz lub zaktualizuj produkt
        product, created = Product.objects.using('matterhorn1').get_or_create(
            product_id=item_data.get('id'),
            defaults={
                'active': item_data.get('active', True),
                'name': item_data.get('name', ''),
                'description': item_data.get('description', ''),
                'creation_date': item_data.get('creation_date'),
                'color': item_data.get('color', ''),
                'url': item_data.get('url', ''),
                'new_collection': item_data.get('new_collection', False),
                'brand': brand,
                'category': category,
                'prices': item_data.get('prices', {}),
                'products_in_set': item_data.get('products_in_set', []),
                'other_colors': item_data.get('other_colors', [])
            }
        )

        if not created:
            # Aktualizuj istniejący produkt
            product.active = item_data.get('active', True)
            product.name = item_data.get('name', '')
            product.description = item_data.get('description', '')
            product.color = item_data.get('color', '')
            product.url = item_data.get('url', '')
            product.new_collection = item_data.get('new_collection', False)
            product.brand = brand
            product.category = category
            product.prices = item_data.get('prices', {})
            product.products_in_set = item_data.get('products_in_set', [])
            product.other_colors = item_data.get('other_colors', [])
            product.save()

        # Importuj warianty
        if item_data.get('variants'):
            for variant_data in item_data['variants']:
                ProductVariant.objects.using('matterhorn1').update_or_create(
                    variant_uid=variant_data.get('variant_uid'),
                    defaults={
                        'product': product,
                        'name': variant_data.get('name', ''),
                        'stock': int(variant_data.get('stock', 0)),
                        'max_processing_time': int(variant_data.get('max_processing_time', 0)),
                        'ean': variant_data.get('ean', '')
                    }
                )

        # Importuj obrazy
        if item_data.get('images'):
            for i, image_url in enumerate(item_data['images']):
                ProductImage.objects.using('matterhorn1').get_or_create(
                    product=product,
                    image_url=image_url,
                    defaults={'order': i}
                )

        # Importuj szczegóły produktu
        if any([item_data.get('weight'), item_data.get('size_table'),
                item_data.get('size_table_txt'), item_data.get('size_table_html')]):
            ProductDetails.objects.using('matterhorn1').update_or_create(
                product=product,
                defaults={
                    'weight': item_data.get('weight', ''),
                    'size_table': item_data.get('size_table', ''),
                    'size_table_txt': item_data.get('size_table_txt', ''),
                    'size_table_html': item_data.get('size_table_html', '')
                }
            )

        logger.debug(f"✅ Zaimportowano produkt ID {product.product_id}")

    except Exception as e:
        logger.error(f"❌ Błąd importu pojedynczego produktu: {e}")
        raise


def _update_inventory_from_api(api_url, username, password, batch_size, dry_run):
    """Pomocnicza funkcja do aktualizacji INVENTORY"""
    try:
        # Wywołaj komendę aktualizacji inventory
        call_command(
            'update_inventory',
            api_url=api_url,
            username=username,
            password=password,
            batch_size=batch_size,
            dry_run=dry_run,
            verbosity=1
        )

        # Pobierz liczbę zaktualizowanych produktów z logów
        from matterhorn1.models import ApiSyncLog
        last_sync = ApiSyncLog.objects.using('matterhorn1').filter(
            sync_type='inventory_update'
        ).order_by('-started_at').first()

        updated_count = last_sync.records_updated if last_sync else 0

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


@shared_task(bind=True, name='matterhorn1.tasks.scheduled_import_and_update')
def scheduled_import_and_update(self, api_url=None, username=None, password=None,
                                batch_size=100, max_products=10000):
    """
    Celery task do planowanych aktualizacji (co 10 minut)

    Logika:
    1. Sprawdza ostatni ID w bazie
    2. Sprawdza czy są nowe produkty (z lukami w ID)
    3. Jeśli są nowe - importuje je
    4. Aktualizuje INVENTORY (tylko zmienione)

    Args:
        api_url: URL API Matterhorn
        username: Nazwa użytkownika API
        password: Hasło API
        batch_size: Rozmiar batcha
        max_products: Max produktów do sprawdzenia
    """
    try:
        logger.info(f"⏰ PLANOWANA AKTUALIZACJA (task_id: {self.request.id})")

        # Pobierz parametry z settings jeśli nie podano
        if not api_url:
            api_url = getattr(settings, 'MATTERHORN_API_URL',
                              'https://matterhorn.pl')
        if not username:
            username = getattr(settings, 'MATTERHORN_API_USERNAME', '')
        if not password:
            password = getattr(settings, 'MATTERHORN_API_PASSWORD', '')

        # KROK 1: Sprawdź czy są nowe produkty do importu
        logger.info("🔍 Sprawdzanie nowych produktów...")

        items_result = _import_products_from_items(
            start_id=None,  # Automatycznie od ostatniego ID
            max_products=max_products,
            api_url=api_url,
            username=username,
            password=password,
            batch_size=batch_size,
            dry_run=False
        )

        imported_count = items_result.get('imported_count', 0)

        if items_result['status'] != 'success':
            logger.error(
                f"❌ Błąd sprawdzania nowych produktów: {items_result.get('error')}")
            return {
                'status': 'error',
                'error': items_result.get('error'),
                'task_id': self.request.id
            }

        if imported_count > 0:
            logger.info(f"✅ Znaleziono {imported_count} nowych produktów")
        else:
            logger.info("📊 Brak nowych produktów")

        # KROK 2: Aktualizacja INVENTORY (zawsze, nawet jeśli nie ma nowych produktów)
        logger.info("🔄 Aktualizacja INVENTORY...")

        inventory_result = _update_inventory_from_api(
            api_url=api_url,
            username=username,
            password=password,
            batch_size=batch_size,
            dry_run=False
        )

        updated_count = inventory_result.get(
            'updated_count', 0) if inventory_result['status'] == 'success' else 0

        if inventory_result['status'] == 'success':
            logger.info(
                f"✅ Zaktualizowano {updated_count} produktów w INVENTORY")
        else:
            logger.warning(
                f"⚠️ Błąd aktualizacji INVENTORY: {inventory_result.get('error')}")

        logger.info(f"🎉 PLANOWANA AKTUALIZACJA ZAKOŃCZONA")
        logger.info(
            f"📊 Nowe produkty: {imported_count}, Zaktualizowane: {updated_count}")

        return {
            'status': 'success',
            'imported_count': imported_count,
            'updated_count': updated_count,
            'task_id': self.request.id
        }

    except Exception as e:
        logger.error(f"❌ Błąd planowanej aktualizacji: {e}")
        return {
            'status': 'error',
            'error': str(e),
            'task_id': self.request.id
        }


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
