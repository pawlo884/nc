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
def capture_variant_ids(sender, instance, using=None, **kwargs):
    # Sprawdź czy to produkt z bazy MPD
    db = using or getattr(instance, '_state', {}).db or 'default'
    if db != 'MPD' and 'MPD' not in str(db):
        try:
            # Sprawdź czy produkt istnieje w bazie MPD
            Products.objects.using('MPD').get(id=instance.id)
            db = 'MPD'
        except (Products.DoesNotExist, Exception):
            return
    
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

        logger.info(
            f"Pobrane variant_id przed usunięciem produktu {instance.id}: {instance.variant_ids}")
    except Exception as e:
        logger.warning(f"Błąd pobierania variant_id dla produktu {instance.id}: {e}")
        instance.variant_ids = []


@receiver(post_delete, sender=Products)
def remove_mapping_in_matterhorn(sender, instance, using=None, **kwargs):
    # Sprawdź czy to produkt z bazy MPD - sprawdź using lub _state.db
    db = using or getattr(instance, '_state', {}).db or 'default'
    if db != 'MPD' and 'MPD' not in str(db):
        # Sprawdź czy instancja pochodzi z bazy MPD przez sprawdzenie czy istnieje w MPD
        try:
            # Próbuj znaleźć produkt w bazie MPD
            Products.objects.using('MPD').get(id=instance.id)
            db = 'MPD'
        except (Products.DoesNotExist, Exception):
            logger.debug(f"Produkt {instance.id} nie jest z bazy MPD, pomijam signal")
            return
    
    try:
        logger.info(
            f"Rozpoczęto usuwanie mapowań dla produktu MPD ID: {instance.id}")

        # Pobierz variant_ids przed usunięciem (jeśli nie zostały już pobrane)
        variant_ids = []
        if not hasattr(instance, 'variant_ids') or not instance.variant_ids:
            try:
                with connections['MPD'].cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT variant_id FROM product_variants
                        WHERE product_id = %s
                        """, [instance.id]
                    )
                    variant_ids = [row[0] for row in cursor.fetchall()]
            except Exception as e:
                logger.warning(f"Nie udało się pobrać variant_ids: {e}")
        else:
            variant_ids = instance.variant_ids

        # Usunięcie produktu z tabeli products w matterhorn1
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

        # Usunięcie wartości variant_id z mapped_variant_uid w tabeli product_variants w matterhorn1
        if variant_ids:
            with connections['matterhorn1'].cursor() as cursor:
                placeholders = ', '.join(['%s'] * len(variant_ids))
                cursor.execute(f"""
                    UPDATE productvariant
                    SET mapped_variant_uid = NULL,
                        is_mapped = False,
                        updated_at = NOW()
                    WHERE mapped_variant_uid IN ({placeholders})
                    """, variant_ids)
                variants_updated = cursor.rowcount
                logger.info(
                    f"Zaktualizowano {variants_updated} rekordów w tabeli product_variants (variant_ids: {variant_ids})")
        else:
            logger.info("Brak variant_id do usunięcia")

        logger.info(
            f"Zakończono usuwanie mapowań dla produktu MPD ID: {instance.id}")

    except Exception as e:
        error_message = f"Błąd podczas usuwania mapowań dla produktu MPD ID: {instance.id} - {str(e)}"
        logger.error(error_message)
        logger.error(traceback.format_exc())
        # Nie rzucamy wyjątku, aby nie blokować usuwania produktu


@receiver(pre_delete, sender=Products)
def product_pre_delete(sender, instance, using=None, **kwargs):
    # Sprawdź czy to produkt z bazy MPD
    db = using or getattr(instance, '_state', {}).db or 'default'
    if db != 'MPD' and 'MPD' not in str(db):
        try:
            # Sprawdź czy produkt istnieje w bazie MPD
            Products.objects.using('MPD').get(id=instance.id)
            db = 'MPD'
        except (Products.DoesNotExist, Exception):
            return
    
    message = f"Przed usunięciem produktu MPD: {instance.id} - {instance.name}"
    logger.info(message)


@receiver(post_delete, sender=Products)
def product_post_delete(sender, instance, using=None, **kwargs):
    # Sprawdź czy to produkt z bazy MPD
    db = using or getattr(instance, '_state', {}).db or 'default'
    if db != 'MPD' and 'MPD' not in str(db):
        try:
            # Sprawdź czy produkt istnieje w bazie MPD (jeśli jeszcze istnieje)
            Products.objects.using('MPD').get(id=instance.id)
            db = 'MPD'
        except (Products.DoesNotExist, Exception):
            # Produkt już usunięty lub nie z bazy MPD
            return
    
    message = f"Po usunięciu produktu MPD: {instance.id} - {instance.name}"
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
