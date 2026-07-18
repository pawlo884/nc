# MPD Frontend (React)

Panel React wyłącznie dla bazy MPD (Master Product Database).

## Uruchomienie (dev)

```powershell
# Terminal 1 — Django
cd src
..\.venv\Scripts\python.exe manage.py runserver --settings=core.settings.dev

# Terminal 2 — React
cd frontend/mpd
npm install
npm run dev
```

Frontend (ta sama ścieżka co prod): **http://localhost:5173/mpd-app/**  
LAN: `http://<IP-PC>:5173/mpd-app/`  
Skrót w adminie: `MPD_REACT_FRONTEND_URL` (domyślnie `http://localhost:5173/mpd-app`).

## Produkcja

Build jest wbudowany w `Dockerfile.prod` i serwowany przez Django pod:

- https://nc.sowa.ch/mpd-app/

API same-origin (`/api/...`). W prod `MPD_REACT_FRONTEND_URL` = `/mpd-app`.

## Strony

| Ścieżka | Opis |
|---------|------|
| `/mpd-app/login` | Logowanie |
| `/mpd-app/` | Lista produktów MPD |
| `/mpd-app/products/:id` | Szczegóły produktu |

## API (tylko MPD)

- `POST /api/auth/token/` — logowanie
- `GET /api/mpd/products/` — lista produktów
- `GET /api/mpd/products/<id>/` — szczegóły produktu

Dokumentacja: http://127.0.0.1:8000/api/docs/
