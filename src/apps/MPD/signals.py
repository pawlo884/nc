from django.dispatch import receiver
from django.db.models.signals import post_delete, post_save, pre_delete, pre_save
from django.db import connections, transaction
from .models import Products, ProductVariants, ProductVariantsRetailPrice, ProductvariantsSources, Sources
import logging
import traceback
from matterhorn1.defs_db import delete_product_folder_from_bucket

logger = logging.getLogger('MPD')


def _get_connections_db():
    """Aliasy połączeń - dev używa zzz_, prod nie."""
    from django.conf import settings
    return (
        'zzz_MPD' if 'zzz_MPD' in settings.DATABASES else 'MPD',
        'zzz_matterhorn1' if 'zzz_matterhorn1' in settings.DATABASES else 'matterhorn1',
        'zzz_tabu' if 'zzz_tabu' in settings.DATABASES else 'tabu',
    )


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
    mpd_db = _get_connections_db()[0]
    db = using or getattr(instance, '_state', {}).db or 'default'
    if db != mpd_db and 'MPD' not in str(db):
        try:
            Products.objects.using(mpd_db).get(id=instance.id)
            db = mpd_db
        except (Products.DoesNotExist, Exception):
            return
    
    try:
        # Pobranie variant_id PRZED usunięciem produktu
        with connections[mpd_db].cursor() as master_cursor:
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
    mpd_db, mh_db, tabu_db = _get_connections_db()
    if db != mpd_db and 'MPD' not in str(db):
        # Sprawdź czy instancja pochodzi z bazy MPD
        try:
            Products.objects.using(mpd_db).get(id=instance.id)
            db = mpd_db
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
                with connections[mpd_db].cursor() as cursor:
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
        with connections[mh_db].cursor() as cursor:
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
            with connections[mh_db].cursor() as cursor:
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

        # Usunięcie mapped_product_uid w Tabu (tabu_product_detail)
        from django.conf import settings
        if tabu_db in settings.DATABASES:
            try:
                with connections[tabu_db].cursor() as cursor:
                    cursor.execute(
                        """
                        UPDATE tabu_product_detail
                        SET mapped_product_uid = NULL
                        WHERE mapped_product_uid = %s
                        """, [instance.id]
                    )
                    tabu_updated = cursor.rowcount
                    if tabu_updated:
                        logger.info(
                            f"Zaktualizowano {tabu_updated} rekordów w tabu_product_detail (mapped_product_uid = {instance.id})")
            except Exception as e:
                logger.warning(f"Nie udało się zaktualizować Tabu dla produktu MPD {instance.id}: {e}")

        logger.info(
            f"Zakończono usuwanie mapowań dla produktu MPD ID: {instance.id}")

    except Exception as e:
        error_message = f"Błąd podczas usuwania mapowań dla produktu MPD ID: {instance.id} - {str(e)}"
        logger.error(error_message)
        logger.error(traceback.format_exc())
        # Nie rzucamy wyjątku, aby nie blokować usuwania produktu


@receiver(pre_delete, sender=Products)
def product_pre_delete(sender, instance, using=None, **kwargs):
    mpd_db = _get_connections_db()[0]
    db = using or getattr(instance, '_state', {}).db or 'default'
    if db != mpd_db and 'MPD' not in str(db):
        try:
            Products.objects.using(mpd_db).get(id=instance.id)
            db = mpd_db
        except (Products.DoesNotExist, Exception):
            return
    
    message = f"Przed usunięciem produktu MPD: {instance.id} - {instance.name}"
    logger.info(message)


@receiver(post_delete, sender=Products)
def product_post_delete(sender, instance, using=None, **kwargs):
    mpd_db = _get_connections_db()[0]
    db = using or getattr(instance, '_state', {}).db or 'default'
    if db != mpd_db and 'MPD' not in str(db):
        try:
            Products.objects.using(mpd_db).get(id=instance.id)
            db = mpd_db
        except (Products.DoesNotExist, Exception):
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
    mpd_db = _get_connections_db()[0]
    if using == mpd_db:
        from django.utils import timezone
        instance.updated_at = timezone.now()


@receiver(pre_save, sender=ProductVariants)
def update_product_variant_timestamp(sender, instance, using, **kwargs):
    """Automatycznie aktualizuje updated_at przy każdym zapisie wariantu produktu"""
    mpd_db = _get_connections_db()[0]
    if using == mpd_db:
        from django.utils import timezone
        instance.updated_at = timezone.now()


@receiver(pre_save, sender=ProductVariantsRetailPrice)
def update_retail_price_timestamp(sender, instance, using, **kwargs):
    """Automatycznie aktualizuje updated_at przy każdym zapisie ceny detalicznej"""
    mpd_db = _get_connections_db()[0]
    if using == mpd_db:
        from django.utils import timezone
        instance.updated_at = timezone.now()


# Task linkowania wariantów po EAN: sygnał na Products (created=True) + on_commit; Matterhorn jawnie na koniec create_mpd_variants.


@receiver(post_save, sender=Products)
def on_product_created_schedule_link_task(sender, instance, created, using=None, **kwargs):
    """
    Przy utworzeniu nowego produktu MPD: po commicie transakcji wyślij task linkowania
    (po EAN) dla każdego źródła, które ma warianty tego produktu. Działa z Tabu (product
    + warianty w jednej transakcji); Matterhorn wywołuje task jawnie w create_mpd_variants.
    """
    if not created:
        return
    mpd_db = _get_connections_db()[0]
    db = using or getattr(instance, '_state', {}).db or 'default'
    if db != mpd_db and 'MPD' not in str(db):
        return
    product_id = instance.id

    def _send_link_tasks():
        from MPD.tasks import link_variants_from_other_sources_task
        source_ids = list(
            ProductvariantsSources.objects.using(mpd_db)
            .filter(variant__product_id=product_id)
            .values_list('source_id', flat=True)
            .distinct()
        )
        for source_id in source_ids:
            link_variants_from_other_sources_task.apply_async(
                args=(product_id, source_id),
                queue='default',
            )
            logger.info(
                "Produkt MPD %s utworzony - wysłano task linkowania (exclude source %s)",
                product_id, source_id,
            )

    transaction.on_commit(_send_link_tasks, using=mpd_db)


@receiver(post_save, sender=Sources)
def on_new_source_created(sender, instance, created, using=None, **kwargs):
    """
    Automatyczne dopinanie wariantów z nowej hurtowni do MPD (po EAN).
    Uruchamiane przy dodaniu nowego źródła (Sources) - tylko gdy istnieje adapter.
    """
    if not created:
        return
    mpd_db = _get_connections_db()[0]
    db = using or getattr(instance, '_state', {}).db or 'default'
    if db != mpd_db and 'MPD' not in str(db):
        return
    try:
        from MPD.source_adapters.registry import get_adapter_for_source
        from MPD.tasks import link_all_products_to_new_source_task
        if get_adapter_for_source(instance.id):
            link_all_products_to_new_source_task.apply_async(
                args=(instance.id,),
                queue='default',
            )
            logger.info(
                "Nowe źródło %s (id=%s) - wysłano task dopinania wariantów po EAN",
                instance.name, instance.id
            )
    except Exception as e:
        logger.warning("Błąd uruchomienia tasku dla nowego źródła %s: %s", instance.id, e)
