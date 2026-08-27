from django.db import migrations
from django.db.utils import OperationalError, ProgrammingError

TASK_NAME = 'tabu: watchdog sync_tabu_stock lock (co 5 min)'


def create_watchdog_periodic_task(apps, schema_editor):
    # django_celery_beat zyje w bazie 'default' (DefaultRouter), a ta migracja
    # bywa uruchamiana z --database=tabu (TabuRouter) — dlatego uzywamy realnych
    # modeli z jawnym using('default') zamiast apps.get_model(), i lapiemy blad
    # gdy celery_beat nie jest zainstalowany albo tabele w 'default' jeszcze nie
    # istnieja (standalone `migrate tabu`).
    try:
        from django_celery_beat.models import IntervalSchedule, PeriodicTask

        interval, _ = IntervalSchedule.objects.using('default').get_or_create(
            every=5,
            period=IntervalSchedule.MINUTES,
        )
        PeriodicTask.objects.using('default').update_or_create(
            name=TASK_NAME,
            defaults={
                'interval': interval,
                'task': 'tabu.tasks.watchdog_tabu_stock_lock',
                'enabled': True,
                'description': 'Sprząta martwy lock sync_tabu_stock, jeśli worker padł w trakcie',
            },
        )
    except (ImportError, OperationalError, ProgrammingError):
        pass


def remove_watchdog_periodic_task(apps, schema_editor):
    try:
        from django_celery_beat.models import PeriodicTask

        PeriodicTask.objects.using('default').filter(name=TASK_NAME).delete()
    except (ImportError, OperationalError, ProgrammingError):
        pass


class Migration(migrations.Migration):

    dependencies = [
        ('tabu', '0012_saga_sagastep'),
    ]

    operations = [
        migrations.RunPython(create_watchdog_periodic_task,
                             remove_watchdog_periodic_task),
    ]
