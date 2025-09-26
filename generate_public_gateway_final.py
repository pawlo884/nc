#!/usr/bin/env python
"""
Skrypt do generowania finalnego gateway.xml z publicznym adresem IP
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


def generate_public_gateway():
    """Generuje gateway.xml z publicznym adresem IP"""
    print("🌐 Generowanie gateway.xml z publicznym adresem IP...")

    # Sprawdź obecny URL
    from django.conf import settings
    api_url = getattr(settings, 'API_BASE_URL', 'http://212.127.93.27:8000')
    print(f"📋 Używany API_BASE_URL: {api_url}")

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

        print(f"✅ Gateway.xml wygenerowany pomyślnie!")
        print(f"📄 Zapisano lokalnie: {local_path}")

        # Sprawdź endpointy
        endpoints = [
            "generate-full-xml",
            "generate-gateway-xml-api"
        ]

        print("\n🔍 Sprawdzanie endpointów w gateway.xml:")
        for endpoint in endpoints:
            if endpoint in xml_content:
                print(f"✅ Zawiera: {endpoint}")
            else:
                print(f"❌ Brakuje: {endpoint}")

        # Sprawdź URL-e
        print("\n🌐 Sprawdzanie URL-i:")
        if "212.127.93.27:8000" in xml_content:
            print("✅ URL-e używają publicznego adresu IP")
        else:
            print("❌ URL-e nie używają publicznego adresu IP")

        # Pokaż przykładowe URL-e
        print("\n📋 Przykładowe URL-e w gateway.xml:")
        lines = xml_content.split('\n')
        url_count = 0
        for line in lines:
            if "generate-" in line and "url=" in line:
                print(f"  {line.strip()}")
                url_count += 1
                if url_count >= 3:
                    break

        return True

    except Exception as e:
        print(f"❌ Błąd podczas generowania: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = generate_public_gateway()
    if success:
        print("\n🎉 Generowanie zakończone pomyślnie!")
        print("\n📋 Publiczne endpointy:")
        print("• http://212.127.93.27:8000/mpd/generate-full-xml/")
        print("• http://212.127.93.27:8000/mpd/generate-full-change-xml/")
        print("• http://212.127.93.27:8000/mpd/generate-gateway-xml-api/")
        print("\n🚀 Uruchom serwer: python manage.py runserver 0.0.0.0:8000")
        print("\n🌐 Twój API jest teraz dostępny publicznie!")
    else:
        print("\n💥 Generowanie nie powiodło się!")
        sys.exit(1)
