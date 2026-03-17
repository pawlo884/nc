"""
Usuwa periodic task dashboard_pydash.tasks.refresh_dashboard_data (nieużywany, powoduje błąd Celery).

Użycie:
  python manage.py remove_pydash_dashboard_task --settings=core.settings.dev
"""
from django.core.management.base import BaseCommand
from django_celery_beat.models import PeriodicTask


class Command(BaseCommand):
    help = 'Usuwa periodic task PyDash (dashboard_pydash.tasks.refresh_dashboard_data) z bazy'

    def handle(self, *args, **options):
        from django.db.models import Q
        qs = PeriodicTask.objects.filter(
            Q(task='dashboard_pydash.tasks.refresh_dashboard_data')
            | Q(name__icontains='PyDash')
        )
        tasks = list(qs)
        for pt in tasks:
            name = pt.name
            pt.delete()
            self.stdout.write(self.style.SUCCESS(f'Usunięto: {name}'))
        if tasks:
            self.stdout.write(self.style.SUCCESS(f'Usunięto {len(tasks)} periodic task(s).'))
        else:
            self.stdout.write('Brak zadań do usunięcia.')
