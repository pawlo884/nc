# Architektura nc_project

Skąd biorą się dane w MPD i dokąd stąd trafiają. MPD jest jedynym źródłem
prawdy o katalogu — trzy hurtownie karmią go niezależnie, dwa kanały
sprzedażowe go stamtąd czerpią, a operator i Claude czytają go z dwóch
różnych stron.

```mermaid
flowchart LR
    subgraph Hurtownie["Hurtownie"]
        MAPI["Matterhorn<br/>B2B API"]
        TAPI["Tabu<br/>REST API"]
        DAPI["Mada<br/>feed XML"]
    end

    subgraph Import["Import"]
        M1["matterhorn1<br/>import + własna baza"]
        T1["tabu<br/>import + własna baza"]
        D1["mada<br/>import + własna baza"]
        WA["web_agent<br/>automatyzacja + OpenAI"]
    end

    MPD[("MPD<br/>centralna baza katalogu<br/>PostgreSQL")]

    ADMIN["Django Admin<br/>ręczne zarządzanie"]
    MCP["MCP server<br/>stdio, tylko odczyt"]
    CLAUDE["Claude Desktop / Code"]

    subgraph Eksport["Eksport"]
        XML["Eksport XML<br/>full/light/gateway → MinIO"]
        PS["prestashop app<br/>WebAPI client (push)"]
    end

    subgraph Sklepy["Sklepy"]
        IDO["IdoSell / IAI<br/>pobiera plik"]
        PSS["PrestaShop<br/>WebAPI"]
    end

    CELERY{{"Celery Beat + Redis<br/>Redis = broker; wyniki/harmonogram w PostgreSQL"}}

    MAPI -->|"co 10 min"| M1
    TAPI -->|"co 10 min"| T1
    DAPI -->|"15 min / dzień"| D1

    M1 -->|"mapa po EAN"| MPD
    T1 -->|"mapa po EAN"| MPD
    D1 -->|"mapa po EAN"| MPD
    WA -.->|"uzupełnia dane (AI)"| MPD

    MPD -->|"generuje"| XML -->|"sklep pobiera"| IDO
    MPD -->|"buduje XML"| PS
    PS -.->|"POST/PUT WebAPI — ręcznie"| PSS

    MPD --- ADMIN
    MPD --- MCP --> CLAUDE

    CELERY -.->|"wyzwala"| M1
    CELERY -.->|"wyzwala"| T1
    CELERY -.->|"wyzwala"| D1
    CELERY -.->|"wyzwala"| XML

    classDef hub fill:#f3e3c6,stroke:#b9791f,stroke-width:2px
    classDef manual stroke-dasharray: 5 5,stroke:#b54708,stroke-width:2px
    class MPD hub
    class PS manual
```

## Czytanie diagramu

- **Linie ciągłe** = automatyczny przepływ danych (import hurtowni → MPD,
  MPD → eksport).
- **Linie przerywane cienkie** (`web_agent`, `Celery → …`) = wyzwolenie/
  wsparcie w tle, nie główny przepływ danych.
- **`prestashop app`** ma przerywaną bursztynową ramkę celowo — to jedyny
  krok w całym diagramie, który dziś odpala się **ręcznie**
  (`manage.py push_prestashop_product`), nie przez Celery Beat. Automatyzacja
  tego to kolejny krok (Faza 4), jeszcze niewdrożony.
- `MPD --- ADMIN` i `MPD --- MCP` to dwa niezależne, równoległe sposoby
  czytania/zasilania tej samej bazy — człowiek przez panel, Claude przez
  lokalny serwer MCP (`apps/MPD/management/commands/run_mcp_server.py`).

## Stack

- **Bazy danych**: PostgreSQL, osobna baza per aplikacja (MPD, matterhorn1,
  tabu, mada, web_agent), routing przez `core/db_routers.py`.
- **Kolejka i harmonogram**: Celery, Redis jako broker; harmonogram i wyniki
  zadań w PostgreSQL (`django-celery-beat`, `django-celery-results`).
- **Pliki i obrazy**: MinIO (S3-kompatybilne) dla wygenerowanych plików XML
  i zdjęć produktów.
- **Środowiska**: produkcja na k3s; dev lokalnie przez docker-compose z
  tunelem SSH do bazy.
