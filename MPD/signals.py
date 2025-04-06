from django.dispatch import receiver
from django.db.models.signals import post_delete, pre_delete
from django.db import connections
from .models import MPD


'''
@receiver(post_delete, sender=MDP)
def remove_product_mapping_in_matterhorn(sender, instance, using, **kwargs):
    if using == 'MasterProductDatabase':
        try:
            with connections['matterhorn'].cursor() as cursor:
                cursor.execute(
                    """
                   # UPDATE products
                   # SET mapped_product_id = NULL
                   # WHERE mapped_product_id = %s
                    """, [instance.id])
        except Exception as e:
            print(f"Błąd aktualizacji mapped_product_id: {e}")


@receiver(post_delete, sender=MDP)
def remove_variants_mapping_in_matterhorn(sender, instance, using, **kwargs):
    if using == "MasterProductDatabase":
        try:
            with connections['matterhorn'].cursor() as cursor:
                cursor.execute(
                    """
                    #UPDATE variants
                    #SET mapped_variant_id = NULL
                    #WHERE mapped_variant_id IN (
                    #    SELECT variant_id FROM product_variants
                    #    WHERE product_id = %s
                    #)
                    """, [instance.id])
        except Exception as e:
            print(f"Bład aktualizacji mapped_variant_id: {e}")"""'''


@receiver(pre_delete, sender=MPD)
def capture_variant_ids(sender, instance, using, **kwargs):
    if using == 'MPD':
        try:
            # Pobranie variant_id PRZED usunięciem produktu
            with connections['MPD'].cursor() as master_cursor:
                master_cursor.execute(
                    """
                    SELECT variant_id FROM product_variants
                    WHERE product_id = %s
                    """, [instance.id]
                )
                instance.variant_ids = [row[0] for row in master_cursor.fetchall()]
            
            print(f"Pobrane variant_id przed usunięciem: {instance.variant_ids}")
        except Exception as e:
            print(f"Błąd pobierania variant_id: {e}")

@receiver(post_delete, sender=MPD)
def remove_mapping_in_matterhorn(sender, instance, using, **kwargs):
    if using == 'MPD':
        try:
            # Usunięcie produktu z tabeli products w matterhorn
            with connections['matterhorn'].cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE products
                    SET mapped_product_id = NULL
                    WHERE mapped_product_id = %s
                    """, [instance.id]
                )
            
            # Usunięcie wartości variant_id z mapped_variant_id w tabeli variants w matterhorn
            if hasattr(instance, 'variant_ids') and instance.variant_ids:
                with connections['matterhorn'].cursor() as cursor:
                    placeholders = ', '.join(['%s'] * len(instance.variant_ids))
                    cursor.execute(f"""
                        UPDATE variants
                        SET mapped_variant_id = NULL
                        WHERE mapped_variant_id IN ({placeholders})
                        """, instance.variant_ids)
                print(f"Zaktualizowano {cursor.rowcount} rekordów w variants.")
            else:
                print("Brak variant_id do usunięcia.")
        
        except Exception as e:
            import traceback
            print(f"Błąd aktualizacji powiązań: {e}")
            print(traceback.format_exc())
