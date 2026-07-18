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

Frontend: http://localhost:5173  
Skrót w adminie: setting `MPD_REACT_FRONTEND_URL` (domyślnie `http://localhost:5173`).

## Produkcja

Build (`vite base=/mpd-app/`) jest wbudowany w `Dockerfile.prod` i serwowany przez Django pod:

- https://nc.sowa.ch/mpd-app/

API pozostaje same-origin (`/api/...`). W prod `MPD_REACT_FRONTEND_URL` domyślnie = `/mpd-app`.

Lokalny test buildu:

```powershell
cd frontend/mpd
npm run build
# dist → ustaw MPD_SPA_ROOT lub skopiuj do mpd_spa/
```

## Strony

| Ścieżka (dev) | Prod | Opis |
|---------------|------|------|
| `/login` | `/mpd-app/login` | Logowanie |
| `/` | `/mpd-app/` | Lista produktów MPD |
| `/products/:id` | `/mpd-app/products/:id` | Szczegóły produktu |

## API (tylko MPD)

- `POST /api/auth/token/` — logowanie
- `GET /api/mpd/products/` — lista produktów
- `GET /api/mpd/products/<id>/` — szczegóły produktu

Dokumentacja: http://127.0.0.1:8000/api/docs/
