"""
Pełny import katalogu Mada (najnowszy plik TYPE=full z manifestu, ~raz dziennie).
Produkty nieobecne w tym przebiegu są oznaczane jako is_active=False (wygaszone).

Użycie:
  python manage.py sync_mada_full --settings=core.settings.dev
  python manage.py sync_mada_full --file=2026-07-28-full --settings=core.settings.dev
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import router, transaction
from django.utils import timezone

from mada.api_client import MadaApiClient, MadaApiError
from mada.importer import import_product_dict, sync_brands
from mada.models import ApiSyncLog, MadaProduct
from mada.parser import iter_products, parse_producers

BATCH_SIZE = 200


class Command(BaseCommand):
    help = 'Pełny import katalogu Mada (najnowszy plik TYPE=full z manifestu API).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file', type=str, default=None,
            help='Wymuś konkretną nazwę pliku full zamiast najnowszego z manifestu',
        )

    def handle(self, *args, **options):
        db = router.db_for_write(MadaProduct)
        client = MadaApiClient()

        file_name = options.get('file')
        if not file_name:
            latest = client.latest_full_file()
            if latest is None:
                raise CommandError('Manifest Mada nie zawiera żadnego pliku TYPE=full.')
            file_name = latest.name

        self.stdout.write(f'Pobieram pełny import Mada: {file_name}')
        log = ApiSyncLog.objects.using(db).create(
            sync_type='full_import', status='running', file_name=file_name,
        )

        try:
            xml_bytes = client.download_products_xml(file_name)
        except MadaApiError as exc:
            self._fail(db, log, str(exc))
            raise CommandError(str(exc))

        processed = created = errors = 0
        seen_api_ids = set()
        category_cache = {}

        try:
            producers = parse_producers(xml_bytes)
            self.stdout.write(f'Producenci w feedzie: {len(producers)}')
            sync_brands(db, producers)

            batch = []
            for product_dict in iter_products(xml_bytes):
                batch.append(product_dict)
                if len(batch) >= BATCH_SIZE:
                    c, e = self._process_batch(db, batch, category_cache)
                    created += c
                    errors += e
                    processed += len(batch)
                    seen_api_ids.update(p['api_id'] for p in batch)
                    self.stdout.write(f'  ... przetworzono {processed}')
                    batch = []
            if batch:
                c, e = self._process_batch(db, batch, category_cache)
                created += c
                errors += e
                processed += len(batch)
                seen_api_ids.update(p['api_id'] for p in batch)

            deactivated = (
                MadaProduct.objects.using(db)
                .exclude(api_id__in=seen_api_ids)
                .filter(is_active=True)
                .update(is_active=False)
            )

            log.status = 'completed'
            log.completed_at = timezone.now()
            log.products_processed = processed
            log.products_created = created
            log.products_updated = processed - created - errors
            log.products_failed = errors
            log.save(using=db)

            self.stdout.write(self.style.SUCCESS(
                f'Import pełny zakończony: processed={processed} created={created} '
                f'errors={errors} wygaszono={deactivated}'
            ))
        except Exception as exc:
            self._fail(db, log, str(exc)[:2000])
            raise

    def _process_batch(self, db, batch, category_cache):
        # Osobna transakcja (savepoint) na produkt - błąd jednego nie psuje reszty
        # batcha (błąd w atomic() na Postgresie unieważnia całą otaczającą transakcję).
        created = 0
        errors = 0
        for product_dict in batch:
            try:
                with transaction.atomic(using=db):
                    was_created = import_product_dict(db, product_dict, category_cache)
                    if was_created:
                        created += 1
            except Exception:
                errors += 1
                self.stderr.write(
                    self.style.WARNING(f"Błąd importu produktu api_id={product_dict.get('api_id')}")
                )
        return created, errors

    def _fail(self, db, log, message):
        log.status = 'failed'
        log.error_message = message
        log.completed_at = timezone.now()
        log.save(using=db)
