from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Eksportuje produkty do pliku XML w formacie IOF'

    def add_arguments(self, parser):
        parser.add_argument(
            '--filename',
            type=str,
            default='export_full.xml',
            help='Nazwa pliku wyjściowego (domyślnie: export_full.xml)'
        )

    def handle(self, *args, **options):
        filename = options['filename']

        self.stdout.write('🔄 Rozpoczynam eksport XML...')

        try:
            from MPD.export_to_full_xml import save_xml_to_file
            result = save_xml_to_file(filename)

            if result:
                self.stdout.write('✅ Eksport XML zakończony pomyślnie!')
                self.stdout.write(f'📁 Plik: {result}')
            else:
                self.stdout.write('❌ Błąd podczas eksportu XML')

        except Exception as e:
            self.stdout.write(f'❌ Błąd podczas eksportu XML: {e}')
