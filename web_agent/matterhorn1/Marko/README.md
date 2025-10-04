# 🏷️ Agent Marko - Dokumentacja

## 📋 Opis

Agent Marko to zaawansowany system automatyzacji do przetwarzania produktów marki Marko w panelu Django Admin. System wykorzystuje **embeddings** i **AI** do inteligentnego mapowania produktów, ciągłego uczenia się i automatycznego przewidywania atrybutów.

## 🎯 Funkcjonalności

### ✅ Obsługiwane kategorie produktów:
- **Kostiumy Dwuczęściowe** - biustonosze, figi, kostiumy dwuczęściowe
- **Kostiumy Jednoczęściowe** - kostiumy one-piece, eleganckie stroje
- **Wszystkie Kategorie** - wszystkie produkty marki Marko

### 🧠 Zaawansowane funkcje z embeddings:
- **Baza wiedzy z embeddings** - semantyczne wyszukiwanie podobnych produktów
- **System uczenia się** - ciągłe doskonalenie na podstawie przetworzonych produktów
- **Inteligentne przewidywania** - atrybuty, kategorie, modele na podstawie podobieństwa
- **Hybrydowe podejście** - kombinacja reguł bazowych i embeddings
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
OPENAI_API_KEY=twoj_openai_key  # Wymagane dla embeddings
```

### 2. Instalacja zależności

```bash
cd web_agent/matterhorn1/Marko
pip install -r requirements.txt
```

### 3. Uruchomienie agenta

```bash
python marko_agent.py
```

### 4. Wybór kategorii

Po uruchomieniu zobaczysz menu:

```
🎯 === WYBÓR KATEGORII PRODUKTÓW MARKO ===

1. Kostiumy Dwuczęściowe
   📝 Biustonosze, figi, kostiumy dwuczęściowe - eleganckie stroje kąpielowe

2. Kostiumy Jednoczęściowe
   📝 Kostiumy jednoczęściowe, eleganckie one-piece

3. Wszystkie Kategorie Marko
   📝 Wszystkie produkty marki Marko

Wybierz kategorię (1-3):
```

## 📁 Struktura plików

```
web_agent/matterhorn1/Marko/
├── marko_agent.py                    # Główny plik uruchomieniowy
├── marko_category_manager.py         # Menedżer kategorii produktów
├── marko_knowledge_base.py           # Baza wiedzy marki (reguły bazowe)
├── marko_embeddings_knowledge.py     # Baza wiedzy z embeddings
├── products_navigator.py             # Nawigacja po produktach
├── admin_login.py                    # Automatyczne logowanie
├── skip_products_list.py             # Lista pomijanych produktów
├── requirements.txt                  # Zależności Python
├── __init__.py                       # Inicjalizacja modułu
├── marko_embeddings.json            # Plik z embeddings (tworzony automatycznie)
└── README.md                         # Ta dokumentacja
```

## 🧠 Baza wiedzy z embeddings

### Modele Marko:
- **Ada** - kostiumy z usztywnianymi miseczkami, dekolt w kształcie serca, push-up

### Wzorce opisów:
- `kostium_usztywniony` - usztywniane miseczki, dolne fiszbiny
- `kostium_push_up` - push-up, unosząc biust
- `kostium_regulowany` - regulowane ramiączka, zapinany na plecach
- `figi_niski_stan` - niski stan, wiązanie po bokach
- `kostium_luksusowy` - glamour zdobienia, luksusowy charakter
- `kostium_pakowany` - pakowany w woreczek foliowy

### Embeddings:
- **OpenAI embeddings** - dla zaawansowanego wyszukiwania semantycznego
- **TF-IDF embeddings** - lokalne embeddings jako fallback
- **Klasteryzacja** - grupowanie podobnych produktów
- **Uczenie się** - system uczy się z każdego przetworzonego produktu

## ⚙️ Konfiguracja

### Parametry przetwarzania:
- **Batch size**: 15 produktów na raz
- **Czas oczekiwania**: 2 sekundy między produktami
- **Maksymalne próby**: 3
- **Uczenie**: włączone (embeddings)
- **Walidacja**: włączona

### Specjalne ustawienia kategorii:

#### Kostiumy Dwuczęściowe:
- Dodatkowe atrybuty: [24] (zapinane z tyłu)
- Wzorce: kostium_usztywniony, kostium_push_up, kostium_regulowany

#### Kostiumy Jednoczęściowe:
- Dodatkowe atrybuty: [25] (wyższy stan)
- Wzorce: kostium_jednoczesciowy, one-piece

## 🔧 Zarządzanie embeddings

### Sprawdzenie statystyk:
```python
from marko_knowledge_base import marko_knowledge
stats = marko_knowledge.get_learning_statistics()
print(stats)
```

### Eksport analizy:
```python
from marko_embeddings_knowledge import marko_embeddings
marko_embeddings.export_embeddings_for_analysis()
```

### Klasteryzacja produktów:
```python
clusters = marko_embeddings.cluster_products(n_clusters=5)
print(clusters)
```

## 🎨 Mapowanie kolorów

| Kolor producenta | Warianty polskie |
|------------------|------------------|
| Multicolor | wielokolorowy, multicolor |
| Black | czarny, black |
| White | biały, white |
| Fioletowy | fioletowy, purple, violet |
| Coral | koralowy, coral, różowy |
| Turkus | turkusowy, morski, niebieski |

## 📊 System uczenia się

Agent automatycznie:
- **Zapisuje embeddings** każdego przetworzonego produktu
- **Analizuje podobieństwa** między produktami
- **Przewiduje atrybuty** na podstawie podobnych produktów
- **Doskonali algorytmy** na podstawie nowych danych
- **Generuje raporty** skuteczności

### Pliki z danymi uczenia:
- `marko_embeddings.json` - zapisane embeddings produktów
- `marko_model.pkl` - model klasteryzacji (opcjonalnie)

## 🧪 Przykłady użycia embeddings

### Wyszukiwanie podobnych produktów:
```python
from marko_embeddings_knowledge import marko_embeddings

