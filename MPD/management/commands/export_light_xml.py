from django.core.management.base import BaseCommand
from MPD.export_to_xml import LightXMLExporter


class Command(BaseCommand):
    help = 'Eksportuje produkty do XML zgodnie ze schematem light.xsd'

    def handle(self, *args, **options):
        try:
            self.stdout.write('🚀 Rozpoczynam eksport light.xml...')

            # Utwórz eksporter
            exporter = LightXMLExporter()

            # Wygeneruj XML
            xml_content = exporter.generate_xml()

            # Zapisz lokalnie
            local_path = exporter.save_local(xml_content)

            # Zapisz do bucket
            bucket_url = exporter.save_to_bucket(local_path)

            if bucket_url:
                self.stdout.write(
                    self.style.SUCCESS(
                        '✅ Eksport light.xml zakończony pomyślnie!')
                )
                self.stdout.write(f'📁 URL: {bucket_url}')
                self.stdout.write(f'📄 Lokalnie zapisano: {local_path}')
            else:
                self.stdout.write(
                    self.style.WARNING(
                        '⚠️ Eksport light.xml zakończony, ale nie udało się zapisać do bucket')
                )
                self.stdout.write(f'📄 Lokalnie zapisano: {local_path}')

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    f'❌ Błąd podczas eksportu light.xml: {str(e)}')
            )
            raise
