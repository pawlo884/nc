"""
Konfiguruje periodic task dla sprawdzania nowych produktów Tabu (co kilka godzin).
Użycie:
  python manage.py setup_tabu_sync_task --settings=core.settings.dev
  python manage.py setup_tabu_sync_task --interval 60 --settings=core.settings.dev
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django_celery_beat.models import IntervalSchedule, PeriodicTask


class Command(BaseCommand):
    help = 'Konfiguruje periodic task dla sprawdzania nowych produktów Tabu (co kilka godzin)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--interval',
            type=int,
            default=60,
            help='Interwał w minutach (domyślnie: 60 = 1h)',
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
        task_name = 'Synchronizacja produktów Tabu'
        task_path = 'tabu.tasks.sync_tabu_products_update'

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
                description='Sprawdza nowe produkty: max(api_id)+1, 404=brak',
            )

            status = 'wyłączony' if options['disable'] else 'włączony'
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Utworzono periodic task: {task_name}\n'
                    f'   - Interwał: co {interval_minutes} minut\n'
                    f'   - Status: {status}'
                )
            )

        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(
            self.style.HTTP_INFO('📋 Wszystkie periodic taski Tabu:')
        )
        self.stdout.write('=' * 60)

        tabu_tasks = PeriodicTask.objects.filter(task__startswith='tabu.tasks.')
        if not tabu_tasks.exists():
            self.stdout.write(self.style.WARNING('   Brak tasków'))
        else:
            for task in tabu_tasks:
                icon = '✅' if task.enabled else '❌'
                info = (
                    f'co {task.interval.every} {task.interval.period}'
                    if task.interval
                    else str(task.crontab or '')
                )
                queue_info = task.queue or '(pusta – używa default)'
                self.stdout.write(
                    f'\n{icon} {task.name}\n'
                    f'   Task: {task.task}\n'
                    f'   Queue: {queue_info}\n'
                    f'   Schedule: {info}\n'
                    f'   Ostatnie uruchomienie: {task.last_run_at or "Nigdy"}'
                )

        self.stdout.write(
            self.style.HTTP_INFO(
                '\n💡 Wskazówki:\n'
                '   - Pełny import: python manage.py sync_tabu_products\n'
                '   - Zmiana interwału: python manage.py setup_tabu_sync_task --interval 60\n'
                '   - Wyłączenie: python manage.py setup_tabu_sync_task --disable\n'
                '   - Admin: /admin/django_celery_beat/periodictask/\n'
            )
        )
