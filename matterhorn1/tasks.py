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
    """Pomocnicza funkcja do importu produktów z ITEMS używając last_update"""
    try:
        # Pobierz ostatni czas importu lub użyj domyślnego
        last_update = _get_last_items_update_time()
        logger.info(f"📅 Używam last_update: {last_update}")

        # WAŻNE: Zapisz czas ROZPOCZĘCIA importu PRZED rozpoczęciem
        if not dry_run:
            _save_items_import_start_time()

        # Użyj bulk API z last_update
        imported_count = 0
        last_imported_id = 0
        page = 1
        limit = 500  # Limit 500 dla importu ITEMS

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
                            break

                        try:
                            items = response.json()
                            if not items:
                                logger.info(
                                    "📊 Brak produktów na stronie - koniec danych")
                                break

                            logger.info(
                                f"📥 Pobrano {len(items)} produktów ze strony {page}")

                            # Bulk import/update
                            if not dry_run:
                                bulk_result = _bulk_import_products(items)
                                imported_count += bulk_result['imported_count']
                                last_imported_id = bulk_result['last_imported_id']
                            else:
                                # Dry run - tylko zlicz
                                for item in items:
                                    if imported_count >= max_products:
                                        break
                                    if item.get("creation_date") is not None:
                                        imported_count += 1
                                        last_imported_id = int(
                                            item.get('id', 0))

                            page += 1
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
                                    f"❌ Osiągnięto maksymalną liczbę prób parsowania JSON")
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
                                f"❌ Osiągnięto maksymalną liczbę prób API")
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
                            f"❌ Osiągnięto maksymalną liczbę prób połączenia")
                        break

            # Jeśli osiągnięto maksymalną liczbę prób, przerwij główną pętlę
            if attempt > max_attempts:
                break

        # Zaktualizuj status importu na 'success' po zakończeniu
        if not dry_run:
            _update_items_import_status('success', imported_count)

        logger.info(
            f"📊 Import zakończony: {imported_count} nowych produktów, ostatni ID: {last_imported_id}")

        return {
            'status': 'success',
            'imported_count': imported_count,
            'last_imported_id': last_imported_id
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


def _get_last_items_update_time():
    """Pobiera ostatni czas importu ITEMS lub zwraca domyślny (2015-01-01)"""
    try:
        from matterhorn1.models import ApiSyncLog
        import pytz
        from datetime import datetime

        last_sync = ApiSyncLog.objects.using('matterhorn1').filter(
            sync_type__in=['items_import', 'items_sync'],
            status__in=['success', 'partial']
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
            return poland_dt.strftime("%Y-%m-%d %H:%M:%S")
        else:
            # Domyślny czas - 2015-01-01 00:00:00
            return "2015-01-01 00:00:00"
    except Exception as e:
        logger.error(
            f"Błąd podczas pobierania ostatniego czasu importu ITEMS: {e}")
        return "2015-01-01 00:00:00"


def _save_items_import_start_time():
    """Zapisuje czas ROZPOCZĘCIA importu ITEMS - to będzie last_update dla następnego importu"""
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
            records_errors=0
        )
        logger.info("✅ Zapisano czas ROZPOCZĘCIA importu ITEMS")
    except Exception as e:
        logger.error(
            f"Błąd podczas zapisywania czasu rozpoczęcia importu ITEMS: {e}")


def _update_items_import_status(status, imported_count):
    """Aktualizuje status ostatniego importu ITEMS"""
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
            last_running.save()
            logger.info(f"✅ Zaktualizowano status importu ITEMS na: {status}")
        else:
            logger.warning(
                "⚠️ Nie znaleziono rekordu 'running' do aktualizacji")
    except Exception as e:
        logger.error(f"Błąd podczas aktualizacji statusu importu ITEMS: {e}")


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
        last_imported_id = 0

        # Przygotuj dane do bulk operations
        products_to_create = []
        products_to_update = []

        # Najpierw przygotuj wszystkie dane
        for item in items:
            if item.get("creation_date") is None:
                continue

            product_id = item.get('id')
            if not product_id:
                continue

            # Sprawdź czy produkt istnieje
            try:
                existing_product = Product.objects.using(
                    'matterhorn1').get(product_id=int(product_id))
                # Aktualizuj istniejący
                _prepare_product_update(existing_product, item)
                products_to_update.append(existing_product)
            except Product.DoesNotExist:
                # Utwórz nowy
                product_data = _prepare_product_create(item)
                products_to_create.append(product_data)

            imported_count += 1
            last_imported_id = int(product_id)

        # Bulk operations w transakcji
        with transaction.atomic(using='matterhorn1'):
            # Utwórz nowe produkty
            if products_to_create:
                Product.objects.using('matterhorn1').bulk_create(
                    products_to_create, batch_size=100)
                logger.info(
                    f"✅ Utworzono {len(products_to_create)} nowych produktów")

                # Utwórz warianty, obrazy i szczegóły dla nowych produktów
                _create_related_objects_for_products(products_to_create)

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
            'imported_count': imported_count,
            'last_imported_id': last_imported_id
        }

    except Exception as e:
        logger.error(f"❌ Błąd bulk import: {e}")
        # Fallback do pojedynczego importu
        imported_count = 0
        last_imported_id = 0
        for item in items:
            if item.get("creation_date") is None:
                continue
            try:
                _import_single_product_with_retry(item)
                imported_count += 1
                last_imported_id = int(item.get('id', 0))
            except Exception as e:
                logger.error(f"❌ Błąd importu produktu {item.get('id')}: {e}")
        return {
            'imported_count': imported_count,
            'last_imported_id': last_imported_id
        }


