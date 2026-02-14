"""
Synchronizacja kategorii z API Tabu (GET products/categories).
Uruchom przed importem produktów – produkty będą linkowane do prawdziwych nazw kategorii.
Użycie:
  python manage.py sync_tabu_categories --settings=core.settings.dev
"""
import logging
import time

from django.db import router

from tabu.models import Category

from .base_tabu_api_command import BaseTabuAPICommand

logger = logging.getLogger(__name__)


class Command(BaseTabuAPICommand):
    help = 'Pobiera listę kategorii z API Tabu (GET products/categories) i zapisuje do bazy'

    def add_arguments(self, parser):
        self.add_common_arguments(parser)

    def handle(self, *args, **options):
        self.setup_logging(options.get('verbose', False))
        self.get_api_credentials(options)

        limit = options.get('limit', 100)
        dry_run = options.get('dry_run', False)

        if not dry_run:
            self.create_sync_log('categories_sync')

        try:
            self.stdout.write('Pobieranie kategorii (GET products/categories)...')

            all_categories = []
            page = 1

            while True:
                params = {'page': page, 'limit': limit}
                data = self.make_api_request('products/categories', params=params)
                categories = data.get('categories', [])

                if not categories:
                    break

                all_categories.extend(categories)
                total = data.get('total')
                if total is not None and len(all_categories) >= int(total):
                    break
                if len(categories) < limit:
                    break

                page += 1
                self.stdout.write(f'   Strona {page}...')
                time.sleep(0.5)

            self.stdout.write(f'   Pobrano {len(all_categories)} kategorii')
            logger.info('Tabu: pobrano %d kategorii', len(all_categories))

            if not all_categories:
                self.stdout.write('Brak kategorii w odpowiedzi API')
                if not dry_run and self.sync_log:
                    self.complete_sync_log('completed')
                return

            all_categories.sort(key=lambda c: (int(c.get('lvl', 0)), int(c.get('id', 0))))

            db = router.db_for_write(Category)
            created = 0
            updated = 0
            id_to_obj = {}

            for api_cat in all_categories:
                cid = str(api_cat.get('id', ''))
                if not cid:
                    continue

                parent_id = api_cat.get('parent_id')
                parent = None
                if parent_id:
                    parent_id = str(parent_id).strip()
                    if parent_id and parent_id in id_to_obj:
                        parent = id_to_obj[parent_id]

                defaults = {
                    'name': str(api_cat.get('name') or '')[:200],
                    'path': str(api_cat.get('path') or '')[:500],
                    'parent': parent,
                }

                if not dry_run:
                    obj, was_created = Category.objects.using(db).update_or_create(
                        category_id=cid,
                        defaults=defaults,
                    )
                    if was_created:
                        created += 1
                    else:
                        updated += 1
                    id_to_obj[cid] = obj

            if not dry_run and self.sync_log:
                self.update_sync_log(
                    products_processed=len(all_categories),
                    products_success=created + updated,
                    products_failed=0,
                    raw_response={'created': created, 'updated': updated},
                )
                self.complete_sync_log('completed')

            self.stdout.write(
                self.style.SUCCESS(
                    f'\n✅ Zakończono! Utworzono: {created}, zaktualizowano: {updated}'
                )
            )
            logger.info('Tabu kategorie: utworzono %d, zaktualizowano %d', created, updated)

        except Exception as e:
            logger.exception('Błąd synchronizacji kategorii Tabu: %s', e)
            if not dry_run and self.sync_log:
                self.complete_sync_log('failed', str(e))
            raise
