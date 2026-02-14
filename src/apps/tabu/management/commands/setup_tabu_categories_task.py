"""
Konfiguruje periodic task dla synchronizacji kategorii Tabu (co tydzień).
Używa GET products/categories – sprawdza czy są nowe kategorie.
Użycie (manage.py jest w src/):
  python src/manage.py setup_tabu_categories_task --settings=core.settings.dev
  python src/manage.py setup_tabu_categories_task --interval 7 --settings=core.settings.dev
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django_celery_beat.models import IntervalSchedule, PeriodicTask


class Command(BaseCommand):
    help = 'Konfiguruje periodic task dla synchronizacji kategorii Tabu (co tydzień)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--interval',
            type=int,
            default=7,
            help='Interwał w dniach (domyślnie: 7 = tydzień)',
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
        interval_days = options['interval']
        task_name = 'Synchronizacja kategorii Tabu'
        task_path = 'tabu.tasks.sync_tabu_categories'

        try:
            existing_task = PeriodicTask.objects.get(name=task_name)

            if options['delete']:
                existing_task.delete()
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Usunięto periodic task: {task_name}')
                )
                return

            schedule, _ = IntervalSchedule.objects.get_or_create(
                every=interval_days,
                period=IntervalSchedule.DAYS,
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
                    f'   - Interwał: co {interval_days} dni\n'
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
                every=interval_days,
                period=IntervalSchedule.DAYS,
            )
            PeriodicTask.objects.create(
                interval=schedule,
                name=task_name,
                task=task_path,
                queue='default',
                enabled=not options['disable'],
                start_time=timezone.now(),
                description='Sprawdza czy są nowe kategorie w API Tabu (GET products/categories)',
            )

            status = 'wyłączony' if options['disable'] else 'włączony'
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Utworzono periodic task: {task_name}\n'
                    f'   - Interwał: co {interval_days} dni\n'
                    f'   - Status: {status}'
                )
            )

        self.stdout.write(
            self.style.HTTP_INFO(
                '\n💡 Wskazówki (z katalogu projektu):\n'
                '   - Ręczna synchronizacja: python src/manage.py sync_tabu_categories --settings=core.settings.dev\n'
                '   - Zmiana interwału: python src/manage.py setup_tabu_categories_task --interval 7 --settings=core.settings.dev\n'
                '   - Wyłączenie: python src/manage.py setup_tabu_categories_task --disable --settings=core.settings.dev\n'
                '   - Admin: /admin/django_celery_beat/periodictask/\n'
            )
        )