def _create_related_objects_for_products(products):
    """Utwórz warianty, obrazy i szczegóły dla produktów"""
    try:
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

        # Bulk operations dla obrazków
        if images_to_create:
            ProductImage.objects.using('matterhorn1').bulk_create(
                images_to_create, batch_size=100)
            logger.info(f"✅ Utworzono {len(images_to_create)} nowych obrazków")

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
        product_id=int(item.get('id')),
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


def _import_single_product_with_retry(item_data, max_attempts=5):
    """Importuje pojedynczy produkt z retry dla błędów bazy danych"""
    for attempt in range(1, max_attempts + 1):
        try:
            _import_single_product(item_data)
            return  # Sukces
        except Exception as e:
            if attempt < max_attempts:
                logger.warning(
                    f"⚠️ Błąd bazy danych dla produktu {item_data.get('id')} (próba {attempt}/{max_attempts}): {e}")
                logger.warning(f"⚠️ Ponawiam za 20 sekund...")
                time.sleep(20)
            else:
                logger.error(
                    f"❌ Osiągnięto maksymalną liczbę prób dla produktu {item_data.get('id')}: {e}")
                raise


def _import_single_product(item_data):
    """Importuje pojedynczy produkt do bazy danych"""
    try:
        from matterhorn1.models import Product, Brand, Category, ProductVariant, ProductImage, ProductDetails

        # Pobierz lub utwórz markę
        brand_id = item_data.get('brand_id') or 'unknown'
        brand_name = item_data.get('brand') or 'Unknown'
        brand, _ = Brand.objects.using('matterhorn1').get_or_create(
            brand_id=brand_id,
            defaults={'name': brand_name}
        )

        # Pobierz lub utwórz kategorię
        category_id = item_data.get('category_id') or 'unknown'
        category_name = item_data.get('category_name') or 'Unknown'
        category_path = item_data.get('category_path') or ''
        category, _ = Category.objects.using('matterhorn1').get_or_create(
            category_id=category_id,
            defaults={
                'name': category_name,
                'path': category_path
            }
        )

        # Konwersja active z string na boolean
        active_value = item_data.get('active', True)
        if isinstance(active_value, str):
            active_value = active_value.lower() in ('true', '1', 'yes', 'y')

        # Konwersja new_collection z string na boolean
        new_collection_value = item_data.get('new_collection', False)
        if isinstance(new_collection_value, str):
            new_collection_value = new_collection_value.upper() in ('Y', 'YES', 'TRUE', '1')

        # Utwórz lub zaktualizuj produkt
        product, created = Product.objects.using('matterhorn1').get_or_create(
            product_id=int(item_data.get('id')),
            defaults={
                'active': active_value,
                'name': item_data.get('name', ''),
                'description': item_data.get('description', ''),
                'creation_date': _parse_creation_date(item_data.get('creation_date')),
                'color': item_data.get('color', ''),
                'url': item_data.get('url', ''),
                'new_collection': new_collection_value,
                'brand': brand,
                'category': category,
                'prices': item_data.get('prices') or {},
                'products_in_set': item_data.get('products_in_set') or [],
                'other_colors': item_data.get('other_colors') or []
            }
        )

        if not created:
            # Aktualizuj istniejący produkt - wszystkie pola z ITEMS
            from django.utils import timezone
            product.active = active_value
            product.name = item_data.get('name', product.name)
            product.description = item_data.get(
                'description', product.description)
            product.creation_date = _parse_creation_date(
                item_data.get('creation_date')) or product.creation_date
            product.color = item_data.get('color', product.color)
            product.url = item_data.get('url', product.url)
            product.new_collection = new_collection_value
            product.brand = brand
            product.category = category
            product.prices = item_data.get('prices') or product.prices
            product.products_in_set = item_data.get(
                'products_in_set') or product.products_in_set
            product.other_colors = item_data.get(
                'other_colors') or product.other_colors
            product.last_api_sync = timezone.now()
            product.save(using='matterhorn1')

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
                    'weight': item_data.get('weight') or '',
                    'size_table': item_data.get('size_table') or '',
                    'size_table_txt': item_data.get('size_table_txt') or '',
                    'size_table_html': item_data.get('size_table_html') or ''
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
