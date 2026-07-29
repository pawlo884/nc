"""
Import przyrostowy Mada (pliki TYPE=partial z manifestu, generowane ~co 10 min).
Przetwarza wszystkie pliki partial nowsze niż ostatni pomyślnie zaimportowany
(cursor = najwyższy file_name wśród ApiSyncLog sync_type=partial_import status=completed).

Uwaga: to tylko optymalizacja świeżości danych - codzienny sync_mada_full jest
źródłem prawdy i naprawia ewentualne pominięte/nieudane okna partial (np. gdy
jeden plik partial zawiedzie, a kolejny po nim się powiedzie, cofnięcie się do
nieudanego pliku nie jest tu obsługiwane - i tak zostanie nadgoniony przy
najbliższym pełnym imporcie).

Użycie:
  python manage.py sync_mada_partial --settings=core.settings.dev
"""
from django.core.management.base import BaseCommand
from django.db import router, transaction
from django.utils import timezone

from mada.api_client import MadaApiClient, MadaApiError
from mada.importer import import_product_dict, sync_brands
from mada.models import ApiSyncLog, MadaProduct
from mada.parser import iter_products, parse_producers


class Command(BaseCommand):
    help = 'Import przyrostowy Mada (pliki TYPE=partial nowsze niż ostatni przetworzony).'

    def handle(self, *args, **options):
        db = router.db_for_write(MadaProduct)
        client = MadaApiClient()

        last_file = (
            ApiSyncLog.objects.using(db)
            .filter(sync_type='partial_import', status='completed')
            .exclude(file_name='')
            .order_by('-file_name')
            .values_list('file_name', flat=True)
            .first()
        )

        try:
            new_files = client.partial_files_after(last_file)
        except MadaApiError as exc:
            self.stderr.write(self.style.ERROR(str(exc)))
            return

        if not new_files:
            self.stdout.write('Brak nowych plików partial do przetworzenia.')
            return

        self.stdout.write(
            f'Znaleziono {len(new_files)} nowych plików partial (od {last_file or "początku"}).'
        )
        category_cache = {}
        for feed_file in new_files:
            self._process_file(db, client, feed_file.name, category_cache)

    def _process_file(self, db, client, file_name, category_cache):
        log = ApiSyncLog.objects.using(db).create(
            sync_type='partial_import', status='running', file_name=file_name,
        )
        try:
            xml_bytes = client.download_products_xml(file_name)
        except MadaApiError as exc:
            self._fail(db, log, str(exc))
            self.stderr.write(self.style.ERROR(f'{file_name}: {exc}'))
            return

        try:
            producers = parse_producers(xml_bytes)
            if producers:
                sync_brands(db, producers)

            processed = created = errors = 0
            for product_dict in iter_products(xml_bytes):
                try:
                    with transaction.atomic(using=db):
                        was_created = import_product_dict(db, product_dict, category_cache)
                        if was_created:
                            created += 1
                except Exception:
                    errors += 1
                    self.stderr.write(self.style.WARNING(
                        f"{file_name}: błąd importu produktu api_id={product_dict.get('api_id')}"
                    ))
                processed += 1

            log.status = 'completed'
            log.completed_at = timezone.now()
            log.products_processed = processed
            log.products_created = created
            log.products_updated = processed - created - errors
            log.products_failed = errors
            log.save(using=db)

            self.stdout.write(self.style.SUCCESS(
                f'{file_name}: processed={processed} created={created} errors={errors}'
            ))
        except Exception as exc:
            self._fail(db, log, str(exc)[:2000])
            raise

    def _fail(self, db, log, message):
        log.status = 'failed'
        log.error_message = message
        log.completed_at = timezone.now()
        log.save(using=db)
