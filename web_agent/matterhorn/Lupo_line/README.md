# 🏊 Agent Lupo Line - Dokumentacja

## 📋 Opis

Agent Lupo Line to wyspecjalizowany system automatyzacji do przetwarzania produktów marki Lupo Line w panelu Django Admin. System obsługuje różne kategorie produktów i wykorzystuje zaawansowaną bazę wiedzy do inteligentnego mapowania produktów.

## 🎯 Funkcjonalności

### ✅ Obsługiwane kategorie produktów:
- **Biustonosze** - biustonosze, bralety, figi, kopy
- **Stroje Jednoczęściowe** - kostiumy one-piece, stroje jednoczęściowe
- **Szorty Kąpielowe** - szorty, spodenki kąpielowe
- **Wszystkie Kategorie** - wszystkie produkty Lupo Line

### 🧠 Zaawansowane funkcje:
- **Baza wiedzy** - specyficzna dla marki Lupo Line
- **System uczenia** - ciągłe doskonalenie algorytmów
- **Walidacja spójności** - sprawdzanie poprawności mapowania
- **Lista pomijanych produktów** - zarządzanie duplikatami
- **Nawigacja automatyczna** - przechodzenie przez produkty

## 🚀 Uruchomienie

### 1. Konfiguracja środowiska

Ustaw zmienne środowiskowe w pliku `.env.dev`:

```bash
DJANGO_ADMIN_USERNAME=twoj_username
DJANGO_ADMIN_PASSWORD=twoje_haslo
DJANGO_ADMIN_URL=http://localhost:8000/admin/
```

### 2. Uruchomienie agenta

```bash
cd web_agent/matterhorn/Lupo_line
python lupo_line_agent.py
```

### 3. Wybór kategorii

Po uruchomieniu zobaczysz menu:

```
🎯 === WYBÓR KATEGORII PRODUKTÓW LUPO LINE ===

1. Biustonosze
   📝 Biustonosze, bralety, figi, kopy

2. Stroje Jednoczęściowe
   📝 Stroje jednoczęściowe, kostiumy one-piece

3. Szorty Kąpielowe
   📝 Szorty, spodenki kąpielowe

4. Wszystkie Kategorie
   📝 Wszystkie produkty Lupo Line

Wybierz kategorię (1-4):
```

## 📁 Struktura plików

```
web_agent/matterhorn/Lupo_line/
├── lupo_line_agent.py          # Główny plik uruchomieniowy
├── category_manager.py         # Menedżer kategorii produktów
├── products_navigator.py       # Nawigacja po produktach
├── admin_login.py             # Automatyczne logowanie
├── lupo_line_knowledge_base.py # Baza wiedzy marki
├── agent_learning_system.py   # System uczenia
├── skip_products_list.py      # Lista pomijanych produktów
├── test_*.py                  # Pliki testowe
└── README.md                  # Ta dokumentacja
```

## 🧠 Baza wiedzy

### Modele Lupo Line:
- **Sofia** - regulowane, ramiączka regulowane
- **Ember** - na fiszbinach, usztywniane miseczki
- **Aqua** - usztywniane miseczki, wiązane na szyi
- **Wave** - miękkie miseczki, na fiszbinach
- **Mirage** - wyższy stan, regulowane
- **Coral** - regulowane (Coral to nazwa modelu!)
- **Gabriella** - regulowane, wyższy stan

### Wzorce opisów:
- `figi_regulowane` - regulowane figi
- `biustonosz_usztywniony` - biustonosze z fiszbinami
- `biustonosz_miekki` - miękkie biustonosze
- `wiazany_na_szyi` - wiązane na szyi
- `stroj_jednoczesciowy` - stroje jednoczęściowe
- `stroj_jednoczesciowy_z_biustonoszem` - z wbudowanym biustonoszem

## ⚙️ Konfiguracja

### Parametry przetwarzania:
- **Batch size**: 10 produktów na raz
- **Czas oczekiwania**: 2 sekundy między produktami
- **Maksymalne próby**: 3
- **Uczenie**: włączone
- **Walidacja**: włączona

### Specjalne ustawienia kategorii:

#### Stroje Jednoczęściowe:
- Dodatkowe atrybuty: [25] (wyższy stan)
- Wzorce: stroj_jednoczesciowy, stroj_jednoczesciowy_z_biustonoszem

#### Biustonosze:
- Wzorce: biustonosz_usztywniony, biustonosz_miekki, wiazany_na_szyi

## 🔧 Zarządzanie listą pomijanych produktów

### Dodanie produktu do listy pomijanych:
```bash
cd web_agent
python manage_skip_list.py add 214962
```

### Sprawdzenie statusu:
```bash
cd web_agent
python manage_skip_list.py status
```

### Usunięcie produktu:
```bash
cd web_agent
python manage_skip_list.py remove 214962
```

## 📊 System uczenia

Agent automatycznie:
- Zapisuje dane o przetwarzanych produktach
- Analizuje wzorce i korelacje
- Doskonali algorytmy na podstawie nowych danych
- Generuje raporty skuteczności

### Plik z danymi uczenia:
- `lupo_line_learned_data.json` - zapisane dane uczenia

## 🎨 Mapowanie kolorów

| Kolor producenta | Warianty polskie |
|------------------|------------------|
| Multicolor | wielokolorowy, multicolor |
| Black | czarny, black |
| White | biały, white |
| Turkus | turkusowy, morski, niebieski |
| Coral | koralowy, coral, różowy |

## ⚠️ Ważne uwagi

1. **Coral to nazwa modelu** - nie mylić z kolorem!
2. **Walidacja spójności** - agent sprawdza czy dane są zgodne z bazą wiedzy
3. **Lista pomijanych** - produkty duplikaty są automatycznie pomijane
4. **Uczenie** - system ciągle się uczy i doskonali
5. **Bezpieczeństwo** - agent nie usuwa danych, tylko mapuje

## 🐛 Rozwiązywanie problemów

### Problem: Nie można się zalogować
- Sprawdź dane logowania w `.env.dev`
- Upewnij się że serwer Django działa
- Sprawdź czy ChromeDriver jest zainstalowany

### Problem: Nie ma produktów do przetwarzania
- Sprawdź filtry kategorii
- Upewnij się że są niezmapowane produkty
- Sprawdź listę pomijanych produktów

### Problem: Błędy mapowania
- Sprawdź bazę wiedzy
- Dodaj nowe wzorce do `lupo_line_knowledge_base.py`
- Sprawdź logi uczenia

## 📈 Rozszerzanie funkcjonalności

### Dodanie nowej kategorii:
1. Dodaj kategorię w `category_manager.py`
2. Rozszerz bazę wiedzy w `lupo_line_knowledge_base.py`
3. Dodaj wzorce opisów
4. Przetestuj na małej grupie produktów

### Dodanie nowego modelu:
1. Dodaj charakterystyki w `lupo_line_knowledge_base.py`
2. Zdefiniuj typowe atrybuty
3. Dodaj kolory i rozmiary
4. Przetestuj mapowanie

## 📞 Wsparcie

W przypadku problemów:
1. Sprawdź logi w konsoli
2. Sprawdź plik `lupo_line_learned_data.json`
3. Sprawdź listę pomijanych produktów
4. Sprawdź bazę wiedzy

---

**Agent Lupo Line** - Inteligentne przetwarzanie produktów marki Lupo Line 🏊‍♀️


