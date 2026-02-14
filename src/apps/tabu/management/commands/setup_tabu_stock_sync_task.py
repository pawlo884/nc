"""
Konfiguruje periodic task dla synchronizacji stanów magazynowych Tabu (co 10 minut).
Używa GET products/basic – lekki endpoint, tylko stany i ceny.
Użycie:
  python manage.py setup_tabu_stock_sync_task --settings=core.settings.dev
  python manage.py setup_tabu_stock_sync_task --interval 10 --settings=core.settings.dev
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django_celery_beat.models import IntervalSchedule, PeriodicTask


class Command(BaseCommand):
    help = 'Konfiguruje periodic task dla synchronizacji stanów magazynowych Tabu (co 10 minut)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--interval',
            type=int,
            default=10,
            help='Interwał w minutach (domyślnie: 10)',
        )
        parser.add_argument(
            '--disable',
            action='store_true',
            help='Wyłącz task',
        )
        parser.add_argument(
            '--delete',
            action='store_true',
            help='Usuń istniejący task',
        )

    def handle(self, *args, **options):
        interval_minutes = options['interval']
        task_name = 'Synchronizacja stanów magazynowych Tabu'
        task_path = 'tabu.tasks.sync_tabu_stock'

        try:
            existing_task = PeriodicTask.objects.get(name=task_name)

            if options['delete']:
                existing_task.delete()
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Usunięto periodic task: {task_name}')
                )
                return

            schedule, _ = IntervalSchedule.objects.get_or_create(
                every=interval_minutes,
                period=IntervalSchedule.MINUTES,
            )
            existing_task.interval = schedule
            existing_task.enabled = not options['disable']
            existing_task.save()

            if not existing_task.queue:
                existing_task.queue = 'default'
                existing_task.save()
            status = 'wyłączony' if options['disable'] else 'włączony'
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Zaktualizowano periodic task: {task_name}\n'
                    f'   - Interwał: co {interval_minutes} minut\n'
                    f'   - Queue: {existing_task.queue or "default"}\n'
                    f'   - Status: {status}'
                )
            )

        except PeriodicTask.DoesNotExist:
            if options['delete']:
                self.stdout.write(
                    self.style.WARNING(f'⚠️  Task nie istnieje: {task_name}')
                )
                return

            schedule, _ = IntervalSchedule.objects.get_or_create(
                every=interval_minutes,
                period=IntervalSchedule.MINUTES,
            )
            PeriodicTask.objects.create(
                interval=schedule,
                name=task_name,
                task=task_path,
                queue='default',
                enabled=not options['disable'],
                start_time=timezone.now(),
                description='Synchronizuje stany i ceny z API Tabu (products/basic), update_from 12 min wstecz',
            )

            status = 'wyłączony' if options['disable'] else 'włączony'
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Utworzono periodic task: {task_name}\n'
                    f'   - Interwał: co {interval_minutes} minut\n'
                    f'   - Status: {status}'
                )
            )

        self.stdout.write(
            self.style.HTTP_INFO(
                '\n💡 Wskazówki:\n'
                '   - Ręczna synchronizacja: python manage.py sync_tabu_stock\n'
                '   - Zmiana interwału: python manage.py setup_tabu_stock_sync_task --interval 10\n'
                '   - Wyłączenie: python manage.py setup_tabu_stock_sync_task --disable\n'
                '   - Admin: /admin/django_celery_beat/periodictask/\n'
            )
        )
