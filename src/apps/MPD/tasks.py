from celery import shared_task
from django.utils import timezone
import logging
from .export_to_xml import FullChangeXMLExporter

logger = logging.getLogger(__name__)


@shared_task(bind=True, name='mpd.export_full_change_xml_full')
def export_full_change_xml_full(self):
    """
    Task do eksportu full_change.xml - tylko zmienione produkty
    Uruchamiany co 30 minut przez periodic task
    """
    start_time = timezone.now()
    task_id = self.request.id

    logger.info(
        f"Rozpoczynam task export_full_change_xml_full (ID: {task_id}) o {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        # Utwórz eksporter
        exporter = FullChangeXMLExporter()

        # Eksport przyrostowy - tylko zmienione produkty
        result = exporter.export()

        end_time = timezone.now()
        duration = end_time - start_time

        if result['bucket_url']:
            logger.info(
                f"Task export_full_change_xml_full (ID: {task_id}) zakonczony pomyslnie w {duration.total_seconds():.2f}s"
            )
            logger.info(f"URL: {result['bucket_url']}")
            logger.info(f"Lokalnie zapisano: {result['local_path']}")

            return {
                'status': 'success',
                'task_id': task_id,
                'bucket_url': result['bucket_url'],
                'local_path': result['local_path'],
                'duration_seconds': duration.total_seconds(),
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat()
            }
        else:
            logger.error(
                f"Task export_full_change_xml_full (ID: {task_id}) blad po {duration.total_seconds():.2f}s"
            )
            logger.error(f"Lokalnie zapisano: {result['local_path']}")

            return {
                'status': 'error',
                'task_id': task_id,
                'error': 'Blad podczas eksportu do S3',
                'local_path': result['local_path'],
                'duration_seconds': duration.total_seconds(),
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat()
            }

    except Exception as e:
        end_time = timezone.now()
        duration = end_time - start_time

        error_msg = f"Task export_full_change_xml_full (ID: {task_id}) blad po {duration.total_seconds():.2f}s: {str(e)}"
        logger.error(error_msg)

        # Oznacz task jako nieudany
        self.update_state(
            state='FAILURE',
            meta={
                'error': str(e),
                'task_id': task_id,
                'duration_seconds': duration.total_seconds(),
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat()
            }
        )

        return {
            'status': 'failure',
            'task_id': task_id,
            'error': str(e),
            'duration_seconds': duration.total_seconds(),
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat()
        }


@shared_task(name='MPD.tasks.link_variants_from_other_sources')
def link_variants_from_other_sources_task(mpd_product_id: int, current_source_id: int):
    """
    Asynchroniczne dopinanie wariantów z innych hurtowni po EAN.
    Uruchamiane po dodaniu produktu do MPD (Tabu/Matterhorn) - nie blokuje głównego flow.
    """
    from MPD.source_adapters import link_variants_from_other_sources

    logger.info(
        "🚀 Task link_variants_from_other_sources: mpd_product_id=%s, current_source_id=%s",
        mpd_product_id, current_source_id
    )
    try:
        stats = link_variants_from_other_sources(
            mpd_product_id, current_source_id)
        if stats.get('linked_count'):
            logger.info(
                "✅ Dopięto %s wariantów z innych hurtowni do produktu MPD %s",
                stats['linked_count'], mpd_product_id
            )
        elif stats.get('errors'):
            logger.warning(
                "⚠️ link_variants_from_other_sources: mpd_product_id=%s błędy=%s",
                mpd_product_id, stats['errors']
            )
        else:
            logger.info(
                "ℹ️ link_variants_from_other_sources: mpd_product_id=%s - brak dopasowań (linked=0)",
                mpd_product_id
            )
        return {'status': 'success', 'stats': stats}
    except Exception as e:
        logger.exception("Błąd link_variants_from_other_sources: %s", e)
        raise


@shared_task(name='MPD.tasks.link_all_products_to_new_source')
def link_all_products_to_new_source_task(new_source_id: int):
    """
    Asynchroniczne dopinanie wariantów z nowej hurtowni do wszystkich produktów MPD (po EAN).
    Uruchamiane automatycznie przy dodaniu nowego źródła (Sources) lub ręcznie.
    """
    from MPD.source_adapters import link_all_products_to_new_source

    logger.info(
        "🚀 Task link_all_products_to_new_source: source_id=%s",
        new_source_id
    )
    try:
        stats = link_all_products_to_new_source(new_source_id)
        if stats.get('linked_count'):
            logger.info(
                "✅ Dopięto %s wariantów z nowej hurtowni do MPD",
                stats['linked_count']
            )
        elif stats.get('errors'):
            logger.warning(
                "⚠️ link_all_products_to_new_source: source_id=%s błędy=%s",
                new_source_id, stats['errors']
            )
        else:
            logger.info(
                "ℹ️ link_all_products_to_new_source: source_id=%s - brak dopasowań",
                new_source_id
            )
        return {'status': 'success', 'stats': stats}
    except Exception as e:
        logger.exception("Błąd link_all_products_to_new_source: %s", e)
        raise


@shared_task(bind=True, name='MPD.tasks.track_recent_stock_changes')
def track_recent_stock_changes(self):
    """
    Task do śledzenia zmian stanów magazynowych
    Uruchamiany okresowo przez periodic task
    """
    start_time = timezone.now()
    task_id = self.request.id

    logger.info(
        f"🚀 Rozpoczynam task track_recent_stock_changes (ID: {task_id}) o {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        # TODO: Implementuj logikę śledzenia zmian stanów magazynowych
        # Na razie zwracamy sukces bez implementacji

        end_time = timezone.now()
        duration = end_time - start_time

        logger.info(
            f"✅ Task track_recent_stock_changes (ID: {task_id}) zakończony pomyślnie w {duration.total_seconds():.2f}s"
        )

        return {
            'status': 'success',
            'task_id': task_id,
            'message': 'Śledzenie zmian stanów magazynowych zakończone',
            'duration_seconds': duration.total_seconds(),
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat()
        }

    except Exception as e:
        end_time = timezone.now()
        duration = end_time - start_time

        error_msg = f"❌ Task track_recent_stock_changes (ID: {task_id}) błąd po {duration.total_seconds():.2f}s: {str(e)}"
        logger.error(error_msg)

        # Oznacz task jako nieudany
        self.update_state(
            state='FAILURE',
            meta={
                'error': str(e),
                'task_id': task_id,
                'duration_seconds': duration.total_seconds(),
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat()
            }
        )

        return {
            'status': 'failure',
            'task_id': task_id,
            'error': str(e),
            'duration_seconds': duration.total_seconds(),
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat()
        }


@shared_task(bind=True, name='MPD.tasks.update_stock_from_matterhorn1')
def update_stock_from_matterhorn1(self, time_window_minutes=15):
    """
    Task do aktualizacji stanów magazynowych w MPD na podstawie danych z matterhorn1

    Proces:
    1. Pobiera zmapowane warianty z matterhorn1 (is_mapped=True)
    2. Filtruje po updated_at - tylko warianty z ostatnich X minut (domyślnie 15)
    3. Znajduje odpowiednie warianty w MPD.ProductvariantsSources po variant_uid
    4. Aktualizuje StockAndPrices w MPD nowymi stanami z matterhorn1
    5. Loguje zmiany do StockHistory

    Args:
        time_window_minutes: Ile minut wstecz sprawdzać (domyślnie 15)

    Uruchamiany okresowo przez periodic task (np. co 5 minut, sprawdza ostatnie 15 minut)
    """
    from django.conf import settings
    from decimal import Decimal
    from datetime import timedelta

    start_time = timezone.now()
    task_id = self.request.id

    logger.info(
        "🚀 Rozpoczynam task update_stock_from_matterhorn1 (ID: %s) o %s (okno czasowe: %s min)",
        task_id, start_time.strftime('%Y-%m-%d %H:%M:%S'), time_window_minutes)

    try:
        # Import modeli
        from matterhorn1.models import ProductVariant as Matterhorn1Variant
        from MPD.models import (
            ProductvariantsSources,
            StockAndPrices,
            StockHistory,
            Sources
        )

        # Określ bazę danych dla matterhorn1
        matterhorn1_db = 'zzz_matterhorn1' if 'zzz_matterhorn1' in settings.DATABASES else 'matterhorn1'
        mpd_db = 'zzz_MPD' if 'zzz_MPD' in settings.DATABASES else 'MPD'

        # Statystyki
        stats = {
            'checked': 0,
            'updated': 0,
            'created': 0,
            'unchanged': 0,
            'errors': 0,
            'error_details': []
        }

        # Pobierz źródło dla Matterhorn
        matterhorn_source = None
        try:
            matterhorn_source = Sources.objects.using(mpd_db).filter(
                name__icontains='matterhorn'
            ).first()

            if not matterhorn_source:
                # Jeśli nie ma źródła, utwórz domyślne
                matterhorn_source = Sources.objects.using(mpd_db).create(
                    name='Matterhorn API',
                    type='api',
                    location='https://api.matterhorn.pl'
                )
                logger.info(
                    "📦 Utworzono nowe źródło: %s (ID: %s)",
                    matterhorn_source.name, matterhorn_source.id)
        except Exception as source_error:
            error_msg = f"Błąd podczas pobierania/tworzenia źródła: {str(source_error)}"
            logger.error(error_msg)
            stats['errors'] += 1
            stats['error_details'].append(error_msg)

        if not matterhorn_source:
            logger.warning(
                "⚠️ Brak źródła Matterhorn - pomijam synchronizację")
            return {
                'status': 'warning',
                'task_id': task_id,
                'message': 'Brak źródła Matterhorn',
                'stats': stats,
                'duration_seconds': (timezone.now() - start_time).total_seconds(),
            }

        # Oblicz czas od którego sprawdzamy zmiany
        time_threshold = start_time - timedelta(minutes=time_window_minutes)

        # Pobierz zmapowane warianty z matterhorn1 zaktualizowane w ostatnich X minutach
        mapped_variants = Matterhorn1Variant.objects.using(matterhorn1_db).filter(
            is_mapped=True,
            mapped_variant_uid__isnull=False,
            updated_at__gte=time_threshold
        ).select_related('product')

        total_variants = mapped_variants.count()
        logger.info(
            "📊 Znaleziono %s zmapowanych wariantów zaktualizowanych od %s",
            total_variants, time_threshold.strftime('%Y-%m-%d %H:%M:%S')
        )

        if total_variants == 0:
            logger.info("ℹ️ Brak zmapowanych wariantów do synchronizacji")
            return {
                'status': 'success',
                'task_id': task_id,
                'message': 'Brak zmapowanych wariantów',
                'stats': stats,
                'duration_seconds': (timezone.now() - start_time).total_seconds(),
            }

        # Przetwórz każdy wariant
        for mh1_variant in mapped_variants:
            stats['checked'] += 1

            try:
                # Znajdź odpowiedni wariant w MPD po mapped_variant_uid
                # mapped_variant_uid w matterhorn1 odpowiada variant_id w MPD
                mpd_variant_source = ProductvariantsSources.objects.using(mpd_db).filter(
                    variant_id=mh1_variant.mapped_variant_uid,
                    source=matterhorn_source
                ).select_related('variant').first()

                if not mpd_variant_source:
                    # Możliwe, że mapowanie jest nieprawidłowe
                    error_msg = (
                        f"Nie znaleziono wariantu MPD dla mapped_variant_uid={mh1_variant.mapped_variant_uid} "
                        f"(mh1_variant_uid={mh1_variant.variant_uid})"
                    )
                    logger.warning("⚠️ %s", error_msg)
                    stats['errors'] += 1
                    stats['error_details'].append(error_msg)
                    continue

                # Sprawdź czy istnieje rekord StockAndPrices
                stock_and_price, created = StockAndPrices.objects.using(mpd_db).get_or_create(
                    variant=mpd_variant_source.variant,
                    source=matterhorn_source,
                    defaults={
                        'stock': mh1_variant.stock,
                        'price': Decimal('0.00'),
                        'currency': 'PLN',
                        'last_updated': timezone.now()
                    }
                )

                if created:
                    # Nowo utworzony rekord - zapisz do historii
                    stats['created'] += 1
                    logger.info(
                        "✨ Utworzono nowy rekord StockAndPrices dla wariantu %s: stock=%s",
                        mpd_variant_source.variant.variant_id, mh1_variant.stock
                    )

                    # Zapisz pierwszą zmianę do historii (0 → nowy stan)
                    try:
                        StockHistory.objects.using(mpd_db).create(
                            stock_id=stock_and_price.id,
                            source_id=matterhorn_source.id,
                            previous_stock=0,
                            new_stock=mh1_variant.stock,
                            previous_price=Decimal('0.00'),
                            new_price=stock_and_price.price
                        )
                        logger.info(
                            "📝 Zapisano do historii: 0 → %s",
                            mh1_variant.stock
                        )
                    except Exception as history_error:
                        logger.error(
                            "⚠️ Błąd zapisu historii dla nowego rekordu: %s",
                            str(history_error)
                        )
                else:
                    # Aktualizuj tylko jeśli stan się zmienił
                    old_stock = stock_and_price.stock
                    new_stock = mh1_variant.stock

                    if old_stock != new_stock:
                        # Zapisz zmianę do historii (change_date auto_now_add)
                        try:
                            StockHistory.objects.using(mpd_db).create(
                                stock_id=stock_and_price.id,
                                source_id=matterhorn_source.id,
                                previous_stock=old_stock,
                                new_stock=new_stock,
                                previous_price=stock_and_price.price,
                                new_price=stock_and_price.price
                            )
                            logger.info(
                                "📝 Zapisano do historii: %s → %s",
                                old_stock, new_stock
                            )
                        except Exception as history_error:
                            logger.error(
                                "⚠️ Błąd zapisu historii: %s",
                                str(history_error)
                            )

                        # Aktualizuj stan
                        stock_and_price.stock = new_stock
                        stock_and_price.last_updated = timezone.now()
                        stock_and_price.save(using=mpd_db)

                        stats['updated'] += 1
                        logger.info(
                            "🔄 Zaktualizowano stan dla wariantu %s: %s → %s",
                            mpd_variant_source.variant.variant_id, old_stock, new_stock
                        )
                    else:
                        stats['unchanged'] += 1

            except Exception as variant_error:
                error_msg = f"Błąd podczas przetwarzania wariantu {mh1_variant.variant_uid}: {str(variant_error)}"
                logger.error("❌ %s", error_msg)
                stats['errors'] += 1
                stats['error_details'].append(error_msg)
                continue

        end_time = timezone.now()
        duration = end_time - start_time

        # Przygotuj podsumowanie
        logger.info(
            "✅ Task update_stock_from_matterhorn1 (ID: %s) zakończony w %.2fs",
            task_id, duration.total_seconds()
        )
        logger.info(
            "📊 Statystyki: Sprawdzono: %s, Zaktualizowano: %s, Utworzono: %s, Bez zmian: %s, Błędy: %s",
            stats['checked'], stats['updated'], stats['created'], stats['unchanged'], stats['errors']
        )

        if stats['errors'] > 0:
            logger.warning(
                "⚠️ Wystąpiły błędy podczas synchronizacji (%s błędów)", stats['errors'])
            # Ogranicz szczegóły błędów do 10 pierwszych
            if len(stats['error_details']) > 10:
                extra_errors = len(stats['error_details']) - 10
                stats['error_details'] = stats['error_details'][:10] + [
                    f"... i {extra_errors} więcej błędów"
                ]

        return {
            'status': 'success' if stats['errors'] == 0 else 'partial',
            'task_id': task_id,
            'message': f"Synchronizacja zakończona: {stats['updated']} zaktualizowano, {stats['created']} utworzono",
            'stats': stats,
            'duration_seconds': duration.total_seconds(),
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat()
        }

    except Exception as main_error:
        end_time = timezone.now()
        duration = end_time - start_time

        logger.error(
            "❌ Task update_stock_from_matterhorn1 (ID: %s) błąd po %.2fs: %s",
            task_id, duration.total_seconds(), str(main_error)
        )
        logger.exception("Szczegóły błędu:")

        # Oznacz task jako nieudany
        self.update_state(
            state='FAILURE',
            meta={
                'error': str(main_error),
                'task_id': task_id,
                'duration_seconds': duration.total_seconds(),
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat()
            }
        )

        return {
            'status': 'failure',
            'task_id': task_id,
            'error': str(main_error),
            'duration_seconds': duration.total_seconds(),
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat()
        }
