# Dokumentacja zewnętrzna: IdoSell API

Linki do oficjalnej dokumentacji IdoSell – do wykorzystania przy integracji lub przy pracy z agentem.

## Główne linki

| Zasób | URL |
|--------|-----|
| **Getting Started (Intro)** | https://idosell.readme.io/docs/getting-started |
| **API Reference (wszystkie endpointy)** | https://idosell.readme.io/reference/ |
| **Deweloperzy IdoSell (wszystkie API)** | https://www.idosell.com/developers |

W API Reference są m.in.: CRM (np. `clients/balance`), CMS, OMS, PIM, SYSTEM, WMS. Przykład endpointu: [clients/balance GET](https://idosell.readme.io/reference/clientsbalanceget).

## OpenAPI (Admin API)

Specyfikacja OpenAPI w JSON (per sklep, per wersja):

```
https://{domena}/api/doc/admin/v{X}/json
```

- `{domena}` – adres panelu sklepu (np. `sklep123.idosell.com`)
- `{X}` – wersja API (2–7, np. `7`)

## Kontekst (z dokumentacji IdoSell)

- Admin API – interfejs do operacji jak w panelu admina (adres panelu + klucz API).
- Dostęp: ten sam sposób dla każdego sklepu; różni się adres API i klucz.
- Sandbox Demo – do testów (operacja w panelu → sprawdzenie, który gateway API ją realizuje).
- Aktualizacje: zmiany wdrażane stopniowo; nowe funkcje dostępne u wszystkich w ciągu ok. 2 tygodni.

## Zastosowanie w projekcie NC

Ten plik służy jako punkt odniesienia do dokumentacji IdoSell przy:
- implementacji integracji z IdoSell,
- odwołaniach do API w kodzie lub w rozmowie z agentem.
