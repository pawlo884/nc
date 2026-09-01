# MCP server: katalog MPD (read-only)

Lokalny serwer MCP (`stdio`) udostępniający katalog MPD (produkty, warianty,
stany, ceny, kategorie) do Claude Desktop/Code. **Tylko odczyt** — żadne
narzędzie w tym serwerze nie modyfikuje danych.

Kod: [`apps/MPD/management/commands/run_mcp_server.py`](../src/apps/MPD/management/commands/run_mcp_server.py)

## Wymagania

- `postgres-ssh-tunnel` musi działać (`docker ps` — publikuje `127.0.0.1:5434`
  na hosta; bez niego serwer nie połączy się z dev bazą)
- `.venv/` w root projektu z zainstalowanymi zależnościami (`mcp` jest już
  w `requirements.txt`)

## Konfiguracja Claude Desktop

Dodaj do `claude_desktop_config.json` (Windows: `%APPDATA%\Claude\claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "nc-mpd-catalog": {
      "command": "C:\\Users\\pawlo\\Desktop\\kodowanie\\nc_project\\.venv\\Scripts\\python.exe",
      "args": [
        "C:\\Users\\pawlo\\Desktop\\kodowanie\\nc_project\\src\\manage.py",
        "run_mcp_server",
        "--settings=core.settings.dev"
      ]
    }
  }
}
```

Zrestartuj Claude Desktop po zmianie configu.

## Ręczny test uruchomienia

```powershell
.venv\Scripts\python.exe src\manage.py run_mcp_server --settings=core.settings.dev
```

Proces zawiśnie czekając na komunikację po stdio (to normalne — tak działa
transport `stdio`, nie ma nic do wypisania dopóki klient MCP się nie połączy).
`Ctrl+C` żeby przerwać. Jeśli od razu wywala błąd (np. połączenia z bazą) —
sprawdź czy `postgres-ssh-tunnel` działa.

## Dostępne narzędzia (tools)

| Tool                               | Opis                                                                  |
| ---------------------------------- | --------------------------------------------------------------------- |
| `search_products(query, limit=20)` | Szukaj produktów po nazwie (częściowe dopasowanie)                    |
| `get_product(product_id)`          | Pełny szczegół: warianty, kolory, rozmiary, ceny, stany, kategorie    |
| `get_stock_by_ean(ean)`            | Szybki lookup stanu/ceny po kodzie kreskowym                          |
| `list_categories()`                | Płaska lista kategorii (`id`/`name`/`parent_id`) do zbudowania drzewa |

## Rozszerzanie

Nowe narzędzie to nowa funkcja w `run_mcp_server.py` (moduł, nie metoda
klasy) zarejestrowana przez `mcp.add_tool(nowa_funkcja)` w `Command.handle()`.
Trzymaj się **tylko odczytu** (`.filter()`/`.get()`/`.first()`) — to jedyna
warstwa ochrony przed przypadkową modyfikacją danych przez narzędzie AI.
Jeśli kiedyś potrzebne będą akcje zapisujące (np. push do PrestaShop przez
MCP), rozważ osobny, jawnie nazwany serwer z dodatkową autoryzacją, nie
dopisywanie do tego.
