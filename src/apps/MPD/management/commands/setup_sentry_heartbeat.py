"""
Management command – konfiguracja periodic task heartbeat dla Sentry Crons.
"""
from django.core.management.base import BaseCommand
from django_celery_beat.models import IntervalSchedule, PeriodicTask


class Command(BaseCommand):
    help = 'Konfiguruje periodic task heartbeat dla monitorowania Sentry Crons'

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
            help='Wyłącz task zamiast go włączyć',
        )
        parser.add_argument(
            '--delete',
            action='store_true',
            help='Usuń istniejący task',
        )

    def handle(self, *args, **options):
        task_name = 'core: server heartbeat (Sentry Crons)'
        task_path = 'core.tasks.server_heartbeat'

        if options['delete']:
            deleted, _ = PeriodicTask.objects.filter(name=task_name).delete()
            self.stdout.write(self.style.SUCCESS(
                f'Usunięto {deleted} periodic task(ów): {task_name}'
            ))
            return

        interval, _ = IntervalSchedule.objects.get_or_create(
            every=options['interval'],
            period=IntervalSchedule.MINUTES,
        )

        task, created = PeriodicTask.objects.update_or_create(
            name=task_name,
            defaults={
                'interval': interval,
                'task': task_path,
                'enabled': not options['disable'],
                'description': (
                    'Heartbeat dla Sentry Crons – alert gdy Celery Beat/worker nie działa'
                ),
            },
        )

        action = 'Utworzono' if created else 'Zaktualizowano'
        status = 'włączony' if task.enabled else 'wyłączony'
        self.stdout.write(self.style.SUCCESS(
            f'{action} periodic task: {task_name} (co {options["interval"]} min, {status})'
        ))
