import logging
from django.core.management.base import CommandError
from .base_api_command import BaseAPICommand

logger = logging.getLogger(__name__)


class Command(BaseAPICommand):
    """
    Komenda do zarządzania głównym Celery task - import i aktualizacja
    """

    help = 'Zarządzanie głównym Celery task - import ITEMS + aktualizacja INVENTORY'

    def add_arguments(self, parser):
        """Dodaj argumenty specyficzne dla zarządzania Celery tasks"""
        self.add_common_arguments(parser)

        parser.add_argument(
            '--action',
            type=str,
            choices=['import', 'status'],
            help='Akcja do wykonania: import, status',
            required=True
        )
        parser.add_argument(
            '--start-id',
            type=int,
            help='ID produktu od którego rozpocząć import (domyślnie ostatni w bazie)',
            default=None
        )
        parser.add_argument(
            '--max-products',
            type=int,
            help='Maksymalna liczba produktów na iterację (domyślnie 200000)',
            default=200000
        )
        parser.add_argument(
            '--auto-continue',
            action='store_true',
            help='Kontynuuj import aż skończą się produkty (domyślnie True)',
            default=True
        )
        parser.add_argument(
            '--task-id',
            type=str,
            help='ID zadania do sprawdzenia statusu',
            default=None
        )
        parser.add_argument(
            '--async',
            action='store_true',
            help='Uruchom zadanie asynchronicznie (domyślnie synchronicznie)'
        )

    def handle(self, *args, **options):
        """Główna logika zarządzania Celery tasks"""
        self.setup_logging(options.get('verbose', False))
        self.get_api_credentials(options)

        action = options.get('action')
        async_mode = options.get('async', False)

        try:
            if action == 'import':
                self.handle_import_action(options, async_mode)
            elif action == 'status':
                self.handle_status_action(options)
            else:
                raise CommandError(f"Nieznana akcja: {action}")

        except Exception as e:
            logger.error(f"Błąd zarządzania Celery tasks: {e}")
            raise CommandError(f"Błąd: {e}")

    def handle_import_action(self, options, async_mode):
        """Obsługa akcji import"""
        from matterhorn1.tasks import full_import_and_update

        start_id = options.get('start_id')
        max_products = options.get('max_products', 200000)
        auto_continue = options.get('auto_continue', True)
        api_url = options.get('api_url')
        username = options.get('username')
        password = options.get('password')
        batch_size = options.get('batch_size', 100)
        dry_run = options.get('dry_run', False)

        self.stdout.write("🚀 Uruchamianie importu (ITEMS + INVENTORY)...")
        self.stdout.write("📊 Parametry:")
        self.stdout.write(f"   - Start ID: {start_id or 'ostatni w bazie'}")
        self.stdout.write(f"   - Max produkty na iterację: {max_products}")
        self.stdout.write(f"   - Auto-continue: {auto_continue}")
        self.stdout.write(
            f"   - Tryb: {'asynchroniczny' if async_mode else 'synchroniczny'}")
        self.stdout.write(f"   - Dry run: {dry_run}")

        if async_mode:
            # Uruchom asynchronicznie
            result = full_import_and_update.delay(
                start_id=start_id,
                max_products=max_products,
                auto_continue=auto_continue,
                api_url=api_url,
                username=username,
                password=password,
                batch_size=batch_size,
                dry_run=dry_run
            )

            self.stdout.write(
                f"✅ Zadanie uruchomione asynchronicznie (task_id: {result.id})")
            self.stdout.write(
                f"📊 Sprawdź status: python manage.py celery_import --action status --task-id {result.id}")
            self.stdout.write(
                "📊 Monitoruj logi: celery -A nc worker --loglevel=info")

        else:
            # Uruchom synchronicznie
            self.stdout.write(
                "⏳ Uruchamianie synchronicznie (może potrwać długo)...")
            result = full_import_and_update(
                start_id=start_id,
                max_products=max_products,
                auto_continue=auto_continue,
                api_url=api_url,
                username=username,
                password=password,
                batch_size=batch_size,
                dry_run=dry_run
            )

            self.stdout.write(f"✅ Import zakończony: {result}")

    def handle_status_action(self, options):
        """Obsługa akcji status"""
        from matterhorn1.tasks import get_import_status

        task_id = options.get('task_id')
        if not task_id:
            raise CommandError("Musisz podać --task-id")

        self.stdout.write(f"📊 Sprawdzanie statusu zadania: {task_id}")

        result = get_import_status(task_id)

        self.stdout.write(f"Status: {result['status']}")
        if result['status'] == 'running':
            self.stdout.write(f"Postęp: {result.get('progress', 0)}%")
        elif result['status'] == 'completed':
            self.stdout.write(f"Wynik: {result['result']}")
        elif result['status'] == 'failed':
            self.stdout.write(f"Błąd: {result['error']}")
        elif result['status'] == 'error':
            self.stdout.write(f"Błąd: {result['error']}")