similar = marko_embeddings.find_similar_products(
    "kostium kąpielowy Ada usztywniane miseczki push-up", 
    limit=5
)
```

### Przewidywanie atrybutów:
```python
attributes = marko_embeddings.predict_attributes_from_description(
    "Biustonosz z usztywnianymi miseczkami i dekoltem w kształcie serca"
)
```

### Inteligentne przewidywania:
```python
from marko_knowledge_base import marko_knowledge

predictions = marko_knowledge.get_smart_predictions(
    title="Kostium kąpielowy Ada",
    description="Zmysłowy i kobiecy kostium z push-up..."
)
```

## ⚠️ Ważne uwagi

1. **Embeddings wymagają OpenAI API** - ustaw OPENAI_API_KEY
2. **System uczy się z każdym produktem** - im więcej przetworzonych produktów, tym lepsze przewidywania
3. **Hybrydowe podejście** - łączy reguły bazowe z embeddings
4. **Bezpieczeństwo** - agent nie usuwa danych, tylko mapuje
5. **Fallback** - jeśli embeddings niedostępne, używa reguł bazowych

## 🐛 Rozwiązywanie problemów

### Problem: Błąd OpenAI API
- Sprawdź OPENAI_API_KEY w `.env.dev`
- Upewnij się że masz dostęp do OpenAI API
- Sprawdź limity API

### Problem: Embeddings nie działają
- Sprawdź czy scikit-learn jest zainstalowany
- Sprawdź czy numpy jest zainstalowany
- System automatycznie przełączy się na reguły bazowe

### Problem: Niskie przewidywania
- Przetwórz więcej produktów dla lepszej bazy wiedzy
- Sprawdź statystyki embeddings
- Upewnij się że produkty są różnorodne

## 📈 Rozszerzanie funkcjonalności

### Dodanie nowej kategorii:
1. Dodaj kategorię w `marko_category_manager.py`
2. Rozszerz bazę wiedzy w `marko_knowledge_base.py`
3. Dodaj wzorce opisów
4. Przetestuj na małej grupie produktów

### Dodanie nowego modelu:
1. Dodaj charakterystyki w `marko_knowledge_base.py`
2. Zdefiniuj typowe atrybuty
3. Dodaj kolory i rozmiary
4. System automatycznie nauczy się z embeddings

### Dostosowanie embeddings:
1. Zmodyfikuj parametry w `marko_embeddings_knowledge.py`
2. Dostosuj liczbę klastrów
3. Zmień algorytm klasteryzacji
4. Przetestuj na danych testowych

## 📞 Wsparcie

W przypadku problemów:
1. Sprawdź logi w konsoli
2. Sprawdź plik `marko_embeddings.json`
3. Sprawdź statystyki embeddings
4. Sprawdź bazę wiedzy
5. Sprawdź rekomendacje systemu

---

**Agent Marko** - Inteligentne przetwarzanie produktów marki Marko z wykorzystaniem embeddings 🏷️🤖
