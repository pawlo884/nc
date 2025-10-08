from django.db import migrations


def create_watchdog_periodic_task(apps, schema_editor):
    IntervalSchedule = apps.get_model('django_celery_beat', 'IntervalSchedule')
    PeriodicTask = apps.get_model('django_celery_beat', 'PeriodicTask')

    # Utwórz/albo pobierz interwał 5 minut
    interval, _ = IntervalSchedule.objects.get_or_create(
        every=5,
        period=IntervalSchedule.MINUTES,
    )

    # Utwórz/albo pobierz zadanie watchdog
    PeriodicTask.objects.update_or_create(
        name='matterhorn1: watchdog import healthcheck (co 5 min)',
        defaults={
            'interval': interval,
            'task': 'matterhorn1.tasks.watchdog_import_healthcheck',
            'enabled': True,
            'description': 'Sprząta stare running oraz ghost locki importu ITEMS',
        }
    )


def remove_watchdog_periodic_task(apps, schema_editor):
    PeriodicTask = apps.get_model('django_celery_beat', 'PeriodicTask')
    PeriodicTask.objects.filter(
        name='matterhorn1: watchdog import healthcheck (co 5 min)'
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('matterhorn1', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_watchdog_periodic_task, remove_watchdog_periodic_task),
    ]


