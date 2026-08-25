"""
Konfiguruje periodic task (django-celery-beat) do codziennego czyszczenia
pustych produktów Mada (bez NAME w feedzie).

Domyślnie 01:00 - godzinę po pełnym imporcie (00:15, patrz
setup_mada_sync_task), żeby nie kasować produktów, które tego samego dnia
mogą jeszcze zostać uzupełnione przez feed.

Użycie:
  python manage.py setup_mada_cleanup_task --settings=core.settings.dev
  python manage.py setup_mada_cleanup_task --hour 1 --minute 0 --settings=core.settings.dev
  python manage.py setup_mada_cleanup_task --disable --settings=core.settings.dev
  python manage.py setup_mada_cleanup_task --delete --settings=core.settings.dev
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django_celery_beat.models import CrontabSchedule, PeriodicTask

TASK_NAME = 'Mada: czyszczenie pustych produktów (dziennie)'


class Command(BaseCommand):
    help = 'Konfiguruje periodic task czyszczący puste produkty Mada raz dziennie.'

    def add_arguments(self, parser):
        parser.add_argument('--hour', type=int, default=1,
                             help='Godzina uruchomienia (domyślnie: 1, po pełnym imporcie o 00:15)')
        parser.add_argument('--minute', type=int, default=0,
                             help='Minuta uruchomienia (domyślnie: 0)')
        parser.add_argument('--disable', action='store_true', help='Wyłącz task')
        parser.add_argument('--delete', action='store_true', help='Usuń task')

    def handle(self, *args, **options):
        if options['delete']:
            deleted, _ = PeriodicTask.objects.filter(name=TASK_NAME).delete()
            if deleted:
                self.stdout.write(self.style.SUCCESS(f'Usunięto periodic task: {TASK_NAME}'))
            else:
                self.stdout.write(self.style.WARNING(f'Task nie istniał: {TASK_NAME}'))
            return

        enabled = not options['disable']

        crontab, _ = CrontabSchedule.objects.get_or_create(
            minute=str(options['minute']),
            hour=str(options['hour']),
            day_of_week='*', day_of_month='*', month_of_year='*',
        )
        task, created = PeriodicTask.objects.update_or_create(
            name=TASK_NAME,
            defaults={
                'crontab': crontab,
                'interval': None,
                'task': 'mada.tasks.cleanup_empty_products',
                'queue': 'default',
                'enabled': enabled,
                'start_time': timezone.now(),
                'description': (
                    'Usuwa produkty Mada bez NAME w feedzie (nigdy nie zmapowane do MPD). '
                    'CASCADE kasuje też ich warianty/zdjęcia. Jeśli produkt pojawi się '
                    'później w feedzie z danymi, sync_mada_full go po prostu odtworzy.'
                ),
            },
        )
        verb = 'Utworzono' if created else 'Zaktualizowano'
        status = 'włączony' if task.enabled else 'wyłączony'
        self.stdout.write(self.style.SUCCESS(
            f'{verb} periodic task: {task.name}\n'
            f'   - Harmonogram: codziennie o {options["hour"]:02d}:{options["minute"]:02d}\n'
            f'   - Status: {status}'
        ))
        self.stdout.write(self.style.HTTP_INFO(
            '\nWskazówki:\n'
            '  - Podgląd bez usuwania: python manage.py cleanup_empty_mada_products --dry-run\n'
            '  - Ręczne uruchomienie: python manage.py cleanup_empty_mada_products\n'
            '  - Wyłączenie: python manage.py setup_mada_cleanup_task --disable\n'
            '  - Admin: /admin/django_celery_beat/periodictask/\n'
        ))
