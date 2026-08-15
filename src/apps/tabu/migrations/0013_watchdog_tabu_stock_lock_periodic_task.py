from django.db import migrations


def create_watchdog_periodic_task(apps, schema_editor):
    IntervalSchedule = apps.get_model('django_celery_beat', 'IntervalSchedule')
    PeriodicTask = apps.get_model('django_celery_beat', 'PeriodicTask')

    interval, _ = IntervalSchedule.objects.get_or_create(
        every=5,
        period='minutes',
    )

    PeriodicTask.objects.update_or_create(
        name='tabu: watchdog sync_tabu_stock lock (co 5 min)',
        defaults={
            'interval': interval,
            'task': 'tabu.tasks.watchdog_tabu_stock_lock',
            'enabled': True,
            'description': 'Sprząta martwy lock sync_tabu_stock, jeśli worker padł w trakcie',
        }
    )


def remove_watchdog_periodic_task(apps, schema_editor):
    PeriodicTask = apps.get_model('django_celery_beat', 'PeriodicTask')
    PeriodicTask.objects.filter(
        name='tabu: watchdog sync_tabu_stock lock (co 5 min)'
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('tabu', '0012_saga_sagastep'),
    ]

    operations = [
        migrations.RunPython(create_watchdog_periodic_task,
                             remove_watchdog_periodic_task),
    ]
