"""
Konfiguruje periodic task Celery – odświeżanie danych dashboardu PyDash (KPI + wykresy → Redis).
Użycie (z katalogu nc_project):
  python src/manage.py setup_dashboard_refresh_task --settings=core.settings.dev
  python src/manage.py setup_dashboard_refresh_task --interval 5 --settings=core.settings.dev
  python src/manage.py setup_dashboard_refresh_task --disable --settings=core.settings.dev
Z katalogu src/:  python manage.py setup_dashboard_refresh_task --settings=core.settings.dev
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django_celery_beat.models import IntervalSchedule, PeriodicTask


class Command(BaseCommand):
    help = 'Konfiguruje periodic task odświeżania danych dashboardu PyDash (cache Redis)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--interval',
            type=int,
            default=5,
            help='Interwał w minutach (domyślnie: 5)',
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
        task_name = 'Odświeżanie danych dashboardu PyDash'
        task_path = 'dashboard_pydash.tasks.refresh_dashboard_data'

        try:
            existing_task = PeriodicTask.objects.get(name=task_name)

            if options['delete']:
                existing_task.delete()
                self.stdout.write(
                    self.style.SUCCESS(f'Usunięto periodic task: {task_name}')
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
                    f'Zaktualizowano periodic task: {task_name}\n'
                    f'  Interwał: co {interval_minutes} min, Queue: default, Status: {status}'
                )
            )

        except PeriodicTask.DoesNotExist:
            if options['delete']:
                self.stdout.write(self.style.WARNING(f'Task nie istnieje: {task_name}'))
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
                description='Ładuje KPI i wykresy dashboardu do cache (Redis); Dash czyta z cache.',
            )

            status = 'wyłączony' if options['disable'] else 'włączony'
            self.stdout.write(
                self.style.SUCCESS(
                    f'Utworzono periodic task: {task_name}\n'
                    f'  Interwał: co {interval_minutes} min, Status: {status}'
                )
            )
