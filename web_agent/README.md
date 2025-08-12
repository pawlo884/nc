# Web Agent

Prosty agent do łączenia się ze stronami internetowymi w Django.

## 🚀 Funkcje

- **Podstawowe połączenie HTTP/HTTPS** - szybkie pobieranie danych
- **Browser Agent** - działanie w przeglądarce na żywo z Selenium
- **Custom headers i cookies** - pełna kontrola nad requestami
- **Obsługa proxy** - anonimowe połączenia
- **Parsowanie HTML** - z BeautifulSoup
- **Screenshots** - automatyczne robienie zrzutów ekranu
- **Logowanie akcji** - do bazy danych
- **Zarządzanie sesjami** - wielokrotne użycie
- **Obsługa błędów** - i timeout

## Instalacja

1. Zainstaluj wymagane biblioteki:
```bash
pip install beautifulsoup4 selenium lxml webdriver-manager
```

2. Dodaj aplikację do `INSTALLED_APPS` w `settings.py`:
```python
INSTALLED_APPS = [
    # ...
    'web_agent',
]
```

3. Wykonaj migracje:
```bash
python manage.py makemigrations web_agent
python manage.py migrate
```

## Szybkie użycie

### 1. Podstawowe połączenie HTTP
```python
from web_agent.agent import connect_to_website

# Szybkie połączenie ze stroną
result = connect_to_website(
    url="https://example.com",
    session_name="My Session"
)

print(f"Status: {result['status_code']}")
print(f"Title: {result['title']}")
print(f"Content length: {result['content_length']}")
```

### 2. Browser Agent - działanie w przeglądarce na żywo
```python
from web_agent.browser_agent import navigate_with_browser, create_browser_agent

# Szybka nawigacja (headless)
result = navigate_with_browser(
    url="https://example.com",
    session_name="Browser Session",
    headless=True  # False = widoczna przeglądarka
)

print(f"Title: {result['title']}")
print(f"Current URL: {result['current_url']}")
```

### 3. Interaktywna praca z przeglądarką
```python
# Utwórz agenta (widoczna przeglądarka)
agent = create_browser_agent(
    session_name="Interactive Session",
    url="https://example.com",
    headless=False  # Widoczna przeglądarka
)

# Przejdź do strony
agent.navigate_to("https://example.com")

# Wypełnij formularz
agent.type_text("input[name='username']", "user123")
agent.type_text("input[name='password']", "pass123")

# Kliknij przycisk
agent.click_element("button[type='submit']")

# Zrób screenshot
screenshot_path = agent.take_screenshot("page.png")

# Zamknij przeglądarkę
agent.close()
```

### 4. Z custom headers
```python
result = connect_to_website(
    url="https://api.example.com/data",
    session_name="API Session",
    headers={
        'Accept': 'application/json',
        'Authorization': 'Bearer token123'
    }
)
```

### 5. Z proxy
```python
result = connect_to_website(
    url="https://example.com",
    session_name="Proxy Session",
    proxy="http://proxy.example.com:8080"
)
```

## Testowanie

Uruchom testy:
```bash
# Test podstawowego agenta
python test_web_agent.py

# Test browser agenta
python test_browser_agent.py
```

## 🎯 Funkcje Browser Agent

- **Nawigacja w przeglądarce** - Chrome z Selenium
- **Interaktywne elementy** - klikanie, wpisywanie tekstu
- **Screenshots** - automatyczne zrzuty ekranu
- **Oczekiwanie na elementy** - inteligentne czekanie
- **Przewijanie** - do konkretnych elementów
- **Tryb headless** - lub widoczna przeglądarka
- **Obsługa formularzy** - wypełnianie pól
- **JavaScript** - wykonuje skrypty JS

## Modele

- `WebSession` - sesje web scraping
- `ScrapingTask` - zadania scraping
- `ScrapingResult` - wyniki scraping
- `WebAgentLog` - logi akcji

## Przykład pełnego użycia

### HTTP Agent
```python
from web_agent.agent import create_web_agent
from web_agent.models import WebSession

# Utwórz sesję
session = WebSession.objects.create(
    name="Test Session",
    url="https://example.com",
    user_agent="Custom User Agent",
    headers={'Accept': 'text/html'},
    timeout=30
)

# Utwórz agenta
agent = create_web_agent(session)

# Połącz się ze stroną
result = agent.connect_to_page("https://example.com")
print(result)
```

### Browser Agent
```python
from web_agent.browser_agent import create_browser_agent

# Utwórz browser agenta
agent = create_browser_agent(
    session_name="Browser Session",
    url="https://example.com",
    headless=False  # Widoczna przeglądarka
)

try:
    # Przejdź do strony
    result = agent.navigate_to("https://example.com")
    
    # Wypełnij formularz
    agent.type_text("input[name='search']", "Python Django")
    agent.click_element("button[type='submit']")
    
    # Zrób screenshot
    screenshot = agent.take_screenshot("result.png")
    
finally:
    # Zawsze zamknij przeglądarkę
    agent.close()
``` 