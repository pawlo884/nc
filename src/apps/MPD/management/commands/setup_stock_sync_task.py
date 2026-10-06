"""
Management command do konfiguracji periodic task dla mostu stanów magazynowych
hurtownia -> MPD.StockAndPrices (#270: rozszerzone o tabu/mada, wcześniej
tylko matterhorn1).
"""
import json

from django.core.management.base import BaseCommand
from django.utils import timezone
from django_celery_beat.models import PeriodicTask, IntervalSchedule

# Nazwa/task_path per źródło. Nazwa dla matterhorn1 zostaje jak była (żeby
# `PeriodicTask.objects.get(name=...)` trafiał w istniejący wpis w prod DB,
# a nie tworzył duplikatu) - tabu/mada dostają analogiczne nowe wpisy.
SOURCES = {
    'matterhorn1': {
        'task_name': 'Synchronizacja stanów MPD z Matterhorn1',
        'task_path': 'MPD.tasks.update_stock_from_matterhorn1',
        'description': 'Synchronizuje stany magazynowe z bazy Matterhorn1 do MPD',
        'takes_time_window': True,
    },
    'tabu': {
        'task_name': 'Synchronizacja stanów MPD z Tabu',
        'task_path': 'MPD.tasks.update_stock_from_tabu',
        'description': 'Synchronizuje stany magazynowe z bazy Tabu do MPD (#270)',
        'takes_time_window': False,
    },
    'mada': {
        'task_name': 'Synchronizacja stanów MPD z Mada',
        'task_path': 'MPD.tasks.update_stock_from_mada',
        'description': 'Synchronizuje stany magazynowe z bazy Mada do MPD (#270)',
        'takes_time_window': False,
    },
}


class Command(BaseCommand):
    help = 'Konfiguruje periodic task dla mostu stanów magazynowych hurtownia -> MPD'

    def add_arguments(self, parser):
        parser.add_argument(
            '--source',
            choices=sorted(SOURCES.keys()),
            default='matterhorn1',
            help='Która hurtownia (domyślnie: matterhorn1, zachowanie sprzed #270)',
        )
        parser.add_argument(
            '--interval',
            type=int,
            default=5,
            help='Interval w minutach (domyślnie: 5)'
        )
        parser.add_argument(
            '--time-window',
            type=int,
            default=15,
            help='Ile minut wstecz sprawdzać zmiany - tylko matterhorn1 (domyślnie: 15)'
        )
        parser.add_argument(
            '--disable',
            action='store_true',
            help='Wyłącz task zamiast go włączyć'
        )
        parser.add_argument(
            '--delete',
            action='store_true',
            help='Usuń istniejący task'
        )

    def handle(self, *args, **options):
        source = SOURCES[options['source']]
        interval_minutes = options['interval']
        time_window_minutes = options['time_window']
        task_name = source['task_name']
        task_path = source['task_path']

        task_kwargs = ''
        if source['takes_time_window']:
            task_kwargs = json.dumps({'time_window_minutes': time_window_minutes})

        # Sprawdź czy task już istnieje
        try:
            existing_task = PeriodicTask.objects.get(name=task_name)

            if options['delete']:
                existing_task.delete()
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✅ Usunięto periodic task: {task_name}')
                )
                return

            # Aktualizuj istniejący task
            schedule, created = IntervalSchedule.objects.get_or_create(
                every=interval_minutes,
                period=IntervalSchedule.MINUTES,
            )

            existing_task.interval = schedule
            existing_task.enabled = not options['disable']
            if source['takes_time_window']:
                existing_task.kwargs = task_kwargs
            existing_task.save()

            status = 'wyłączony' if options['disable'] else 'włączony'
            extra = f'\n   - Okno czasowe: {time_window_minutes} minut' if source['takes_time_window'] else ''
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Zaktualizowano periodic task: {task_name}\n'
                    f'   - Interval: co {interval_minutes} minut'
                    f'{extra}\n'
                    f'   - Status: {status}'
                )
            )

        except PeriodicTask.DoesNotExist:
            if options['delete']:
                self.stdout.write(
                    self.style.WARNING(f'⚠️  Task nie istnieje: {task_name}')
                )
                return

            # Utwórz nowy task
            schedule, created = IntervalSchedule.objects.get_or_create(
                every=interval_minutes,
                period=IntervalSchedule.MINUTES,
            )

            if created:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✨ Utworzono nowy schedule: co {interval_minutes} minut')
                )

            task = PeriodicTask.objects.create(
                interval=schedule,
                name=task_name,
                task=task_path,
                kwargs=task_kwargs,
                enabled=not options['disable'],
                start_time=timezone.now(),
                description=source['description'],
            )

            status = 'wyłączony' if options['disable'] else 'włączony'
            extra = f'\n   - Okno czasowe: {time_window_minutes} minut' if source['takes_time_window'] else ''
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Utworzono periodic task: {task_name}\n'
                    f'   - Interval: co {interval_minutes} minut'
                    f'{extra}\n'
                    f'   - Status: {status}\n'
                    f'   - Task ID: {task.id}'
                )
            )

        # Pokaż informacje o tasków
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.HTTP_INFO(
            '📋 Wszystkie periodic taski dla MPD:'))
        self.stdout.write('=' * 60)

        mpd_tasks = PeriodicTask.objects.filter(task__startswith='MPD.tasks.')

        if not mpd_tasks.exists():
            self.stdout.write(self.style.WARNING('   Brak tasków'))
        else:
            for task in mpd_tasks:
                status_icon = '✅' if task.enabled else '❌'
                schedule_info = ''
                if task.interval:
                    schedule_info = f'co {task.interval.every} {task.interval.period}'
                elif task.crontab:
                    schedule_info = str(task.crontab)

                self.stdout.write(
                    f'\n{status_icon} {task.name}\n'
                    f'   Task: {task.task}\n'
                    f'   Schedule: {schedule_info}\n'
                    f'   Ostatnie uruchomienie: {task.last_run_at or "Nigdy"}'
                )

        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(
            self.style.HTTP_INFO(
                '\n💡 Wskazówki:\n'
                '   - Domyślnie: matterhorn1, co 5 minut, okno 15 minut\n'
                '   - Inna hurtownia: python manage.py setup_stock_sync_task --source tabu\n'
                '   - Zmiana intervalu: python manage.py setup_stock_sync_task --interval 10\n'
                '   - Zmiana okna czasowego (tylko matterhorn1): --time-window 30\n'
                '   - Aby wyłączyć: python manage.py setup_stock_sync_task --source tabu --disable\n'
                '   - Aby usunąć: python manage.py setup_stock_sync_task --source tabu --delete\n'
                '   - Monitoring: http://localhost:5555 (Flower)\n'
                '   - Admin: /admin/django_celery_beat/periodictask/\n'
            )
        )
