"""
Ręczny, jawny push jednego produktu MPD do PrestaShop WebAPI. Faza 1 -
narzędzie do weryfikacji end-to-end na pojedynczym produkcie, NIE bulk/cron
(to Faza 4, po potwierdzeniu że mapowanie/payloady są poprawne).

Użycie:
  python manage.py push_prestashop_product --id=123 --dry-run
  python manage.py push_prestashop_product --id=123
"""
from django.core.management.base import BaseCommand, CommandError

from MPD.models import ProductVariants, Products
from prestashop.api_client import PrestaShopApiClient, PrestaShopApiError
from prestashop.exporter import build_product_xml, push_combination, push_product, push_stock


class Command(BaseCommand):
    help = 'Wypycha jeden produkt MPD (+ jego warianty/stany) do PrestaShop WebAPI.'

    def add_arguments(self, parser):
        parser.add_argument('--id', type=int, required=True,
                             help='ID produktu w MPD (Products.id)')
        parser.add_argument('--dry-run', action='store_true',
                             help='Tylko zbuduj i wypisz XML produktu, bez wysyłania niczego.')

    def handle(self, *args, **options):
        product_id = options['id']
        try:
            product = Products.objects.using('MPD').get(id=product_id)
        except Products.DoesNotExist:
            raise CommandError(f'Nie znaleziono produktu MPD id={product_id}')

        try:
            client = PrestaShopApiClient()
        except PrestaShopApiError as exc:
            raise CommandError(str(exc))

        if options['dry_run']:
            self.stdout.write(self.style.WARNING(
                f'[dry-run] Buduję XML dla "{product.name}" (MPD id={product.id}) - '
                f'nic nie wysyłam, nic nie tworzę w PrestaShop.'
            ))
            xml_body = build_product_xml(product, client, dry_run=True)
            self.stdout.write(xml_body.decode('utf-8'))
            variants = ProductVariants.objects.using('MPD').filter(product=product)
            self.stdout.write(
                f'\n{variants.count()} wariant(ów) zostałoby wysłanych jako combinations.')
            return

        self.stdout.write(f'Wypycham produkt "{product.name}" (MPD id={product.id})...')
        try:
            presta_product_id = push_product(product, client)
        except PrestaShopApiError as exc:
            raise CommandError(f'Błąd tworzenia/aktualizacji produktu: {exc}')
        self.stdout.write(self.style.SUCCESS(
            f'✅ Produkt PrestaShop id={presta_product_id}'))

        variants = ProductVariants.objects.using('MPD').filter(product=product)
        pushed, errors = 0, 0
        for index, variant in enumerate(variants):
            try:
                # Dokladnie jeden combination per produkt moze miec default_on=1
                # w PrestaShop - dajemy go pierwszemu (chyba ze ktorys juz jest
                # oznaczony jako domyslny z poprzedniego pushu).
                is_default = (index == 0) and not variant.presta_combination_id
                combination_id = push_combination(
                    variant, presta_product_id, client, default_on=is_default)
                push_stock(variant, presta_product_id, combination_id, client)
                pushed += 1
            except PrestaShopApiError as exc:
                errors += 1
                self.stderr.write(self.style.ERROR(
                    f'  ❌ Wariant {variant.variant_id}: {exc}'))

        self.stdout.write(self.style.SUCCESS(
            f'✅ Zakończono: {pushed} wariant(ów) wypchniętych, {errors} błędów.'))
