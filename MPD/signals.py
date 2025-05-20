from django.dispatch import receiver
from django.db.models.signals import post_delete, pre_delete
from django.db import connections
from .models import Products
import logging
import traceback
from matterhorn.defs_db import delete_product_folder_from_bucket

logger = logging.getLogger('MPD')


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


@receiver(pre_delete, sender=Products)
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
                instance.variant_ids = [row[0]
                                        for row in master_cursor.fetchall()]

            print(
                f"Pobrane variant_id przed usunięciem: {instance.variant_ids}")
        except Exception as e:
            print(f"Błąd pobierania variant_id: {e}")


@receiver(post_delete, sender=Products)
def remove_mapping_in_matterhorn(sender, instance, using, **kwargs):
    if using == 'MPD':
        try:
            logger.info(
                f"Rozpoczęto usuwanie mapowań dla produktu MPD ID: {instance.id}")

            # Usunięcie produktu z tabeli products w matterhorn
            with connections['matterhorn'].cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE products 
                    SET mapped_product_id = NULL,
                        is_mapped = NULL,
                        last_updated = NOW()
                    WHERE mapped_product_id = %s
                    """, [instance.id]
                )
                products_updated = cursor.rowcount
                logger.info(
                    f"Zaktualizowano {products_updated} rekordów w tabeli products")

            # Usunięcie wartości variant_id z mapped_variant_id w tabeli variants w matterhorn
            if hasattr(instance, 'variant_ids') and instance.variant_ids:
                with connections['matterhorn'].cursor() as cursor:
                    placeholders = ', '.join(
                        ['%s'] * len(instance.variant_ids))
                    cursor.execute(f"""
                        UPDATE variants
                        SET mapped_variant_id = NULL,
                            is_mapped = NULL,
                            last_updated = NOW()
                        WHERE mapped_variant_id IN ({placeholders})
                        """, instance.variant_ids)
                    variants_updated = cursor.rowcount
                    logger.info(
                        f"Zaktualizowano {variants_updated} rekordów w tabeli variants")
            else:
                logger.info("Brak variant_id do usunięcia")

            logger.info(
                f"Zakończono usuwanie mapowań dla produktu MPD ID: {instance.id}")

        except Exception as e:
            error_message = f"Błąd podczas usuwania mapowań dla produktu MPD ID: {instance.id} - {str(e)}"
            logger.error(error_message)
            logger.error(traceback.format_exc())
            raise  # Ponownie rzucamy wyjątek, aby Django wiedział o błędzie


@receiver(pre_delete, sender=Products)
def product_pre_delete(sender, instance, **kwargs):
    message = f"Przed usunięciem produktu: {instance.id} - {instance.name}"
    print(message)
    logger.info(message)


@receiver(post_delete, sender=Products)
def product_post_delete(sender, instance, **kwargs):
    message = f"Po usunięciu produktu: {instance.id} - {instance.name}"
    print(message)
    logger.info(message)
    # Usuwanie folderu z bucketa
    try:
        delete_product_folder_from_bucket(instance.id)
    except Exception as e:
        logger.error(
            f"Błąd podczas usuwania folderu z bucketa dla produktu {instance.id}: {e}")
