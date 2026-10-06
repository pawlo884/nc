from django.db import migrations


def create_watchdog_periodic_task(apps, schema_editor):
    IntervalSchedule = apps.get_model('django_celery_beat', 'IntervalSchedule')
    PeriodicTask = apps.get_model('django_celery_beat', 'PeriodicTask')

    interval, _ = IntervalSchedule.objects.get_or_create(
        every=5,
        period='minutes',
    )

    PeriodicTask.objects.update_or_create(
        name='mada: watchdog import healthcheck (co 5 min)',
        defaults={
            'interval': interval,
            'task': 'mada.tasks.watchdog_import_healthcheck',
            'enabled': True,
            'description': 'Sprząta wpisy ApiSyncLog utknięte w running (#267)',
        }
    )


def remove_watchdog_periodic_task(apps, schema_editor):
    PeriodicTask = apps.get_model('django_celery_beat', 'PeriodicTask')
    PeriodicTask.objects.filter(
        name='mada: watchdog import healthcheck (co 5 min)'
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('mada', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_watchdog_periodic_task,
                             remove_watchdog_periodic_task),
    ]
