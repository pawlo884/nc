from django.core.management.base import BaseCommand
from django.utils import timezone
from MPD.export_to_xml import FullChangeXMLExporter
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Uruchamia godzinowy eksport full_change.xml - tylko produkty zmienione w ciągu ostatnich 2 godzin'

    def add_arguments(self, parser):
        parser.add_argument(
            '--full',
            action='store_true',
            help='Uruchom pełny eksport (wszystkie produkty) zamiast przyrostowego',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Szczegółowe logowanie',
        )

    def handle(self, *args, **options):
        start_time = timezone.now()

        if options['verbose']:
            self.stdout.write(
                f"🚀 Rozpoczynam eksport full_change.xml o {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

        try:
            # Utwórz eksporter
            exporter = FullChangeXMLExporter()

            if options['full']:
                # Eksport pełny - wszystkie produkty
                self.stdout.write(
                    "📋 Uruchamiam pełny eksport (wszystkie produkty)...")
                result = exporter.export_full()
            else:
                # Eksport przyrostowy - tylko zmienione produkty z ostatnich 2 godzin
                self.stdout.write(
                    "🔄 Uruchamiam eksport przyrostowy (zmienione produkty z ostatnich 2h)...")
                result = exporter.export_incremental()

            end_time = timezone.now()
            duration = end_time - start_time

            if result['bucket_url']:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✅ Eksport full_change.xml zakończony pomyślnie w {duration.total_seconds():.2f}s!"
                    )
                )
                self.stdout.write(f"📁 URL: {result['bucket_url']}")
                self.stdout.write(
                    f"📄 Lokalnie zapisano: {result['local_path']}")

                if options['verbose']:
                    self.stdout.write(
                        f"⏰ Rozpoczęto: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
                    self.stdout.write(
                        f"⏰ Zakończono: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
                    self.stdout.write(f"⏱️  Czas trwania: {duration}")

            else:
                self.stdout.write(
                    self.style.ERROR(
                        f"❌ Błąd podczas eksportu full_change.xml po {duration.total_seconds():.2f}s"
                    )
                )
                self.stdout.write(
                    f"📄 Lokalnie zapisano: {result['local_path']}")

        except Exception as e:
            end_time = timezone.now()
            duration = end_time - start_time

            self.stdout.write(
                self.style.ERROR(
                    f"❌ Błąd podczas eksportu po {duration.total_seconds():.2f}s: {str(e)}"
                )
            )
            logger.error(f"Błąd podczas eksportu full_change.xml: {str(e)}")
            raise
