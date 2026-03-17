from django.core.management.base import BaseCommand
from django.utils import timezone
from MPD.models import ExportTracking, ProductVariants
from django.db.models import Max
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Naprawia ExportTracking dla full_change.xml - ustawia last_exported_product_id na maksymalne ID produktu'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Pokaż co zostanie zmienione bez wprowadzania zmian',
        )

    def handle(self, *args, **options):
        self.stdout.write("🔍 Sprawdzam stan ExportTracking...")

        try:
            # Pobierz maksymalne ID produktu z bazy (bez pola iai_product_id)
            max_iai_id = ProductVariants.objects.using('MPD').aggregate(
                max_id=Max('product_id')
            )['max_id'] or 0

            self.stdout.write(
                f"📊 Maksymalny iai_product_id w bazie: {max_iai_id}")

            # Sprawdź tracking dla full.xml
            full_tracking = ExportTracking.objects.using('MPD').filter(
                export_type='full.xml'
            ).first()

            if full_tracking:
                self.stdout.write(
                    f"📋 full.xml - last_exported_product_id: {full_tracking.last_exported_product_id}")
            else:
                self.stdout.write("❌ Brak tracking dla full.xml")
                return

            # Sprawdź tracking dla full_change.xml
            change_tracking = ExportTracking.objects.using('MPD').filter(
                export_type='full_change.xml'
            ).first()

            if change_tracking:
                self.stdout.write(
                    f"📋 full_change.xml - last_exported_product_id: {change_tracking.last_exported_product_id}")
            else:
                self.stdout.write("❌ Brak tracking dla full_change.xml")
                return

            # Sprawdź czy trzeba naprawić
            if change_tracking.last_exported_product_id < max_iai_id:
                self.stdout.write(self.style.WARNING("⚠️  Wykryto problem:"))
                self.stdout.write(
                    f"   • full_change.xml ma last_exported_product_id = {change_tracking.last_exported_product_id}")
                self.stdout.write(
                    f"   • Powinien mieć = {max_iai_id} (jak full.xml)")
                self.stdout.write(
                    f"   • To dlatego full_change.xml jest pusty!")

                if options['dry_run']:
                    self.stdout.write("🔍 DRY RUN - co zostanie zmienione:")
                    self.stdout.write(
                        f"   • full_change.xml.last_exported_product_id: {change_tracking.last_exported_product_id} → {max_iai_id}")
                    self.stdout.write(
                        f"   • full_change.xml.total_products_exported: {change_tracking.total_products_exported} → {max_iai_id}")
                    self.stdout.write(
                        f"   • full_change.xml.last_exported_timestamp: {change_tracking.last_exported_timestamp} → {timezone.now()}")
                else:
                    self.stdout.write("🔧 Naprawiam...")

                    old_id = change_tracking.last_exported_product_id
                    old_count = change_tracking.total_products_exported
                    old_timestamp = change_tracking.last_exported_timestamp

                    change_tracking.last_exported_product_id = max_iai_id
                    change_tracking.total_products_exported = max_iai_id
                    change_tracking.last_exported_timestamp = timezone.now()
                    change_tracking.export_status = 'success'
                    change_tracking.save()

                    self.stdout.write(self.style.SUCCESS("✅ Naprawiono!"))
                    self.stdout.write(
                        f"   • last_exported_product_id: {old_id} → {max_iai_id}")
                    self.stdout.write(
                        f"   • total_products_exported: {old_count} → {max_iai_id}")
                    self.stdout.write(
                        f"   • last_exported_timestamp: {old_timestamp} → {change_tracking.last_exported_timestamp}")
                    self.stdout.write("")
                    self.stdout.write(
                        "💡 Teraz full_change.xml będzie eksportował zmiany dla wszystkich wyeksportowanych produktów")
            else:
                self.stdout.write(self.style.SUCCESS(
                    "✅ ExportTracking jest poprawny - nie ma potrzeby naprawy"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Błąd: {str(e)}"))
            logger.error(f"Błąd podczas naprawy ExportTracking: {str(e)}")
            raise
