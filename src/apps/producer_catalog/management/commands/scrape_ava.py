"""
Komenda: python manage.py scrape_ava [--full] [--limit N]
Zbiera produkty z avalingerie.pl do mini bazy (producer_catalog).
Zapisuje historię cen – do pilnowania zmian.
"""
import logging
from django.core.management.base import BaseCommand
from django.utils import timezone

from producer_catalog.models import (
    ProducerSource,
    ProducerProduct,
    ProducerProductVariant,
    ProducerPriceHistory,
)
from producer_catalog.scraper.ava import (
    LISTING_URLS,
    collect_product_urls,
    scrape_product_page,
    _session,
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Scrapuje katalog AVA (avalingerie.pl): produkty, rozmiary, opisy, ceny. Zapisuje historię cen."

    def add_arguments(self, parser):
        parser.add_argument(
            "--full",
            action="store_true",
            help="Przeskanuj wszystkie listy kategorii (domyślnie: tak).",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Limit liczby produktów do przetworzenia (0 = bez limitu).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Tylko zbierz URL-e i parsuj, bez zapisu do bazy.",
        )

    def handle(self, *args, **options):
        full = options["full"]
        limit = options["limit"] or 0
        dry_run = options["dry_run"]

        source, _ = ProducerSource.objects.get_or_create(
            slug="ava",
            defaults={
                "name": "AVA Lingerie",
                "base_url": "https://avalingerie.pl/pl/",
                "is_active": True,
            },
        )

        session = _session()
        listing_urls = None if options["full"] else [LISTING_URLS[0]]
        urls = collect_product_urls(session, listing_urls=listing_urls)
        self.stdout.write(f"Znaleziono {len(urls)} unikalnych URL-i produktów.")

        if limit:
            urls = list(urls)[:limit]
        else:
            urls = list(urls)

        created_products = 0
        updated_products = 0
        created_variants = 0
        price_changes = 0

        for i, url in enumerate(urls, 1):
            self.stdout.write(f"[{i}/{len(urls)}] {url}")
            data = scrape_product_page(url, session=session)
            if not data:
                continue

            if dry_run:
                self.stdout.write(
                    f"  DRY-RUN: {data['name']} | cena {data['price_brutto']} | rozmiarów: {len(data['sizes'])}"
                )
                continue

            product, created = ProducerProduct.objects.update_or_create(
                source=source,
                url=url,
                defaults={
                    "external_id": data.get("external_id"),
                    "name": data["name"],
                    "description": (data.get("description") or "")[:50000],
                    "image_url": (data.get("image_url") or "")[:1000],
                    "scraped_at": timezone.now(),
                },
            )
            if created:
                created_products += 1
            else:
                updated_products += 1

            price_brutto = data.get("price_brutto")
            sizes = data.get("sizes") or []

            for size_name in sizes:
                variant, v_created = ProducerProductVariant.objects.get_or_create(
                    product=product,
                    size_name=size_name.strip()[:100],
                    defaults={
                        "price_brutto": price_brutto,
                        "currency": data.get("currency", "PLN"),
                        "scraped_at": timezone.now(),
                    },
                )
                if v_created:
                    created_variants += 1
                    if price_brutto is not None:
                        ProducerPriceHistory.objects.create(
                            variant=variant,
                            price_brutto=price_brutto,
                            currency=data.get("currency", "PLN"),
                        )
                else:
                    # Pilnuj cen – jeśli się zmieniła, zapisz historię
                    old_price = variant.price_brutto
                    if price_brutto is not None and old_price != price_brutto:
                        ProducerPriceHistory.objects.create(
                            variant=variant,
                            price_brutto=price_brutto,
                            currency=data.get("currency", "PLN"),
                        )
                        variant.price_brutto = price_brutto
                        variant.scraped_at = timezone.now()
                        variant.save(update_fields=["price_brutto", "scraped_at"])
                        price_changes += 1
                    elif price_brutto is not None:
                        variant.scraped_at = timezone.now()
                        variant.save(update_fields=["scraped_at"])

            # Produkty bez rozmiarów (np. jeden wariant) – jeden wariant z pustym rozmiarem lub "uniwersalny"
            if not sizes and price_brutto is not None:
                variant, v_created = ProducerProductVariant.objects.get_or_create(
                    product=product,
                    size_name="",
                    defaults={
                        "price_brutto": price_brutto,
                        "currency": data.get("currency", "PLN"),
                        "scraped_at": timezone.now(),
                    },
                )
                if v_created:
                    created_variants += 1
                    ProducerPriceHistory.objects.create(
                        variant=variant,
                        price_brutto=price_brutto,
                        currency=data.get("currency", "PLN"),
                    )

        if not dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Gotowe. Produkty: +{created_products} nowych, {updated_products} zaktualizowanych. "
                    f"Warianty: +{created_variants}. Zmiany cen: {price_changes}."
                )
            )
