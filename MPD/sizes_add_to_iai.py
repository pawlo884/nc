
from dotenv import load_dotenv
import os
import sys
import django
import requests
import json
import importlib

# Dodaj katalog główny projektu do sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

# Załaduj zmienne środowiskowe z .env.dev
env_path = os.path.join(project_root, '.env.dev')
load_dotenv(dotenv_path=env_path)

# Konfiguracja Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nc.settings.dev')
django.setup()

# Dynamic import - odporne na auto-organizację importów przez IDE
mpd_models = importlib.import_module('MPD.models')
Sizes = mpd_models.Sizes
# URL API
url = "https://demo177-pl.yourtechnicaldomain.com/api/admin/v6/sizes/sizes"

# Headers
headers = {
    "accept": "application/json",
    "content-type": "application/json",
    "X-API-KEY": "YXBwbGljYXRpb24xOk5Sbm5TekI1Zk1mR2swcjlIVGM0TGp1ZlA4d2VQRzRDZlZpc2xmSUFGVC9mK0s4ZUwxbkhoeTI1YjdXQVJPMnU="
}

try:
    # Pobranie sizes z bazy danych przez model Django
    sizes_queryset = Sizes.objects.filter(
        category='bielizna'
    ).filter(
        iai_size_id__isnull=True
    ) | Sizes.objects.filter(
        category='bielizna',
        iai_size_id=''
    )

    total_sizes = sizes_queryset.count()
    print(f"Znaleziono {total_sizes} rozmiarów do wysłania")

    if total_sizes == 0:
        print("Brak danych do wysłania")
    else:
        # Iteruj po każdym rozmiarze osobno
        for index, size in enumerate(sizes_queryset, 1):
            print(
                f"\n--- Przetwarzanie {index}/{total_sizes}: {size.name} ---")

            # Przygotuj JSON dla pojedynczego rozmiaru
            size_data = {
                "group_id": 1098261181,
                "name": f"{size.name}_bielizna",
                "lang_data": [
                    {
                        "lang_id": "pol",
                        "name": size.name
                    }
                ],
                "operation": "add"
            }

            # Payload dla pojedynczego rozmiaru
            payload = {
                "params": {
                    "sizes": [size_data]  # Tylko jeden rozmiar w tablicy
                }
            }

            print("JSON do wysłania:")
            print(json.dumps(payload, indent=2, ensure_ascii=False))

            # Wysłanie PUT request dla tego rozmiaru
            try:
                response = requests.put(
                    url, json=payload, headers=headers, timeout=30)
                print(f"PUT Status: {response.status_code}")
                print(f"PUT Response: {response.text}")

                if response.status_code == 200:
                    print(f"✅ PUT Sukces dla rozmiaru: {size.name}")

                    # Po udanym PUT wykonaj GET żeby pobrać size_id
                    print("Wykonuję GET request żeby pobrać size_id...")
                    print("Czekam 2 sekundy na synchronizację...")
                    import time
                    time.sleep(2)

                    try:
                        get_response = requests.get(
                            url, headers=headers, timeout=30)
                        print(f"GET Status: {get_response.status_code}")

                        if get_response.status_code == 200:
                            get_data = get_response.json()

                            # Szukaj dodanego rozmiaru w odpowiedzi
                            expected_name = f"{size.name}_bielizna"
                            found_size_id = None
                            print(f"🔍 Szukam rozmiaru: {expected_name}")

                            # Przeszukaj size_groups w odpowiedzi
                            if 'size_groups' in get_data:
                                print(
                                    f"📋 Znaleziono {len(get_data['size_groups'])} grup rozmiarów")
                                for group in get_data['size_groups']:
                                    group_name = group.get(
                                        'group_name', 'brak nazwy')
                                    print(f"🔍 Sprawdzam grupę: {group_name}")

                                    if 'sizes' in group:
                                        for api_size in group['sizes']:
                                            size_name = api_size.get(
                                                'size_name')
                                            if size_name == expected_name:
                                                found_size_id = api_size.get(
                                                    'size_id')
                                                print(
                                                    f"🎯 Znaleziono size_id: {found_size_id} dla {expected_name} w grupie {group_name}")
                                                break
                                        if found_size_id:
                                            break

                            # Aktualizuj bazę danych jeśli znaleziono size_id
                            if found_size_id:
                                size.iai_size_id = found_size_id
                                size.save()
                                print(
                                    f"💾 Zapisano iai_size_id={found_size_id} dla rozmiaru {size.name}")
                            else:
                                print(
                                    f"⚠️ Nie znaleziono size_id dla {expected_name} w odpowiedzi GET")
                                print("GET Response fragment:",
                                      json.dumps(get_data, indent=2)[:500])
                        else:
                            print(
                                f"❌ GET request failed: {get_response.status_code}")

                    except requests.RequestException as e:
                        print(f"❌ Błąd GET request: {e}")
                    except json.JSONDecodeError as e:
                        print(f"❌ Błąd parsowania JSON z GET: {e}")

                else:
                    print(f"❌ PUT Błąd dla rozmiaru: {size.name}")

            except requests.RequestException as e:
                print(f"❌ Błąd HTTP dla rozmiaru {size.name}: {e}")
                continue

            print("-" * 50)

            # TESTOWE: Wykonaj tylko raz - usuń break żeby przetwarzać wszystkie

except Exception as e:
    print(f"Błąd: {e}")
