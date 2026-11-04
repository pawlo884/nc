"""Korekta danych: ujemne `TabuProductVariant.store` (np. -1 z API Tabu) -> 0.

Ujemny stan w bazie wywalał `sync_tabu_stock` (CheckViolation na
`tabu_stock_history.old_stock`) i trafiał jako ujemny stock do MPD.
Od teraz sync zapisuje stan przez `parse_store` (clamp do 0); ta migracja
czyści to, co zostało zapisane wcześniej. `store_total` produktów też.
"""
from django.db import migrations


def clamp_negative_store(apps, schema_editor):
    db = schema_editor.connection.alias
    Variant = apps.get_model('tabu', 'TabuProductVariant')
    Product = apps.get_model('tabu', 'TabuProduct')
    Variant.objects.using(db).filter(store__lt=0).update(store=0)
    Product.objects.using(db).filter(store_total__lt=0).update(store_total=0)


class Migration(migrations.Migration):

    dependencies = [
        ('tabu', '0013_watchdog_tabu_stock_lock_periodic_task'),
    ]

    operations = [
        migrations.RunPython(clamp_negative_store, migrations.RunPython.noop),
    ]
