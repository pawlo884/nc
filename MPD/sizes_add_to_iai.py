from MPD.models import Sizes
import os
import django
import requests
import json

# Konfiguracja Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nc.settings.dev')
django.setup()


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

    # Przygotowanie JSON
    sizes_list = []
    for size in sizes_queryset:
        size_data = {
            "group_id": size.id,
            "name": f"{size.name}_bielizna",
            "lang_data": [
                {
                    "lang_id": "pol",
                    "name": size.name
                }
            ],
            "operation": "add"
        }
        sizes_list.append(size_data)

    # Payload do wysłania
    payload = {
        "params": {
            "sizes": sizes_list
        }
    }

    print(f"Znaleziono {len(sizes_list)} rozmiarów do wysłania:")
    print(json.dumps(payload, indent=2, ensure_ascii=False))

    # Wysłanie PUT request
    if sizes_list:  # Tylko jeśli są dane do wysłania
        response = requests.put(url, json=payload, headers=headers)
        print(f"\nStatus: {response.status_code}")
        print(f"Response: {response.text}")
    else:
        print("Brak danych do wysłania")

except Exception as e:
    print(f"Błąd: {e}")
