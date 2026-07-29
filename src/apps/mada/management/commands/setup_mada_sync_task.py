"""
Konfiguruje periodic tasks (django-celery-beat) dla synchronizacji Mada:
- import pełny: raz dziennie o zadanej godzinie (domyślnie 00:15, po wygenerowaniu
  pliku -full przez mada.pl ok. 00:01-00:02)
- import przyrostowy: co N minut (domyślnie 15)

Użycie:
  python manage.py setup_mada_sync_task --settings=core.settings.dev
  python manage.py setup_mada_sync_task --partial-interval 10 --full-hour 0 --full-minute 15 --settings=core.settings.dev
  python manage.py setup_mada_sync_task --disable --settings=core.settings.dev
  python manage.py setup_mada_sync_task --delete --settings=core.settings.dev
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django_celery_beat.models import CrontabSchedule, IntervalSchedule, PeriodicTask

FULL_TASK_NAME = 'Mada: import pełny (dziennie)'
PARTIAL_TASK_NAME = 'Mada: import przyrostowy'


class Command(BaseCommand):
    help = 'Konfiguruje periodic tasks dla importu pełnego (dziennie) i przyrostowego (co N min) Mada.'

    def add_arguments(self, parser):
        parser.add_argument('--partial-interval', type=int, default=15,
                             help='Interwał importu przyrostowego w minutach (domyślnie: 15)')
        parser.add_argument('--full-hour', type=int, default=0,
                             help='Godzina uruchomienia importu pełnego (domyślnie: 0)')
        parser.add_argument('--full-minute', type=int, default=15,
                             help='Minuta uruchomienia importu pełnego (domyślnie: 15)')
        parser.add_argument('--disable', action='store_true', help='Wyłącz oba taski')
        parser.add_argument('--delete', action='store_true', help='Usuń oba taski')

    def handle(self, *args, **options):
        if options['delete']:
            for name in (FULL_TASK_NAME, PARTIAL_TASK_NAME):
                deleted, _ = PeriodicTask.objects.filter(name=name).delete()
                if deleted:
                    self.stdout.write(self.style.SUCCESS(f'Usunięto periodic task: {name}'))
                else:
                    self.stdout.write(self.style.WARNING(f'Task nie istniał: {name}'))
            return

        enabled = not options['disable']

        crontab, _ = CrontabSchedule.objects.get_or_create(
            minute=str(options['full_minute']),
            hour=str(options['full_hour']),
            day_of_week='*', day_of_month='*', month_of_year='*',
        )
        full_task, created = PeriodicTask.objects.update_or_create(
            name=FULL_TASK_NAME,
            defaults={
                'crontab': crontab,
                'interval': None,
                'task': 'mada.tasks.sync_mada_full',
                'queue': 'default',
                'enabled': enabled,
                'start_time': timezone.now(),
                'description': 'Pełny import katalogu Mada (najnowszy plik TYPE=full).',
            },
        )
        self._report(full_task, created,
                     f"codziennie o {options['full_hour']:02d}:{options['full_minute']:02d}")

        interval, _ = IntervalSchedule.objects.get_or_create(
            every=options['partial_interval'], period=IntervalSchedule.MINUTES,
        )
        partial_task, created = PeriodicTask.objects.update_or_create(
            name=PARTIAL_TASK_NAME,
            defaults={
                'interval': interval,
                'crontab': None,
                'task': 'mada.tasks.sync_mada_partial',
                'queue': 'default',
                'enabled': enabled,
                'start_time': timezone.now(),
                'description': 'Import przyrostowy Mada (pliki TYPE=partial nowsze niż ostatni przetworzony).',
            },
        )
        self._report(partial_task, created, f"co {options['partial_interval']} minut")

        self.stdout.write(self.style.HTTP_INFO(
            '\nWskazówki:\n'
            '  - Ręczny import pełny: python manage.py sync_mada_full\n'
            '  - Ręczny import przyrostowy: python manage.py sync_mada_partial\n'
            '  - Wyłączenie obu: python manage.py setup_mada_sync_task --disable\n'
            '  - Admin: /admin/django_celery_beat/periodictask/\n'
        ))

    def _report(self, task, created, schedule_desc):
        verb = 'Utworzono' if created else 'Zaktualizowano'
        status = 'włączony' if task.enabled else 'wyłączony'
        self.stdout.write(self.style.SUCCESS(
            f'{verb} periodic task: {task.name}\n'
            f'   - Harmonogram: {schedule_desc}\n'
            f'   - Status: {status}'
        ))
