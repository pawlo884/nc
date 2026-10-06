"""
Most stanów magazynowych: hurtownia (warianty `is_mapped=True`) -> MPD.StockAndPrices.

Współdzielone przez `MPD.tasks.update_stock_from_tabu` / `update_stock_from_mada`
(#270). `update_stock_from_matterhorn1` ma własną, starszą, nietestowaną
implementację wprost w `MPD/tasks.py` - zostawiona bez zmian, żeby nie
ryzykować regresji czegoś co już działa na produkcji bez siatki testów.

Dlaczego bez okna czasowego (inaczej niż matterhorn1): TabuProductVariant nie
ma pola `updated_at`, więc nie ma po czym filtrować "co się zmieniło od X".
Zamiast okna bierzemy WSZYSTKIE zmapowane (`is_mapped=True`) warianty przy
każdym uruchomieniu - `sync_stock_bridge` i tak nie zapisuje nic (ani do
StockAndPrices, ani do StockHistory) gdy stan się nie zmienił, więc dla
zbioru ograniczonego do już-zlinkowanych wariantów to tanie.
"""
import logging
from decimal import Decimal
from typing import Iterable, Tuple

from django.utils import timezone

logger = logging.getLogger(__name__)


def sync_stock_bridge(
    mapped_stock_pairs: Iterable[Tuple[int, int]],
    *,
    source_name: str,
    source_type_default: str,
    source_location_default: str,
    mpd_db: str,
) -> dict:
    """
    mapped_stock_pairs: (mapped_variant_uid, current_stock) dla wariantów
    hurtowni z is_mapped=True - mapped_variant_uid odpowiada
    ProductvariantsSources.variant_id w MPD.

    Źródło (`Sources`) dopasowane po dokładnej nazwie `source_name` (ten sam
    rekord co przy linkowaniu w `tabu/services.py` / `mada/services.py`),
    tworzone przy braku. Cena nie jest tu ruszana (price=0.00 przy tworzeniu -
    jak w matterhorn1 - idzie innym torem); tylko stock + StockHistory.

    Zwraca stats: {'checked', 'updated', 'created', 'unchanged', 'errors', 'error_details'}.
    """
    from MPD.models import ProductvariantsSources, StockAndPrices, StockHistory, Sources

    stats = {
        'checked': 0, 'updated': 0, 'created': 0, 'unchanged': 0,
        'errors': 0, 'error_details': [],
    }

    source, source_created = Sources.objects.using(mpd_db).get_or_create(
        name=source_name,
        defaults={'type': source_type_default, 'location': source_location_default},
    )
    if source_created:
        logger.info("📦 Utworzono nowe źródło: %s (ID: %s)", source.name, source.id)

    now = timezone.now()
    for mapped_variant_uid, current_stock in mapped_stock_pairs:
        stats['checked'] += 1
        try:
            pvs = ProductvariantsSources.objects.using(mpd_db).filter(
                variant_id=mapped_variant_uid, source=source,
            ).select_related('variant').first()
            if not pvs:
                stats['errors'] += 1
                stats['error_details'].append(
                    f'Brak ProductvariantsSources dla variant_id={mapped_variant_uid} '
                    f'(source={source_name})'
                )
                continue

            sap, created = StockAndPrices.objects.using(mpd_db).get_or_create(
                variant=pvs.variant, source=source,
                defaults={
                    'stock': current_stock, 'price': Decimal('0.00'),
                    'currency': 'PLN', 'last_updated': now,
                },
            )
            if created:
                stats['created'] += 1
                StockHistory.objects.using(mpd_db).create(
                    stock_id=sap.id, source_id=source.id,
                    previous_stock=0, new_stock=current_stock,
                    previous_price=Decimal('0.00'), new_price=sap.price,
                )
            elif sap.stock != current_stock:
                # Warunkowy UPDATE (idempotentny wzorzec jak w tabu/mada mirror-sync) -
                # zapisujemy historię PRZED update'em, na starym sap.stock.
                StockHistory.objects.using(mpd_db).create(
                    stock_id=sap.id, source_id=source.id,
                    previous_stock=sap.stock, new_stock=current_stock,
                    previous_price=sap.price, new_price=sap.price,
                )
                StockAndPrices.objects.using(mpd_db).filter(pk=sap.pk).update(
                    stock=current_stock, last_updated=now,
                )
                stats['updated'] += 1
            else:
                stats['unchanged'] += 1
        except Exception as exc:
            stats['errors'] += 1
            stats['error_details'].append(f'variant_id={mapped_variant_uid}: {exc}')
            logger.exception("Błąd sync_stock_bridge (%s) dla variant_id=%s", source_name, mapped_variant_uid)

    return stats
