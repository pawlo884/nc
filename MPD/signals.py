from django.dispatch import receiver
from django.db.models.signals import post_delete, pre_delete, pre_save
from django.db import connections
from .models import Products, ProductVariants, ProductVariantsRetailPrice
import logging
import traceback
from matterhorn1.defs_db import delete_product_folder_from_bucket

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
                   # SET mapped_product_uid = False
                   # WHERE mapped_product_uid = %s
                    """, [instance.id])
        except Exception as e:
            print(f"Błąd aktualizacji mapped_product_uid: {e}")


@receiver(post_delete, sender=MDP)
def remove_variants_mapping_in_matterhorn(sender, instance, using, **kwargs):
    if using == "MasterProductDatabase":
        try:
            with connections['matterhorn'].cursor() as cursor:
                cursor.execute(
                    """
                    #UPDATE variants
                    #SET mapped_variant_uid = NULL
                    #WHERE mapped_variant_uid IN (
                    #    SELECT variant_id FROM product_variants
                    #    WHERE product_id = %s
                    #)
                    """, [instance.id])
        except Exception as e:
            print(f"Bład aktualizacji mapped_variant_uid: {e}")"""'''


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
    """Usuń mapowanie produktu z bazy matterhorn1 po usunięciu produktu z MPD"""
    # Sprawdź czy używamy bazy MPD (może być 'MPD' lub 'mpd' w zależności od konfiguracji)
    if using in ['MPD', 'mpd']:
        try:
            logger.info(
                f"Rozpoczęto usuwanie mapowań dla produktu MPD ID: {instance.id} (using: {using})")

            # Usunięcie mapowania produktu w matterhorn1
            with connections['matterhorn1'].cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE product 
                    SET mapped_product_uid = NULL,
                        is_mapped = False,
                        updated_at = NOW()
                    WHERE mapped_product_uid = %s
                    """, [instance.id]
                )
                products_updated = cursor.rowcount
                logger.info(
                    f"Zaktualizowano {products_updated} rekordów w tabeli product (mapped_product_uid = {instance.id})")
                
                # Sprawdź czy rzeczywiście zaktualizowano
                if products_updated == 0:
                    logger.warning(f"Nie znaleziono produktów z mapped_product_uid = {instance.id} w matterhorn1")
                else:
                    logger.info(f"✅ Pomyślnie usunięto mapowanie dla {products_updated} produktów")

            # Usunięcie wartości variant_id z mapped_variant_uid w tabeli product_variants w matterhorn1
            if hasattr(instance, 'variant_ids') and instance.variant_ids:
                with connections['matterhorn1'].cursor() as cursor:
                    placeholders = ', '.join(
                        ['%s'] * len(instance.variant_ids))
                    cursor.execute(f"""
                        UPDATE productvariant
                        SET mapped_variant_uid = NULL,
                            is_mapped = False,
                            updated_at = NOW()
                        WHERE mapped_variant_uid IN ({placeholders})
                        """, instance.variant_ids)
                    variants_updated = cursor.rowcount
                    logger.info(
                        f"Zaktualizowano {variants_updated} rekordów w tabeli product_variants")
            else:
                logger.info("Brak variant_id do usunięcia")

            logger.info(
                f"✅ Zakończono usuwanie mapowań dla produktu MPD ID: {instance.id}")

        except Exception as e:
            error_message = f"❌ Błąd podczas usuwania mapowań dla produktu MPD ID: {instance.id} - {str(e)}"
            logger.error(error_message)
            logger.error(traceback.format_exc())
            # Nie rzucamy wyjątku - pozwalamy Django kontynuować usuwanie
            # raise  # Odkomentuj jeśli chcesz zatrzymać usuwanie przy błędzie


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


@receiver(pre_save, sender=Products)
def update_product_timestamp(sender, instance, using, **kwargs):
    """Automatycznie aktualizuje updated_at przy każdym zapisie produktu"""
    if using == 'MPD':
        from django.utils import timezone
        instance.updated_at = timezone.now()


@receiver(pre_save, sender=ProductVariants)
def update_product_variant_timestamp(sender, instance, using, **kwargs):
    """Automatycznie aktualizuje updated_at przy każdym zapisie wariantu produktu"""
    if using == 'MPD':
        from django.utils import timezone
        instance.updated_at = timezone.now()


@receiver(pre_save, sender=ProductVariantsRetailPrice)
def update_retail_price_timestamp(sender, instance, using, **kwargs):
    """Automatycznie aktualizuje updated_at przy każdym zapisie ceny detalicznej"""
    if using == 'MPD':
        from django.utils import timezone
        instance.updated_at = timezone.now()
