#!/usr/bin/env python
"""
Skrypt do wygenerowania nowego gateway.xml z endpointami API
"""

from MPD.export_to_xml import GatewayXMLExporter
import os
import sys
import django

# Dodaj ścieżkę do projektu
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Ustaw zmienne środowiskowe Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nc.settings.dev')

# Inicjalizuj Django
django.setup()


def generate_new_gateway():
    """Generuje nowy gateway.xml z endpointami API"""
    print("🚀 Generowanie nowego gateway.xml z endpointami API...")

    try:
        # Utwórz eksporter
        exporter = GatewayXMLExporter()

        # Wygeneruj XML
        xml_content = exporter.generate_xml()

        # Zapisz lokalnie
        local_path = 'MPD_test/xml/matterhorn/gateway.xml'
        os.makedirs(os.path.dirname(local_path), exist_ok=True)

        with open(local_path, 'w', encoding='utf-8') as f:
            f.write(xml_content)

        print(f"✅ Nowy gateway.xml wygenerowany pomyślnie!")
        print(f"📄 Zapisano lokalnie: {local_path}")

        # Sprawdź czy zawiera endpointy API
        if "generate-full-xml" in xml_content:
            print("✅ Zawiera endpoint full.xml")
        else:
            print("❌ Brak endpointu full.xml")

        if "generate-light-xml" in xml_content:
            print("✅ Zawiera endpoint light.xml")
        else:
            print("❌ Brak endpointu light.xml")

        if "generate-producers-xml" in xml_content:
            print("✅ Zawiera endpoint producers.xml")
        else:
            print("❌ Brak endpointu producers.xml")

        if "generate-categories-xml" in xml_content:
            print("✅ Zawiera endpoint categories.xml")
        else:
            print("❌ Brak endpointu categories.xml")

        # Pokaż fragment XML
        print("\n📋 Fragment wygenerowanego XML:")
        lines = xml_content.split('\n')
        for i, line in enumerate(lines):
            if i < 30:  # Pokaż pierwsze 30 linii
                print(f"  {line}")
            elif "generate-" in line:
                print(f"  {line}")

        return True

    except Exception as e:
        print(f"❌ Błąd podczas generowania: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = generate_new_gateway()
    if success:
        print("\n🎉 Generowanie zakończone pomyślnie!")
    else:
        print("\n💥 Generowanie nie powiodło się!")
        sys.exit(1)



