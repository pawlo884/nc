Oto kompletna dokumentacja Twojego systemu w formacie Markdown. Możesz ją skopiować do pliku `README.md` lub `DOCS.md` w swoim projekcie.

---

# System Automatycznej Standaryzacji Zdjęć Produktowych (Django + Celery + RTX 4070)

System pozwala na bezobsługowe wyrównywanie proporcji zdjęć i dobudowywanie tła przy użyciu lokalnej jednostki GPU, z uwzględnieniem harmonogramu domowników (granie w gry) oraz oszczędności energii (Wake-on-LAN).

## 1. Architektura Systemu

* **Backend:** Django + Celery.
* **Storage:** MinIO (S3 compatible).
* **AI Engine:** Stable Diffusion WebUI (Forge) na zdalnej maszynie z RTX 4070.
* **Komunikacja:** REST API + Wake-on-LAN (Magic Packet).

---

## 2. Konfiguracja Maszyny GPU (RTX 4070)

### A. BIOS & Windows (WoL)

1. Włącz **Wake on Magic Packet** w ustawieniach karty sieciowej (Menedżer Urządzeń).
2. Włącz **Wake-on-LAN** w BIOS/UEFI.
3. Ustaw plan zasilania: "Uśpij po 30 minutach bezczynności".

### B. Stable Diffusion Forge

Uruchom Forge z flagami umożliwiającymi dostęp z sieci lokalnej:

```bash
webui-user.bat --api --listen --port 7860

```

### C. Monitor obciążenia (Mini-serwer statusu)

Stwórz lekki skrypt `gpu_status.py`, aby Django wiedziało, czy karta jest wolna:

```python
from fastapi import FastAPI
import pynvml

app = FastAPI()
pynvml.nvmlInit()

@app.get("/gpu-free")
def is_gpu_free():
    handle = pynvml.nvmlDeviceGetHandleByIndex(0)
    util = pynvml.nvmlDeviceGetUtilizationRates(handle)
    # Zwraca True, jeśli użycie GPU < 15% (brak gier)
    return {"free": util.gpu < 15}

```

---

## 3. Integracja w Django (Celery Task)

### Wymagane biblioteki

```bash
pip install wakeonlan requests boto3 pynvml

```

### Kod Zadania (`tasks.py`)

```python
import base64
import requests
from io import BytesIO
from wakeonlan import send_magic_packet
from celery import shared_task
from django.conf import settings

# Konfiguracja zdalnej jednostki
GPU_MAC = "AA:BB:CC:DD:EE:FF"
GPU_IP = "192.168.1.50"
API_URL = f"http://{GPU_IP}:7860/sdapi/v1/img2img"
STATUS_URL = f"http://{GPU_IP}:8000/gpu-free"

@shared_task(bind=True, max_retries=10)
def process_product_image(self, product_id):
    # 1. Sprawdź czy maszyna żyje
    try:
        status = requests.get(STATUS_URL, timeout=2).json()
    except:
        # Maszyna śpi - obudź ją
        send_magic_packet(GPU_MAC)
        raise self.retry(countdown=60) # Spróbuj za minutę (boot systemu)

    # 2. Sprawdź czy GPU jest wolne (czy dziecko nie gra)
    if not status.get("free"):
        raise self.retry(countdown=600) # Ktoś gra, spróbuj za 10 min

    # 3. Pobierz zdjęcie z MinIO i przygotuj payload (Outpainting)
    # [Logika pobierania z MinIO i kodowania do Base64]
    
    payload = {
        "init_images": [img_b64],
        "prompt": "high quality product photo, white studio background, soft shadows",
        "alwayson_scripts": {
            "ControlNet": {
                "args": [{"model": "control_v11p_sd15_inpaint", "module": "inpaint_only"}]
            }
        },
        "width": 1024,
        "height": 1024
    }

    # 4. Wyślij do RTX 4070
    response = requests.post(API_URL, json=payload)
    if response.status_code == 200:
        # Zapisz wynik w MinIO i zaktualizuj DB
        pass

```

---

## 4. Workflow Pracy

1. **Rejestracja:** Nowy produkt wpada do Django -> zdjęcie ląduje w MinIO.
2. **Kolejkowanie:** Zadanie `process_product_image` trafia do Celery.
3. **Inteligentne Czekanie:**
* Jeśli RTX jest wyłączony -> **WoL Signal** -> Retry.
* Jeśli RTX pracuje (gra) -> **Wait** -> Retry.


4. **Przetwarzanie:** AI generuje brakujące tło, wyrównując zdjęcie do kwadratu .
5. **Finalizacja:** Gotowe zdjęcie trafia do MinIO, status produktu zmienia się na "Aktywny".
6. **Uśpienie:** Po zakończeniu wszystkich zadań i 30 min bezczynności, maszyna GPU sama się wyłącza.

---

### Do zrobienia:

* [ ] Wpisz właściwy adres MAC karty RTX 4070.
* [ ] Skonfiguruj statyczne IP dla maszyny GPU na routerze.
* [ ] Pobierz model ControlNet Inpaint na maszynę z RTX.

**Czy chcesz, abym dopisał funkcję w Pythonie do automatycznego robienia "letterboxingu" (dodawania marginesów przed wysłaniem do AI)?**