# Tabu API – dokumentacja

**Dokumentacja oficjalna:** [https://b2b.tabu.com.pl/api/v1](https://b2b.tabu.com.pl/api/v1)

## Podstawy

- **URL bazowy:** `https://b2b.tabu.com.pl/api/v1`
- **Uwierzytelnienie:** nagłówek `X-API-KEY: Twój klucz API`
- Metody: GET, POST (REST). Zalecane: `Content-Type: application/json` i JSON w body.
- **Limity:** max 100 zapytań/minutę (przy przekroczeniu blokada 2 min). Max 1000 elementów w `limit`.

## Konfiguracja w projekcie

W `.env.dev`:

```env
TABU_API_BASE_URL=https://b2b.tabu.com.pl/api/v1
TABU_API_KEY=Twój_klucz_API
```

Domyślnie `TABU_API_BASE_URL` jest ustawiony na powyższy URL; można go nadpisać.

## Test połączenia

```bash
cd src
python manage.py test_tabu_connection --settings=core.settings.dev
```

Z podaniem klucza w linii:

```bash
python manage.py test_tabu_connection --api-key=TWÓJ_KLUCZ --settings=core.settings.dev
```

Inne zasoby (domyślnie wywoływany jest `GET .../products`):

```bash
python manage.py test_tabu_connection --path=products/categories --settings=core.settings.dev
python manage.py test_tabu_connection --path=users/me --settings=core.settings.dev
```

## Wybrane zasoby (produkty, zamówienia)

| Zasób | Opis |
|-------|------|
| `GET products` | Lista produktów (parametry: path, category_id, update_from, update_to) |
| `GET products/{id}` | Szczegóły produktu |
| `GET products/details` | Szczegółowa lista produktów (max limit 100) |
| `GET products/basic` | Stany magazynowe i ceny |
| `GET products/categories` | Pełna lista kategorii |
| `GET products/producers` | Lista producentów |
| `GET orders` | Lista zamówień |
| `GET orders/{id}` | Szczegóły zamówienia |
| `GET users/me` | Dane użytkownika API |

Stronicowanie: parametry `page`, `limit`, `lang` dla list.

## Kody odpowiedzi

- **200** – sukces  
- **400** – nieprawidłowe dane  
- **401** – błąd autoryzacji  
- **403** – brak dostępu do zasobu  
- **404** – zasób nie istnieje  
- **429** – przekroczony limit zapytań  
- **500** – błąd serwera  

Pełna lista endpointów i parametrów: [https://b2b.tabu.com.pl/api/v1](https://b2b.tabu.com.pl/api/v1).
