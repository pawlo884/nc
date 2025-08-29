#!/usr/bin/env python
"""
Skrypt do generowania producers.xml z tabeli brands używając kolumny iai_brand_id
"""

import os
import sys
import django

# Dodaj ścieżkę do projektu
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Ustaw zmienne środowiskowe Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nc.settings.dev')

# Inicjalizuj Django
django.setup()


def generate_producers_xml():
    """Generuje producers.xml z tabeli brands używając iai_brand_id"""
    print("🏭 Generowanie producers.xml z tabeli brands...")

    try:
        # Importuj eksporter
        from MPD.export_to_xml import ProducersXMLExporter

        # Utwórz eksporter
        exporter = ProducersXMLExporter()

        # Wygeneruj XML
        xml_content = exporter.generate_xml()

        # Zapisz lokalnie
        local_path = 'MPD_test/xml/matterhorn/producers.xml'
        os.makedirs(os.path.dirname(local_path), exist_ok=True)

        with open(local_path, 'w', encoding='utf-8') as f:
            f.write(xml_content)

        print("✅ Producers.xml wygenerowany pomyślnie!")
        print(f"📄 Zapisano lokalnie: {local_path}")

        # Pokaż statystyki
        from MPD.models import Brands
        total_brands = Brands.objects.using('MPD').count()
        brands_with_iai_id = Brands.objects.using(
            'MPD').filter(iai_brand_id__isnull=False).count()

        print("\n📊 Statystyki:")
        print(f"   • Łączna liczba marek: {total_brands}")
        print(f"   • Marki z iai_brand_id: {brands_with_iai_id}")
        print(
            f"   • Marki bez iai_brand_id: {total_brands - brands_with_iai_id}")

        # Pokaż przykładowe producenty
        print("\n📋 Przykładowe producenty w XML:")
        lines = xml_content.split('\n')
        producer_count = 0
        for line in lines:
            if '<producer id=' in line:
                print(f"  {line.strip()}")
                producer_count += 1
                if producer_count >= 5:  # Pokaż tylko pierwsze 5
                    break

        # Sprawdź zgodność ze schematem
        print("\n🔍 Sprawdzanie zgodności ze schematem producers.xsd:")
        if 'file_format="IOF"' in xml_content:
            print("✅ Zawiera file_format IOF")
        else:
            print("❌ Brak file_format IOF")

        if 'version="3.0"' in xml_content:
            print("✅ Zawiera version 3.0")
        else:
            print("❌ Brak version 3.0")

        if 'language="pol"' in xml_content:
            print("✅ Zawiera language pol")
        else:
            print("❌ Brak language pol")

        return True

    except Exception as e:
        print(f"❌ Błąd podczas generowania: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = generate_producers_xml()
    if success:
        print("\n🎉 Generowanie producers.xml zakończone pomyślnie!")
        print("\n📋 Dostępne endpointy:")
        print("• http://192.168.1.109:8000/mpd/generate-producers-xml/")
    else:
        print("\n❌ Generowanie zakończone z błędami!")
