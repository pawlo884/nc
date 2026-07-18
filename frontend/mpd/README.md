# MPD Frontend (React)

Panel React wyłącznie dla bazy MPD (Master Product Database).

## Uruchomienie

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

## Strony

| Ścieżka | Opis |
|---------|------|
| `/login` | Logowanie |
| `/` | Lista produktów MPD |
| `/products/:id` | Szczegóły produktu (warianty, zdjęcia, opis) |

## API (tylko MPD)

- `POST /api/auth/token/` — logowanie
- `GET /api/mpd/products/` — lista produktów
- `GET /api/mpd/products/<id>/` — szczegóły produktu

Dokumentacja: http://127.0.0.1:8000/api/docs/
