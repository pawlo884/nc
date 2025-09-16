import time
import logging
from datetime import datetime, timedelta
from django.core.management.base import CommandError
from django.core.management import call_command
from .base_api_command import BaseAPICommand

logger = logging.getLogger(__name__)


class Command(BaseAPICommand):
    """
    Komenda do planowania regularnych aktualizacji (co 10 minut)
    """

    help = 'Planuje regularne aktualizacje - sprawdza nowe produkty i aktualizuje INVENTORY'

    def add_arguments(self, parser):
        """Dodaj argumenty specyficzne dla planowania"""
        self.add_common_arguments(parser)

        parser.add_argument(
            '--action',
            type=str,
            choices=['schedule', 'run-now', 'status'],
            help='Akcja do wykonania: schedule, run-now, status',
            required=True
        )
        parser.add_argument(
            '--interval-minutes',
            type=int,
            help='Interwał aktualizacji w minutach (domyślnie 10)',
            default=10
        )
        parser.add_argument(
            '--max-products',
            type=int,
            help='Maksymalna liczba produktów do sprawdzenia (domyślnie 10000)',
            default=10000
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
        """Główna logika planowania"""
        self.setup_logging(options.get('verbose', False))
        self.get_api_credentials(options)

        action = options.get('action')
        async_mode = options.get('async', False)

        try:
            if action == 'schedule':
                self.handle_schedule_action(options, async_mode)
            elif action == 'run-now':
                self.handle_run_now_action(options, async_mode)
            elif action == 'status':
                self.handle_status_action(options)
            else:
                raise CommandError(f"Nieznana akcja: {action}")

        except Exception as e:
            logger.error(f"Błąd planowania: {e}")
            raise CommandError(f"Błąd: {e}")

    def handle_schedule_action(self, options, async_mode):
        """Obsługa akcji schedule - planowanie regularnych aktualizacji"""
        from matterhorn1.tasks import scheduled_import_and_update

        interval_minutes = options.get('interval_minutes', 10)
        max_products = options.get('max_products', 10000)
        api_url = options.get('api_url')
        username = options.get('username')
        password = options.get('password')
        batch_size = options.get('batch_size', 100)

        self.stdout.write(
            f"⏰ Planowanie aktualizacji co {interval_minutes} minut...")
        self.stdout.write(f"📊 Parametry:")
        self.stdout.write(f"   - Interwał: {interval_minutes} minut")
        self.stdout.write(f"   - Max produkty: {max_products}")
        self.stdout.write(
            f"   - Tryb: {'asynchroniczny' if async_mode else 'synchroniczny'}")

        if async_mode:
            # Uruchom asynchronicznie
            result = scheduled_import_and_update.delay(
                api_url=api_url,
                username=username,
                password=password,
                batch_size=batch_size,
                max_products=max_products
            )

            self.stdout.write(
                f"✅ Zadanie zaplanowane asynchronicznie (task_id: {result.id})")
            self.stdout.write(
                f"📊 Sprawdź status: python manage.py schedule_import --action status --task-id {result.id}")

        else:
            # Uruchom synchronicznie
            self.stdout.write("⏳ Uruchamianie synchronicznie...")
            result = scheduled_import_and_update(
                api_url=api_url,
                username=username,
                password=password,
                batch_size=batch_size,
                max_products=max_products
            )

            self.stdout.write(f"✅ Planowana aktualizacja zakończona: {result}")

    def handle_run_now_action(self, options, async_mode):
        """Obsługa akcji run-now - uruchomienie jednorazowej aktualizacji"""
        from matterhorn1.tasks import scheduled_import_and_update

        max_products = options.get('max_products', 10000)
        api_url = options.get('api_url')
        username = options.get('username')
        password = options.get('password')
        batch_size = options.get('batch_size', 100)

        self.stdout.write("🚀 Uruchamianie jednorazowej aktualizacji...")
        self.stdout.write(f"📊 Parametry:")
        self.stdout.write(f"   - Max produkty: {max_products}")
        self.stdout.write(
            f"   - Tryb: {'asynchroniczny' if async_mode else 'synchroniczny'}")

        if async_mode:
            # Uruchom asynchronicznie
            result = scheduled_import_and_update.delay(
                api_url=api_url,
                username=username,
                password=password,
                batch_size=batch_size,
                max_products=max_products
            )

            self.stdout.write(
                f"✅ Zadanie uruchomione asynchronicznie (task_id: {result.id})")
            self.stdout.write(
                f"📊 Sprawdź status: python manage.py schedule_import --action status --task-id {result.id}")

        else:
            # Uruchom synchronicznie
            self.stdout.write("⏳ Uruchamianie synchronicznie...")
            result = scheduled_import_and_update(
                api_url=api_url,
                username=username,
                password=password,
                batch_size=batch_size,
                max_products=max_products
            )

            self.stdout.write(
                f"✅ Jednorazowa aktualizacja zakończona: {result}")

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
