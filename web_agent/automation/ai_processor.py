"""
Moduł przetwarzania danych produktów przez OpenAI/HuggingFace.
"""
import logging
from typing import Dict, Optional, List
import os
import time
import sys
from pydantic import BaseModel, Field, field_validator

# Ustaw kodowanie stdout na UTF-8 dla poprawnego wyświetlania polskich znaków
if sys.stdout.encoding is None or sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except (AttributeError, ValueError):
        # Python < 3.7 lub stdout nie można przekonfigurować
        pass

logger = logging.getLogger(__name__)


def is_figi_product(product_name: str) -> bool:
    """
    Sprawdza czy produkt to figi kąpielowe na podstawie nazwy.
    
    Args:
        product_name: Nazwa produktu
        
    Returns:
        True jeśli produkt to figi kąpielowe
    """
    if not product_name:
        return False
    
    name_lower = product_name.lower()
    # Sprawdź czy nazwa zawiera "figi" (ale nie "figi kąpielowe" jako część kostiumu)
    figi_keywords = ['figi', 'figi kąpielowe', 'figi kapielowe']
    
    # Jeśli nazwa zawiera "figi" i nie zawiera "kostium" ani "dwuczęściowy"
    if any(keyword in name_lower for keyword in figi_keywords):
        # Upewnij się, że to nie jest kostium dwuczęściowy z figami
        if 'kostium' not in name_lower and 'dwuczęściowy' not in name_lower:
            return True
        # Jeśli zawiera "figi" ale też "kostium", sprawdź kontekst
        if 'figi' in name_lower and 'kostium' in name_lower:
            # Jeśli "figi" pojawia się przed "kostium" lub jest głównym słowem
            figi_index = name_lower.find('figi')
            kostium_index = name_lower.find('kostium')
            if figi_index < kostium_index or figi_index != -1:
                return True
    
    return False


class ProductNameStructure(BaseModel):
    """
    Struktura nazwy produktu zapewniająca spójność i profesjonalizm.
    Format: "Kostium kąpielowy [nazwa_modelu]" lub "Figi kąpielowe [nazwa_modelu]"
    """
    base_type: str = Field(
        ...,
        description="Podstawowy typ produktu - 'Kostium kąpielowy' lub 'Figi kąpielowe'",
        min_length=3,
        max_length=50
    )
    model_name: str = Field(
        ...,
        description="Nazwa modelu produktu (np. 'Ada', 'Lupo', 'Elegant') - WYMAGANE",
        min_length=1,
        max_length=30
    )
    final_name: str = Field(
        ...,
        description="Finalna, gotowa nazwa produktu w formacie 'Kostium kąpielowy [nazwa_modelu]' (max 100 znaków)",
        min_length=5,
        max_length=100
    )

    def to_final_name(self) -> str:
        """
        Zwraca finalną nazwę produktu w formacie 'Kostium kąpielowy [nazwa_modelu]' lub 'Figi kąpielowe [nazwa_modelu]'.
        Zawsze buduje z base_type i model_name, ignorując final_name z JSON.
        """
        # Użyj base_type zamiast hardcoded "Kostium kąpielowy"
        base = self.base_type
        if self.model_name and self.model_name.strip():
            return f"{base} {self.model_name.strip()}".strip()
        return base

    @field_validator('base_type', 'final_name', 'model_name')
    @classmethod
    def validate_required_fields(cls, v: str) -> str:
        """Walidacja wymaganych pól tekstowych"""
        if not v or not v.strip():
            raise ValueError("Pole nie może być puste")
        return v.strip()

    @field_validator('base_type')
    @classmethod
    def validate_base_type(cls, v: str) -> str:
        """Walidacja base_type - zwraca 'Kostium kąpielowy' lub 'Figi kąpielowe'"""
        # Normalizuj do dozwolonych wartości
        v_lower = v.lower().strip()
        if 'figi' in v_lower:
            return "Figi kąpielowe"
        return "Kostium kąpielowy"


class ProductDescriptionStructure(BaseModel):
    """
    Struktura opisu produktu zapewniająca spójność dla wszystkich produktów.
    """
    introduction: str = Field(
        ...,
        description="Krótkie wprowadzenie (jedno zdanie) opisujące produkt",
        min_length=30,
        max_length=200
    )
    top_features: List[str] = Field(
        default=[],
        description="Lista cech góry (biustonosz) - każda cecha jako osobny string. Dla fig kąpielowych może być pusta lista [].",
        min_length=0,
        max_length=10
    )
    bottom_features: List[str] = Field(
        ...,
        description="Lista cech dołu (figi) - każda cecha jako osobny string",
        min_length=1,
        max_length=10
    )
    finishing: str = Field(
        ...,
        description="Opis wykończenia i zdobień",
        min_length=50,
        max_length=300
    )
    packaging: str = Field(
        ...,
        description="Opis pakowania produktu",
        min_length=30,
        max_length=200
    )
    size_tip: str = Field(
        ...,
        description="Wskazówka dotycząca rozmiaru (np. dopasowany krój, polecany rozmiar)",
        min_length=30,
        max_length=200
    )

    def to_formatted_text(self) -> str:
        """
        Konwertuje strukturę na sformatowany tekst opisu produktu.
        Dla fig kąpielowych pomija sekcję "Góra (biustonosz)".
        """
        lines = [self.introduction, ""]
        
        # Dodaj sekcję "Góra" tylko jeśli top_features nie jest puste i nie zawiera tylko "brak góry"
        has_top = self.top_features and len(self.top_features) > 0
        is_only_brak_gory = has_top and len(self.top_features) == 1 and self.top_features[0].lower().strip() == "brak góry"
        
        if has_top and not is_only_brak_gory:
            lines.extend([
                "Góra (biustonosz)",
                "",
                *[f"{feature}" for feature in self.top_features],
                ""
            ])
        
        # Zawsze dodaj sekcję "Dół"
        lines.extend([
            "Dół (figi)",
            "",
            *[f"{feature}" for feature in self.bottom_features],
            "",
            "Wykończenie",
            "",
            self.finishing,
            "",
            "Pakowanie",
            "",
            self.packaging,
            "",
            "Wskazówka rozmiarowa",
            self.size_tip
        ])
        return "\n".join(lines)

    @field_validator('introduction', 'finishing', 'packaging', 'size_tip')
    @classmethod
    def validate_text_fields(cls, v: str) -> str:
        """Walidacja i normalizacja pól tekstowych"""
        if not v or not v.strip():
            raise ValueError("Pole nie może być puste")
        return v.strip()

    @field_validator('top_features', 'bottom_features')
    @classmethod
    def validate_features(cls, v: List[str]) -> List[str]:
        """Walidacja listy cech"""
        if not v:
            raise ValueError("Lista cech nie może być pusta")
        return [feature.strip() for feature in v if feature.strip()]


class AIProcessor:
    """Klasa do modyfikacji danych produktów przez OpenAI/HuggingFace"""

    def __init__(self, api_key: Optional[str] = None, api_type: Optional[str] = None):
        """
        Inicjalizacja procesora AI.

        Args:
            api_key: Klucz API. Jeśli None, próbuje pobrać z zmiennych środowiskowych.
            api_type: Typ API - 'openai' lub 'huggingface'. Jeśli None, próbuje automatycznie wykryć.
        """
        if api_key is None:
            # Najpierw sprawdź HF_TOKEN (preferowany - działa z HuggingFace Router API)
            api_key = os.getenv('HF_TOKEN')
            if api_key:
                api_type = 'huggingface'
            else:
                # Sprawdź OPENAI_API_KEY_NOVITA
                api_key = os.getenv('OPENAI_API_KEY_NOVITA')
                if api_key:
                    api_type = 'openai'
                else:
                    # Fallback do OPENAI_API_KEY
                    api_key = os.getenv('OPENAI_API_KEY')
                    if api_key:
                        api_type = 'openai'

        if not api_key:
            raise ValueError(
                "API key is required. Set OPENAI_API_KEY_NOVITA, HF_TOKEN, or OPENAI_API_KEY environment variable."
            )

        self.api_key = api_key
        self.api_type = api_type or self._detect_api_type()

        if self.api_type == 'openai':
            from openai import OpenAI
            self.client = OpenAI(api_key=api_key)
            logger.info("AIProcessor zainicjalizowany z OpenAI")
        elif self.api_type == 'huggingface':
            # Użyj HuggingFace Router API (obsługuje modele przez OpenAI-compatible API)
            from openai import OpenAI
            self.client = OpenAI(
                base_url="https://router.huggingface.co/v1",
                api_key=api_key
            )
            logger.info(
                "AIProcessor zainicjalizowany z HuggingFace Router API")
        else:
            raise ValueError(f"Nieobsługiwany typ API: {self.api_type}")

    def _detect_api_type(self) -> str:
        """Automatycznie wykrywa typ API na podstawie klucza"""
        if 'hf_' in self.api_key or 'hf-' in self.api_key:
            return 'huggingface'
        else:
            return 'openai'

    def enhance_product_description(self, original_description: str, product_name: str = None, use_structured: bool = True) -> str:
        """
        Ulepsza opis produktu przez AI z użyciem strukturyzowanej formy (Pydantic).

        Args:
            original_description: Oryginalny opis produktu
            product_name: Nazwa produktu (opcjonalne, używane do wykrywania typu produktu)
            use_structured: Czy używać strukturyzowanej formy (Pydantic). Domyślnie True.

        Returns:
            Ulepszony opis produktu
        """
        if not original_description or not original_description.strip():
            return ""

        try:
            if use_structured:
                return self._enhance_with_structure(original_description, product_name)
            else:
                return self._enhance_legacy(original_description)
        except Exception as e:
            logger.error(f"Błąd podczas ulepszania opisu przez AI: {e}")
            # Fallback do legacy metody
            logger.info("Próba użycia legacy metody...")
            try:
                return self._enhance_legacy(original_description)
            except Exception as fallback_error:
                logger.error(
                    f"Błąd również w legacy metodzie: {fallback_error}")
                return original_description

    def _truncate_fields_to_limits(self, data: Dict) -> Dict:
        """
        Automatycznie skraca pola w danych do limitów zdefiniowanych w ProductDescriptionStructure.

        Args:
            data: Słownik z danymi do walidacji

        Returns:
            Słownik ze skróconymi polami
        """
        limits = {
            'introduction': 200,
            'finishing': 300,
            'packaging': 200,
            'size_tip': 200
        }

        truncated_data = data.copy()

        for field, max_length in limits.items():
            if field in truncated_data and isinstance(truncated_data[field], str):
                if len(truncated_data[field]) > max_length:
                    # Skróć do max_length, zachowując pełne słowa
                    truncated = truncated_data[field][:max_length]
                    # Znajdź ostatnią spację przed limitem, aby nie przecinać słów
                    last_space = truncated.rfind(' ')
                    if last_space > max_length * 0.8:  # Jeśli ostatnia spacja jest blisko końca
                        truncated = truncated[:last_space]
                    truncated_data[field] = truncated.strip() + '...'
                    logger.debug(
                        f"Skrócono pole '{field}' z {len(data[field])} do {len(truncated_data[field])} znaków")

        # Skróć również top_features i bottom_features jeśli są zbyt długie
        for feature_list_name in ['top_features', 'bottom_features']:
            if feature_list_name in truncated_data and isinstance(truncated_data[feature_list_name], list):
                truncated_data[feature_list_name] = [
                    feature[:300] + '...' if len(feature) > 300 else feature
                    for feature in truncated_data[feature_list_name]
                ]

        return truncated_data

    def _enhance_with_structure(self, original_description: str, product_name: str = None) -> str:
        """
        Ulepsza opis produktu używając strukturyzowanej formy (Pydantic).
        """
        import json

        # Sprawdź czy to figi kąpielowe
        is_figi = False
        if product_name:
            is_figi = is_figi_product(product_name)

        # Dostosuj prompt w zależności od typu produktu
        if is_figi:
            product_type_instruction = "To są FIGI KĄPIELOWE - produkt składa się TYLKO z dołu (figi), NIE MA góry (biustonosza). NIE generuj sekcji 'Góra (biustonosz)' - produkt to tylko figi."
            top_features_instruction = "top_features: NIE UŻYWAJ - produkt to tylko figi, nie ma góry. Ustaw jako pustą listę []."
        else:
            product_type_instruction = "To jest KOSTIUM KĄPIELOWY - produkt składa się z góry (biustonosz) i dołu (figi)."
            top_features_instruction = "top_features: Lista cech góry (biustonosz) - WYMAGANE MINIMUM 1 cecha! Każda cecha jako osobny string w formacie \"cecha – elegancki opis korzyści\" (np. \"usztywniane miseczki z dolnymi fiszbinami – zapewniają stabilne podtrzymanie i pięknie modelują biust\"). Max 10 cech, każda max 300 znaków. Jeśli produkt nie ma góry, użyj [\"brak góry\"]."

        system_prompt = f"""Jesteś ekspertem od copywritingu e-commerce specjalizującym się w bieliźnie i kostiumach kąpielowych.

{product_type_instruction}

TWOJE ZADANIE:
Przekształć poniższy opis produktu na bardziej profesjonalny, przyciągający i sprzedażowy opis przeznaczony dla sklepu internetowego z bielizną i kostiumami kąpielowymi. Użyj eleganckiego, kobiecego i zmysłowego języka, skup się na cechach funkcjonalnych i estetycznych produktu. Podziel opis na sekcje: {"\"Dół\", \"Wykończenie\", \"Pakowanie\" oraz \"Wskazówka rozmiarowa\" (BEZ sekcji \"Góra\")" if is_figi else "\"Góra\", \"Dół\", \"Wykończenie\", \"Pakowanie\" oraz \"Wskazówka rozmiarowa\""}. Dodaj konkretne wskazówki dla klienta, aby łatwiej wybrał rozmiar i używał produktu.

WYTYCZNE:

1. STYL I TON:
- Elegancki, kobiecy, zmysłowy
- Profesjonalny, ale przyjazny i zachęcający
- Skup się na korzyściach dla klientki
- Używaj języka, który buduje emocjonalny związek z produktem
- Podkreślaj wyjątkowość i jakość

2. STRUKTURA (JSON) - WAŻNE: PRZESTRZEGAJ DOKŁADNIE LIMITÓW ZNAKÓW:
- introduction: Krótkie, przyciągające wprowadzenie (jedno zdanie) opisujące produkt w elegancki sposób - MAKSYMALNIE 200 znaków!
- {top_features_instruction}
- bottom_features: Lista cech dołu (figi) - WYMAGANE MINIMUM 1 cecha! Każda cecha jako osobny string w formacie "cecha – elegancki opis korzyści" (np. "krój midi – wygodnie układa się na biodrach, subtelnie podkreślając kobiece kształty"). Max 10 cech, każda max 300 znaków. Jeśli produkt nie ma dołu, użyj ["brak dołu"].
- finishing: Elegancki opis wykończenia i zdobień, podkreślający luksusowy charakter (50-300 znaków, MAKSYMALNIE 300 znaków!)
- packaging: Opis pakowania produktu z naciskiem na praktyczność i wygodę (30-200 znaków, MAKSYMALNIE 200 znaków!)
- size_tip: Konkretne wskazówki rozmiarowe dla klienta, aby łatwiej wybrał rozmiar (30-200 znaków, MAKSYMALNIE 200 znaków!)

UWAGA: Jeśli przekroczysz limity znaków, odpowiedź zostanie odrzucona. Bądź zwięzły, ale elegancki!
UWAGA: {"bottom_features MUSI zawierać przynajmniej 1 element - nie może być pustą listą!" if is_figi else "top_features i bottom_features MUSZĄ zawierać przynajmniej 1 element - nie mogą być pustymi listami!"}

TWOJE ZADANIE:
Przekształć poniższy opis produktu na bardziej profesjonalny, przyciągający i sprzedażowy opis przeznaczony dla sklepu internetowego z bielizną i kostiumami kąpielowymi. Użyj eleganckiego, kobiecego i zmysłowego języka, skup się na cechach funkcjonalnych i estetycznych produktu. Podziel opis na sekcje: „Góra”, „Dół”, „Wykończenie”, „Pakowanie” oraz „Wskazówka rozmiarowa”. Dodaj konkretne wskazówki dla klienta, aby łatwiej wybrał rozmiar i używał produktu.

WYTYCZNE:

1. STYL I TON:
- Elegancki, kobiecy, zmysłowy
- Profesjonalny, ale przyjazny i zachęcający
- Skup się na korzyściach dla klientki
- Używaj języka, który buduje emocjonalny związek z produktem
- Podkreślaj wyjątkowość i jakość

2. STRUKTURA (JSON) - WAŻNE: PRZESTRZEGAJ DOKŁADNIE LIMITÓW ZNAKÓW:
- introduction: Krótkie, przyciągające wprowadzenie (jedno zdanie) opisujące produkt w elegancki sposób - MAKSYMALNIE 200 znaków!
- top_features: Lista cech góry (biustonosz) - WYMAGANE MINIMUM 1 cecha! Każda cecha jako osobny string w formacie "cecha – elegancki opis korzyści" (np. "usztywniane miseczki z dolnymi fiszbinami – zapewniają stabilne podtrzymanie i pięknie modelują biust"). Max 10 cech, każda max 300 znaków. Jeśli produkt nie ma góry, użyj ["brak góry"].
- bottom_features: Lista cech dołu (figi) - WYMAGANE MINIMUM 1 cecha! Każda cecha jako osobny string w formacie "cecha – elegancki opis korzyści" (np. "niski stan – subtelnie podkreśla kobiece kształty"). Max 10 cech, każda max 300 znaków. Jeśli produkt nie ma dołu, użyj ["brak dołu"].
- finishing: Elegancki opis wykończenia i zdobień, podkreślający luksusowy charakter (50-300 znaków, MAKSYMALNIE 300 znaków!)
- packaging: Opis pakowania produktu z naciskiem na praktyczność i wygodę (30-200 znaków, MAKSYMALNIE 200 znaków!)
- size_tip: Konkretne wskazówki rozmiarowe dla klienta, aby łatwiej wybrał rozmiar (30-200 znaków, MAKSYMALNIE 200 znaków!)

UWAGA: Jeśli przekroczysz limity znaków, odpowiedź zostanie odrzucona. Bądź zwięzły, ale elegancki!
UWAGA: top_features i bottom_features MUSZĄ zawierać przynajmniej 1 element - nie mogą być pustymi listami!

3. FORMAT CECH (top_features i bottom_features):
- Każda cecha powinna być w formacie: "nazwa cechy – elegancki opis korzyści" (np. "ramiączka odpinane i regulowane – zapewniają wygodę i możliwość noszenia na różne sposoby, idealne na opaleniznę")
- Używaj myślnika (–) do oddzielenia nazwy od opisu
- Opisuj korzyści, nie tylko cechy techniczne
- Używaj zmysłowego, kobiecego języka
- Bądź konkretny: wymień fiszbiny, wiązania, zapięcia, materiały, rozmiary push-up itp.

4. CO UWZGLĘDNIĆ W TOP_FEATURES (góra/biustonosz):
- Typ miseczek (usztywniane, push-up, wyjmowane) i ich korzyści
- Fiszbiny (dolne, kształt) i jak modelują sylwetkę
- Dekolt (kształt, głębokość) i jego efekt wizualny
- Zapięcie (z tyłu, z przodu, regulowane) i wygoda
- Ramiączka (odpinane, regulowane, szerokość) i możliwości stylizacji
- Rozmiary push-up (jeśli dostępne) i efekt optyczny
- Inne cechy konstrukcyjne z naciskiem na korzyści

5. CO UWZGLĘDNIĆ W BOTTOM_FEATURES (dół/figi):
- Stan (niski, wysoki) i efekt wizualny
- Podszewka (obecność, materiał) i komfort
- Wiązania (po bokach, z tyłu, regulowane) i możliwość dopasowania
- Krój i dopasowanie oraz jak podkreśla sylwetkę
- Inne cechy konstrukcyjne z naciskiem na korzyści

6. CO UWZGLĘDNIĆ W FINISHING:
- Zdobienia (glamour, hafty, aplikacje) i ich elegancja
- Detale dekoracyjne i luksusowy charakter
- Charakter wykończenia (luksusowy, elegancki, zmysłowy)
- Zastosowanie (wakacje, sesje zdjęciowe, plażowe chwile)

7. CO UWZGLĘDNIĆ W PACKAGING:
- Rodzaj opakowania (woreczek foliowy, pudełko) i jego praktyczność
- Wygoda na wyjazd i przechowywanie
- Dbałość o szczegóły

8. CO UWZGLĘDNIĆ W SIZE_TIP:
- Konkretne wskazówki dotyczące rozmiaru (zamówić większy/mniejszy)
- Informacje o kroju (dopasowany, luźny) i jak to wpływa na wybór
- Praktyczne porady dotyczące dopasowania
- Pomoc w wyborze odpowiedniego rozmiaru

9. JĘZYK I STYL:
- Używaj eleganckich, kobiecych określeń
- Podkreślaj zmysłowość i kobiecość
- Opisuj korzyści, nie tylko cechy
- Buduj emocjonalny związek z produktem
- Używaj pozytywnych, zachęcających sformułowań

10. CZEGO UNIKAĆ:
- Zbyt technicznego języka
- Sztampowych frazesów
- Zbyt agresywnych zachęt do zakupu
- Powtórzeń
- Zbyt długich opisów

ODPOWIEDŹ MUSI BYĆ W FORMACIE JSON zgodnym z podanym schematem."""

        if is_figi:
            user_prompt = f"Przekształć poniższy opis produktu na bardziej profesjonalny, przyciągający i sprzedażowy opis przeznaczony dla sklepu internetowego z bielizną i kostiumami kąpielowymi. Użyj eleganckiego, kobiecego i zmysłowego języka, skup się na cechach funkcjonalnych i estetycznych produktu. WAŻNE: To są FIGI KĄPIELOWE - produkt składa się TYLKO z dołu (figi), NIE MA góry. Ustaw top_features jako pustą listę []. Wyodrębnij WSZYSTKIE cechy dołu (figi) do bottom_features. bottom_features MUSI zawierać przynajmniej 1 element. Wyodrębnij również wykończenie, pakowanie i konkretne wskazówki rozmiarowe dla klienta:\n\n{original_description}"
        else:
            user_prompt = f"Przekształć poniższy opis produktu na bardziej profesjonalny, przyciągający i sprzedażowy opis przeznaczony dla sklepu internetowego z bielizną i kostiumami kąpielowymi. Użyj eleganckiego, kobiecego i zmysłowego języka, skup się na cechach funkcjonalnych i estetycznych produktu. WAŻNE: Wyodrębnij WSZYSTKIE cechy góry (biustonosz) do top_features i WSZYSTKIE cechy dołu (figi) do bottom_features. Każda lista MUSI zawierać przynajmniej 1 element. Jeśli nie ma informacji o górze/dole, użyj odpowiednio [\"brak góry\"] lub [\"brak dołu\"]. Wyodrębnij również wykończenie, pakowanie i konkretne wskazówki rozmiarowe dla klienta:\n\n{original_description}"

        # Próba użycia structured output (jeśli dostępne)
        try:
            if self.api_type == 'openai':
                model_name = "gpt-4o-mini"
                if os.getenv('OPENAI_API_KEY_NOVITA') == self.api_key:
                    model_name = "gpt-5.2"

                # Spróbuj użyć response_format dla structured output
                try:
                    logger.info(
                        "Wysyłam żądanie do OpenAI API (timeout: 30s)...")
                    print("[INFO] Wysyłam żądanie do OpenAI API (timeout: 30s)...")
                    print("[INFO] Czekam na odpowiedź...")
                    # Dla modelu gpt-5.2 używamy max_completion_tokens zamiast max_tokens
                    api_params = {
                        "model": model_name,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        "response_format": {"type": "json_object"},
                        "temperature": 0.7,
                        "timeout": 30
                    }
                    if model_name == "gpt-5.2":
                        api_params["max_completion_tokens"] = 1000
                    else:
                        api_params["max_tokens"] = 1000
                    response = self.client.chat.completions.create(
                        **api_params)
                    logger.info("Otrzymano odpowiedź z OpenAI API")
                    print("[INFO] Otrzymano odpowiedź z OpenAI API")
                except Exception:
                    # Fallback - zwykłe wywołanie bez response_format
                    logger.info("Fallback: wywołanie bez response_format...")
                    print("[INFO] Fallback: wywołanie bez response_format...")
                    print("[INFO] Czekam na odpowiedź...")
                    # Dla modelu gpt-5.2 używamy max_completion_tokens zamiast max_tokens
                    api_params = {
                        "model": model_name,
                        "messages": [
                            {"role": "system", "content": system_prompt +
                                "\n\nODPOWIEDŹ MUSI BYĆ TYLKO JSON, BEZ ŻADNYCH DODATKOWYCH KOMENTARZY."},
                            {"role": "user", "content": user_prompt}
                        ],
                        "temperature": 0.7,
                        "timeout": 30
                    }
                    if model_name == "gpt-5.2":
                        api_params["max_completion_tokens"] = 1000
                    else:
                        api_params["max_tokens"] = 1000
                    response = self.client.chat.completions.create(
                        **api_params)
                    logger.info("Otrzymano odpowiedź z OpenAI API (fallback)")
                    print("[INFO] Otrzymano odpowiedź z OpenAI API (fallback)")

                content = response.choices[0].message.content
                if not content:
                    raise ValueError("Pusta odpowiedź z API")

                logger.info("Przetwarzam odpowiedź z API...")
                print("[INFO] Przetwarzam odpowiedź z API...")
                content = content.strip()

                # Wyciągnij JSON z odpowiedzi (może być otoczony markdown)
                if "```json" in content:
                    content = content.split("```json")[
                        1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()

                # Parsuj JSON
                logger.info("Parsuję JSON z odpowiedzi...")
                print("[INFO] Parsuję JSON z odpowiedzi...")
                data = json.loads(content)
                logger.info("JSON sparsowany pomyślnie")
                print("[INFO] JSON sparsowany pomyślnie")

                # Skróć pola do limitów przed walidacją
                logger.info("Skracam pola do limitów...")
                print("[INFO] Skracam pola do limitów...")
                data = self._truncate_fields_to_limits(data)

                # Waliduj przez Pydantic
                logger.info("Waliduję dane przez Pydantic...")
                print("[INFO] Waliduję dane przez Pydantic...")
                description_structure = ProductDescriptionStructure(**data)
                logger.info("Walidacja zakończona pomyślnie")
                print("[INFO] Walidacja zakończona pomyślnie")

                # Konwertuj na tekst
                logger.info("Konwertuję strukturę na tekst...")
                print("[INFO] Konwertuję strukturę na tekst...")
                formatted_text = description_structure.to_formatted_text()

                logger.info(
                    f"Opis ulepszony przez AI ze strukturą (długość: {len(formatted_text)})")
                print(
                    f"[INFO] Opis ulepszony przez AI (długość: {len(formatted_text)} znaków)")
                return formatted_text

            elif self.api_type == 'huggingface':
                # Użyj OpenAI API z modelem gpt-5.2 zamiast HuggingFace
                # Pobierz klucz OpenAI (preferuj OPENAI_API_KEY, potem OPENAI_API_KEY_NOVITA)
                openai_key = os.getenv('OPENAI_API_KEY') or os.getenv(
                    'OPENAI_API_KEY_NOVITA')
                if not openai_key:
                    raise ValueError(
                        "Brak klucza OpenAI API dla modelu gpt-5.2")

                from openai import OpenAI
                openai_client = OpenAI(api_key=openai_key)

                max_retries = 2  # Zmniejszone z 5 do 2
                retry_delay = 3  # Zmniejszone z 5 do 3

                for attempt in range(max_retries):
                    try:
                        logger.info(
                            f"Próba {attempt + 1}/{max_retries} - wysyłam żądanie do OpenAI API (model: gpt-5.2, timeout: 30s)...")
                        print(
                            f"[INFO] Próba {attempt + 1}/{max_retries} - wysyłam żądanie do OpenAI API (model: gpt-5.2, timeout: 30s)...")
                        print("[INFO] Czekam na odpowiedź...")
                        response = openai_client.chat.completions.create(
                            model="gpt-5.2",
                            messages=[
                                {"role": "system", "content": system_prompt +
                                    "\n\nODPOWIEDŹ MUSI BYĆ TYLKO JSON, BEZ ŻADNYCH DODATKOWYCH KOMENTARZY."},
                                {"role": "user", "content": user_prompt}
                            ],
                            temperature=0.7,
                            # Zmienione z max_tokens na max_completion_tokens dla gpt-5.2
                            max_completion_tokens=1000,
                            timeout=30  # Zmniejszone z 120 do 30 sekund
                        )
                        logger.info(
                            f"Otrzymano odpowiedź z OpenAI API (model: gpt-5.2, próba {attempt + 1})")
                        print(
                            f"[INFO] Otrzymano odpowiedź z OpenAI API (model: gpt-5.2, próba {attempt + 1})")

                        content = response.choices[0].message.content
                        if not content:
                            raise ValueError("Pusta odpowiedź z API")

                        logger.info("Przetwarzam odpowiedź z OpenAI API...")
                        print("[INFO] Przetwarzam odpowiedź z OpenAI API...")
                        content = content.strip()

                        # Wyciągnij JSON
                        if "```json" in content:
                            content = content.split("```json")[
                                1].split("```")[0].strip()
                        elif "```" in content:
                            content = content.split(
                                "```")[1].split("```")[0].strip()

                        # Parsuj JSON
                        logger.info("Parsuję JSON z odpowiedzi...")
                        print("[INFO] Parsuję JSON z odpowiedzi...")
                        data = json.loads(content)
                        logger.info("JSON sparsowany pomyślnie")
                        print("[INFO] JSON sparsowany pomyślnie")

                        # Skróć pola do limitów przed walidacją
                        logger.info("Skracam pola do limitów...")
                        print("[INFO] Skracam pola do limitów...")
                        data = self._truncate_fields_to_limits(data)

                        # Waliduj przez Pydantic
                        logger.info("Waliduję dane przez Pydantic...")
                        print("[INFO] Waliduję dane przez Pydantic...")
                        description_structure = ProductDescriptionStructure(
                            **data)
                        logger.info("Walidacja zakończona pomyślnie")
                        print("[INFO] Walidacja zakończona pomyślnie")

                        formatted_text = description_structure.to_formatted_text()

                        logger.info(
                            f"Opis ulepszony przez AI ze strukturą (długość: {len(formatted_text)})")
                        print(
                            f"[INFO] Opis ulepszony przez AI (długość: {len(formatted_text)} znaków)")
                        return formatted_text

                    except json.JSONDecodeError as e:
                        logger.warning(
                            f"Błąd parsowania JSON (próba {attempt + 1}/{max_retries}): {e}")
                        if attempt < max_retries - 1:
                            time.sleep(retry_delay)
                            retry_delay = min(retry_delay * 2, 60)
                            continue
                        else:
                            raise
                    except Exception as e:
                        error_msg = str(e)
                        is_timeout = (
                            "504" in error_msg or "Gateway Timeout" in error_msg or
                            "timeout" in error_msg.lower() or "InternalServerError" in error_msg or
                            "Request timed out" in error_msg
                        )
                        if is_timeout and attempt < max_retries - 1:
                            logger.warning(
                                f"Timeout (próba {attempt + 1}/{max_retries}), czekam {retry_delay}s...")
                            time.sleep(retry_delay)
                            retry_delay = min(retry_delay * 2, 60)
                            continue
                        else:
                            raise

                # Jeśli nie udało się, rzuć wyjątek
                raise ValueError(
                    "Nie udało się wygenerować strukturyzowanego opisu")
            else:
                raise ValueError(f"Nieobsługiwany typ API: {self.api_type}")

        except Exception as e:
            logger.error(
                f"Błąd podczas generowania strukturyzowanego opisu: {e}")
            raise

    def _enhance_legacy(self, original_description: str) -> str:
        """
        Legacy metoda ulepszania opisu produktu (bez struktury Pydantic).
        """
        try:
            if self.api_type == 'openai':
                # Sprawdź czy używamy klucza Novita (może obsługiwać model gpt-5.2)
                model_name = "gpt-4o-mini"  # Domyślny model
                if os.getenv('OPENAI_API_KEY_NOVITA') == self.api_key:
                    model_name = "gpt-5.2"  # Spróbuj użyć modelu gpt-5.2

                response = self.client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {
                            "role": "system",
                            "content": """Jesteś ekspertem od copywritingu e-commerce specjalizującym się w modzie plażowej i strojach kąpielowych.

                            TWOJE ZADANIE:
                            Przekształć podany opis produktu w atrakcyjny, sprzedażowy tekst dla sklepu online.

                            WYTYCZNE:

                            1. STYL I TON:
                            - Przyjazny, inspirujący, lekko lifestyle'owy
                            - Zwracaj się do klienta w sposób naturalny
                            - Buduj emocjonalny związek z produktem

                            2. STRUKTURA OPISU:
                            - Chwytliwe otwarcie (1-2 zdania)
                            - Kluczowe cechy i korzyści (3-5 punktów)
                            - Szczegóły techniczne (materiał, krój, dopasowanie)
                            - Zachęta do zakupu

                            3. CO UWZGLĘDNIĆ:
                            - Rodzaj stroju (bikini, kostium, majtki, góra)
                            - Krój i fason
                            - Materiał i jego właściwości (szybkoschnący, elastyczny, UV)
                            - Dla kogo (typ sylwetki, styl życia)
                            - Okazje do noszenia (plaża, basen, wakacje)
                            - Unikalne cechy (fiszbiny, wyściółka, wiązania)

                            4. SEO:
                            - Naturalnie wpleć słowa kluczowe
                            - Unikaj keyword stuffing
                            - Długość: 100-200 słów

                            5. CZEGO UNIKAĆ:
                            - Przesadnych obietnic
                            - Sztampowych frazesów
                            - Zbyt technicznego języka
                            - Powtórzeń"""
                        },
                        {
                            "role": "user",
                            "content": f"Ulepsz ten opis produktu:\n\n{original_description}"
                        }
                    ],
                    temperature=0.7,
                    max_tokens=1000
                )

                if response.choices[0].message.content:
                    enhanced = response.choices[0].message.content.strip()
                else:
                    enhanced = original_description

            elif self.api_type == 'huggingface':
                # Użyj OpenAI API z modelem gpt-5.2 zamiast HuggingFace
                # Pobierz klucz OpenAI (preferuj OPENAI_API_KEY, potem OPENAI_API_KEY_NOVITA)
                openai_key = os.getenv('OPENAI_API_KEY') or os.getenv(
                    'OPENAI_API_KEY_NOVITA')
                if not openai_key:
                    raise ValueError(
                        "Brak klucza OpenAI API dla modelu gpt-5.2")

                from openai import OpenAI
                openai_client = OpenAI(api_key=openai_key)

                # Spróbuj kilka razy z retry w przypadku błędów 504/timeout
                max_retries = 2  # Zmniejszone z 5 do 2
                # Zmniejszony początkowy delay (3, 6 sekund)
                retry_delay = 3  # Zmniejszone z 5 do 3
                enhanced = None

                # Model do użycia
                model = "gpt-5.2"

                success = False
                for attempt in range(max_retries):
                    if success:
                        break

                    try:
                        logger.info(
                            f"Próba {attempt + 1}/{max_retries} z modelem {model} (OpenAI API)")
                        print(
                            f"[INFO] Próba {attempt + 1}/{max_retries} z modelem {model} (OpenAI API)")

                        response = openai_client.chat.completions.create(
                            model=model,
                            messages=[
                                {
                                    "role": "system",
                                    "content": """Jesteś ekspertem od copywritingu e-commerce specjalizującym się w modzie plażowej i strojach kąpielowych.

                            TWOJE ZADANIE:
                            Przekształć podany opis produktu w atrakcyjny, sprzedażowy tekst dla sklepu online.

                            WYTYCZNE:

                            1. STYL I TON:
                            - Przyjazny, inspirujący, lekko lifestyle'owy
                            - Zwracaj się do klienta w sposób naturalny
                            - Buduj emocjonalny związek z produktem

                            2. STRUKTURA OPISU:
                            - Chwytliwe otwarcie (1-2 zdania)
                            - Kluczowe cechy i korzyści (3-5 punktów)
                            - Szczegóły techniczne (materiał, krój, dopasowanie)
                            - Zachęta do zakupu

                            3. CO UWZGLĘDNIĆ:
                            - Rodzaj stroju (bikini, kostium, majtki, góra)
                            - Krój i fason
                            - Materiał i jego właściwości (szybkoschnący, elastyczny, UV)
                            - Dla kogo (typ sylwetki, styl życia)
                            - Okazje do noszenia (plaża, basen, wakacje)
                            - Unikalne cechy (fiszbiny, wyściółka, wiązania)

                            4. SEO:
                            - Naturalnie wpleć słowa kluczowe
                            - Unikaj keyword stuffing
                            - Długość: 100-200 słów

                            5. CZEGO UNIKAĆ:
                            - Przesadnych obietnic
                            - Sztampowych frazesów
                            - Zbyt technicznego języka
                            - Powtórzeń"""
                                },
                                {
                                    "role": "user",
                                    "content": f"Ulepsz ten opis produktu:\n\n{original_description}"
                                }
                            ],
                            temperature=0.7,
                            # Zmienione z max_tokens na max_completion_tokens dla gpt-5.2
                            max_completion_tokens=800,
                            timeout=30  # Zmniejszone z 120 do 30 sekund
                        )
                        logger.info(
                            f"Otrzymano odpowiedź z OpenAI API (model: gpt-5.2, próba {attempt + 1})")
                        print(
                            f"[INFO] Otrzymano odpowiedź z OpenAI API (model: gpt-5.2, próba {attempt + 1})")

                        if response.choices[0].message.content:
                            enhanced = response.choices[0].message.content.strip(
                            )
                        else:
                            enhanced = original_description

                        # Sukces - wyjdź z pętli
                        logger.info(f"Sukces z modelem {model}")
                        print(f"[INFO] Sukces z modelem {model}")
                        success = True
                        break

                    except Exception as e:
                        error_msg = str(e)
                        logger.warning(
                            f"Błąd z modelem {model}: {error_msg[:100]}")
                        print(
                            f"[DEBUG] Błąd z modelem {model}: {error_msg[:100]}")

                        # Jeśli to timeout/504, spróbuj retry
                        is_timeout = (
                            "504" in error_msg or "Gateway Timeout" in error_msg or
                            "timeout" in error_msg.lower() or "InternalServerError" in error_msg or
                            "Request timed out" in error_msg
                        )

                        if is_timeout:
                            # Przejdź do retry
                            if attempt < max_retries - 1:
                                logger.warning(
                                    f"Błąd timeout OpenAI API (próba {attempt + 1}/{max_retries}), "
                                    f"czekam {retry_delay}s i ponawiam...")
                                print(
                                    f"[INFO] Błąd timeout OpenAI API (próba {attempt + 1}/{max_retries}), "
                                    f"czekam {retry_delay}s i ponawiam...")
                                time.sleep(retry_delay)
                                # Exponential backoff, max 10s (zmniejszone z 60)
                                retry_delay = min(retry_delay * 2, 10)
                                continue  # Przejdź do następnej próby
                            else:
                                # Ostatnia próba - zwróć oryginalny opis
                                logger.error(
                                    f"Błąd timeout OpenAI API po {max_retries} próbach")
                                print(
                                    f"[INFO] Błąd timeout OpenAI API po {max_retries} próbach")
                                enhanced = original_description
                                success = True  # Zakończ pętle
                                break
                        else:
                            # Inny błąd - zwróć oryginalny opis
                            logger.error(
                                f"Błąd OpenAI API: {e}")
                            print(
                                f"[INFO] Błąd OpenAI API: {error_msg[:100]}")
                            enhanced = original_description
                            success = True  # Zakończ pętle
                            break

                # Jeśli HuggingFace nie zadziałało, spróbuj OpenAI jako fallback
                if not enhanced or enhanced == original_description:
                    openai_key = os.getenv(
                        'OPENAI_API_KEY_NOVITA') or os.getenv('OPENAI_API_KEY')
                    if openai_key and openai_key != self.api_key:
                        logger.info("Próba użycia OpenAI jako fallback...")
                        print("[DEBUG] Próba użycia OpenAI jako fallback...")
                        try:
                            from openai import OpenAI
                            openai_client = OpenAI(api_key=openai_key)

                            # Określ model OpenAI
                            model_name = "gpt-4o-mini"
                            if os.getenv('OPENAI_API_KEY_NOVITA') == openai_key:
                                model_name = "gpt-5.2"

                            response = openai_client.chat.completions.create(
                                model=model_name,
                                messages=[
                                    {
                                        "role": "system",
                                        "content": """Jesteś ekspertem od copywritingu e-commerce specjalizującym się w modzie plażowej i strojach kąpielowych.

                            TWOJE ZADANIE:
                            Przekształć podany opis produktu w atrakcyjny, sprzedażowy tekst dla sklepu online.

                            WYTYCZNE:

                            1. STYL I TON:
                            - Przyjazny, inspirujący, lekko lifestyle'owy
                            - Zwracaj się do klienta w sposób naturalny
                            - Buduj emocjonalny związek z produktem

                            2. STRUKTURA OPISU:
                            - Chwytliwe otwarcie (1-2 zdania)
                            - Kluczowe cechy i korzyści (3-5 punktów)
                            - Szczegóły techniczne (materiał, krój, dopasowanie)
                            - Zachęta do zakupu

                            3. CO UWZGLĘDNIĆ:
                            - Rodzaj stroju (bikini, kostium, majtki, góra)
                            - Krój i fason
                            - Materiał i jego właściwości (szybkoschnący, elastyczny, UV)
                            - Dla kogo (typ sylwetki, styl życia)
                            - Okazje do noszenia (plaża, basen, wakacje)
                            - Unikalne cechy (fiszbiny, wyściółka, wiązania)

                            4. SEO:
                            - Naturalnie wpleć słowa kluczowe
                            - Unikaj keyword stuffing
                            - Długość: 100-200 słów

                            5. CZEGO UNIKAĆ:
                            - Przesadnych obietnic
                            - Sztampowych frazesów
                            - Zbyt technicznego języka
                            - Powtórzeń"""
                                    },
                                    {
                                        "role": "user",
                                        "content": f"Ulepsz ten opis produktu:\n\n{original_description}"
                                    }
                                ],
                                temperature=0.7,
                                max_tokens=800,  # Zmniejszone dla szybszej odpowiedzi
                                timeout=30  # Zmniejszone z 120 do 30 sekund
                            )
                            logger.info(
                                "Otrzymano odpowiedź z OpenAI (fallback)")
                            print(
                                "[DEBUG] Otrzymano odpowiedź z OpenAI (fallback)")

                            if response.choices[0].message.content:
                                enhanced = response.choices[0].message.content.strip(
                                )
                                logger.info("Użyto OpenAI jako fallback")
                                print("[DEBUG] Użyto OpenAI jako fallback")
                        except Exception as fallback_error:
                            logger.error(
                                f"Błąd podczas fallback do OpenAI: {fallback_error}")
                            print(
                                f"[DEBUG] Błąd podczas fallback do OpenAI: {fallback_error}")

                if not enhanced:
                    enhanced = original_description
            else:
                raise ValueError(f"Nieobsługiwany typ API: {self.api_type}")

            logger.info(f"Opis ulepszony przez AI (długość: {len(enhanced)})")
            return enhanced

        except Exception as e:
            logger.error(f"Błąd podczas ulepszania opisu przez AI: {e}")
            # Jeśli HuggingFace nie działa, spróbuj OpenAI jako fallback
            if self.api_type == 'huggingface':
                openai_key = os.getenv(
                    'OPENAI_API_KEY_NOVITA') or os.getenv('OPENAI_API_KEY')
                if openai_key:
                    logger.info("Próba użycia OpenAI jako fallback...")
                    try:
                        from openai import OpenAI
                        openai_client = OpenAI(api_key=openai_key)

                        model_name = "gpt-4o-mini"
                        if os.getenv('OPENAI_API_KEY_NOVITA') == openai_key:
                            model_name = "gpt-5.2"

                        response = openai_client.chat.completions.create(
                            model=model_name,
                            messages=[
                                {
                                    "role": "system",
                                    "content": """Jesteś ekspertem od copywritingu e-commerce specjalizującym się w modzie plażowej i strojach kąpielowych.

                            TWOJE ZADANIE:
                            Przekształć podany opis produktu w atrakcyjny, sprzedażowy tekst dla sklepu online.

                            WYTYCZNE:

                            1. STYL I TON:
                            - Przyjazny, inspirujący, lekko lifestyle'owy
                            - Zwracaj się do klienta w sposób naturalny
                            - Buduj emocjonalny związek z produktem

                            2. STRUKTURA OPISU:
                            - Chwytliwe otwarcie (1-2 zdania)
                            - Kluczowe cechy i korzyści (3-5 punktów)
                            - Szczegóły techniczne (materiał, krój, dopasowanie)
                            - Zachęta do zakupu

                            3. CO UWZGLĘDNIĆ:
                            - Rodzaj stroju (bikini, kostium, majtki, góra)
                            - Krój i fason
                            - Materiał i jego właściwości (szybkoschnący, elastyczny, UV)
                            - Dla kogo (typ sylwetki, styl życia)
                            - Okazje do noszenia (plaża, basen, wakacje)
                            - Unikalne cechy (fiszbiny, wyściółka, wiązania)

                            4. SEO:
                            - Naturalnie wpleć słowa kluczowe
                            - Unikaj keyword stuffing
                            - Długość: 100-200 słów

                            5. CZEGO UNIKAĆ:
                            - Przesadnych obietnic
                            - Sztampowych frazesów
                            - Zbyt technicznego języka
                            - Powtórzeń"""
                                },
                                {
                                    "role": "user",
                                    "content": f"Ulepsz ten opis produktu:\n\n{original_description}"
                                }
                            ],
                            temperature=0.7,
                            max_tokens=1000,
                            timeout=120
                        )

                        if response.choices[0].message.content:
                            enhanced = response.choices[0].message.content.strip(
                            )
                            logger.info("Użyto OpenAI jako fallback")
                            return enhanced
                    except Exception as fallback_error:
                        logger.error(
                            f"Błąd podczas fallback do OpenAI: {fallback_error}")

            import traceback
            traceback.print_exc()
            return original_description

    def enhance_product_name(self, original_name: str, use_structured: bool = True) -> str:
        """
        Ulepsza nazwę produktu przez AI używając struktury Pydantic.

        Args:
            original_name: Oryginalna nazwa produktu
            use_structured: Czy używać strukturyzowanej formy (Pydantic). Domyślnie True.

        Returns:
            Ulepszona nazwa produktu

        Raises:
            Exception: Jeśli nie udało się ulepszyć nazwy
        """
        if not original_name or not original_name.strip():
            raise ValueError("Oryginalna nazwa produktu jest pusta")

        if use_structured:
            try:
                return self._enhance_name_with_structure(original_name)
            except Exception as e:
                logger.error(
                    f"Błąd podczas strukturyzowanego ulepszania nazwy: {e}")
                # Nie używamy fallback - rzucamy wyjątek
                raise Exception(
                    f"Nie udało się ulepszyć nazwy produktu: {e}") from e
        else:
            try:
                return self._enhance_name_legacy(original_name)
            except Exception as e:
                logger.error(f"Błąd podczas ulepszania nazwy (legacy): {e}")
                raise Exception(
                    f"Nie udało się ulepszyć nazwy produktu: {e}") from e

    def _enhance_name_with_structure(self, original_name: str) -> str:
        """
        Ulepsza nazwę produktu używając strukturyzowanej formy (Pydantic).
        """
        import json

        # Sprawdź czy to figi
        is_figi = is_figi_product(original_name)
        
        if is_figi:
            base_type = "Figi kąpielowe"
            example_format = "Figi kąpielowe [model_name]"
            example_input = "Figi kąpielowe Model Ada M-803 (1) Lilia - Marko"
            example_output = '{"base_type": "Figi kąpielowe", "model_name": "Ada", "final_name": "Figi kąpielowe Ada"}'
        else:
            base_type = "Kostium kąpielowy"
            example_format = "Kostium kąpielowy [model_name]"
            example_input = "Kostium dwuczęściowy Kostium kąpielowy Model Ada M-803 (1) Lilia - Marko"
            example_output = '{"base_type": "Kostium kąpielowy", "model_name": "Ada", "final_name": "Kostium kąpielowy Ada"}'

        system_prompt = f"""Jesteś ekspertem od nazewnictwa produktów tekstylnych i modowych.

TWOJE ZADANIE:
Przekształć podaną nazwę produktu w profesjonalną nazwę dla sklepu online.

WYTYCZNE:

1. STRUKTURA (JSON) - WAŻNE: PRZESTRZEGAJ DOKŁADNIE LIMITÓW ZNAKÓW:
- base_type: "{base_type}" (nie zmieniaj tego!)
- model_name: Nazwa modelu (np. 'Ada', 'Lupo', 'Elegant') - WYMAGANE, 1-30 znaków
- final_name: Finalna nazwa w formacie "{example_format}" - 5-100 znaków, MAKSYMALNIE 100 znaków!

2. FORMAT FINALNEJ NAZWY:
- Format: "{example_format}" (np. "{example_format.replace('[model_name]', 'Ada')}")
- ZAWSZE zaczynaj od "{base_type}"
- NIE dodawaj koloru, kodu produktu, numerów w nawiasach, marki
- NIE dodawaj niczego poza "{base_type}" i nazwą modelu
- Używaj wielkich liter tylko na początku wyrazów (Title Case)

3. PRZYKŁADY:
- Input: "{example_input}"
- Output: {example_output}

4. CZEGO UNIKAĆ:
- Kodów modeli (M-803, M-123)
- Numerów w nawiasach ((1), (2))
- Nazwy marki na końcu (- Marko, - Lupo)
- Kolorów (Lilia, Czarny, itp.)
- Słowa "Model" w nazwie
- Powtórzeń

ODPOWIEDŹ MUSI BYĆ W FORMACIE JSON zgodnym z podanym schematem."""

        user_prompt = f"Przekształć tę nazwę produktu w strukturęzowany format JSON:\n\n{original_name}"

        try:
            if self.api_type == 'openai':
                model_name = "gpt-4o-mini"
                if os.getenv('OPENAI_API_KEY_NOVITA') == self.api_key:
                    model_name = "gpt-5.2"

                logger.info(
                    f"Używam API: {self.api_type}, model: {model_name}")
                print(
                    f"[DEBUG] Używam API: {self.api_type}, model: {model_name}")

                try:
                    response = self.client.chat.completions.create(
                        model=model_name,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        response_format={"type": "json_object"},
                        temperature=0.7,
                        # Zmienione z max_tokens na max_completion_tokens dla gpt-5.2
                        max_completion_tokens=300,
                        timeout=60
                    )
                except Exception as e:
                    error_msg = str(e)
                    logger.warning(
                        f"Błąd przy pierwszej próbie (response_format): {error_msg}")
                    print(
                        f"[DEBUG] Błąd przy pierwszej próbie (response_format): {error_msg}")
                    # Spróbuj bez response_format
                    response = self.client.chat.completions.create(
                        model=model_name,
                        messages=[
                            {"role": "system", "content": system_prompt +
                                "\n\nODPOWIEDŹ MUSI BYĆ TYLKO JSON, BEZ ŻADNYCH DODATKOWYCH KOMENTARZY."},
                            {"role": "user", "content": user_prompt}
                        ],
                        temperature=0.7,
                        max_tokens=300,
                        timeout=60
                    )

                logger.info(
                    f"Otrzymano odpowiedź z API, liczba choices: {len(response.choices)}")
                print(
                    f"[DEBUG] Otrzymano odpowiedź z API, liczba choices: {len(response.choices)}")

                if not response.choices:
                    raise ValueError("Brak choices w odpowiedzi z API")

                content = response.choices[0].message.content
                logger.info(
                    f"Content z API (długość): {len(content) if content else 0}")
                print(
                    f"[DEBUG] Content z API (długość): {len(content) if content else 0}")

                if not content:
                    logger.error(
                        "Pusta odpowiedź z API - response.choices[0].message.content jest None lub pusty")
                    print(
                        "[DEBUG] Pusta odpowiedź z API - response.choices[0].message.content jest None lub pusty")
                    logger.error(f"Pełna odpowiedź: {response}")
                    print(f"[DEBUG] Pełna odpowiedź: {response}")
                    raise ValueError("Pusta odpowiedź z API")

                content = content.strip()

                # Wyciągnij JSON z odpowiedzi
                if "```json" in content:
                    content = content.split("```json")[
                        1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()

                # Parsuj JSON
                data = json.loads(content)

                # Waliduj przez Pydantic
                name_structure = ProductNameStructure(**data)

                # Zwróć finalną nazwę
                final_name = name_structure.to_final_name()
                logger.info(
                    f"Nazwa ulepszona przez AI ze strukturą: {final_name}")
                return final_name

            elif self.api_type == 'huggingface':
                # Użyj OpenAI API z modelem gpt-5.2 zamiast HuggingFace
                openai_key = os.getenv('OPENAI_API_KEY') or os.getenv(
                    'OPENAI_API_KEY_NOVITA')
                if not openai_key:
                    raise ValueError(
                        "Brak klucza OpenAI API dla modelu gpt-5.2")

                from openai import OpenAI
                openai_client = OpenAI(api_key=openai_key)

                max_retries = 5
                retry_delay = 5

                logger.info(
                    f"Używam OpenAI API, model: gpt-5.2")
                print(
                    f"[INFO] Używam OpenAI API, model: gpt-5.2")

                for attempt in range(max_retries):
                    try:
                        response = openai_client.chat.completions.create(
                            model="gpt-5.2",
                            messages=[
                                {"role": "system", "content": system_prompt +
                                    "\n\nODPOWIEDŹ MUSI BYĆ TYLKO JSON, BEZ ŻADNYCH DODATKOWYCH KOMENTARZY."},
                                {"role": "user", "content": user_prompt}
                            ],
                            temperature=0.7,
                            # Zmienione z max_tokens na max_completion_tokens dla gpt-5.2
                            max_completion_tokens=300,
                            timeout=60
                        )

                        logger.info(
                            f"Otrzymano odpowiedź z API (próba {attempt + 1}), liczba choices: {len(response.choices)}")
                        print(
                            f"[DEBUG] Otrzymano odpowiedź z API (próba {attempt + 1}), liczba choices: {len(response.choices)}")

                        if not response.choices:
                            raise ValueError("Brak choices w odpowiedzi z API")

                        content = response.choices[0].message.content
                        logger.info(
                            f"Content z API (długość): {len(content) if content else 0}")
                        print(
                            f"[DEBUG] Content z API (długość): {len(content) if content else 0}")

                        if not content:
                            logger.error(
                                f"Pusta odpowiedź z API (próba {attempt + 1}) - response.choices[0].message.content jest None lub pusty")
                            print(
                                f"[DEBUG] Pusta odpowiedź z API (próba {attempt + 1}) - response.choices[0].message.content jest None lub pusty")
                            logger.error(f"Pełna odpowiedź: {response}")
                            print(f"[DEBUG] Pełna odpowiedź: {response}")
                            raise ValueError("Pusta odpowiedź z API")

                        content = content.strip()

                        # Wyciągnij JSON
                        if "```json" in content:
                            content = content.split("```json")[
                                1].split("```")[0].strip()
                        elif "```" in content:
                            content = content.split(
                                "```")[1].split("```")[0].strip()

                        # Parsuj JSON
                        data = json.loads(content)

                        # Waliduj przez Pydantic
                        name_structure = ProductNameStructure(**data)
                        final_name = name_structure.to_final_name()

                        logger.info(
                            f"Nazwa ulepszona przez AI ze strukturą: {final_name}")
                        return final_name

                    except json.JSONDecodeError as e:
                        logger.warning(
                            f"Błąd parsowania JSON (próba {attempt + 1}/{max_retries}): {e}")
                        if attempt < max_retries - 1:
                            time.sleep(retry_delay)
                            retry_delay = min(retry_delay * 2, 60)
                            continue
                        else:
                            raise
                    except Exception as e:
                        error_msg = str(e)
                        is_timeout = (
                            "504" in error_msg or "Gateway Timeout" in error_msg or
                            "timeout" in error_msg.lower() or "InternalServerError" in error_msg or
                            "Request timed out" in error_msg
                        )
                        if is_timeout and attempt < max_retries - 1:
                            logger.warning(
                                f"Timeout (próba {attempt + 1}/{max_retries}), czekam {retry_delay}s...")
                            time.sleep(retry_delay)
                            retry_delay = min(retry_delay * 2, 60)
                            continue
                        else:
                            raise

                raise ValueError(
                    "Nie udało się wygenerować strukturyzowanej nazwy")
            else:
                raise ValueError(f"Nieobsługiwany typ API: {self.api_type}")

        except Exception as e:
            logger.error(
                f"Błąd podczas generowania strukturyzowanej nazwy: {e}")
            # Fallback: lokalna heurystyka bez użycia zewnętrznego API
            try:
                logger.info(
                    "Próba użycia lokalnej heurystyki do wygenerowania nazwy produktu...")
                print(
                    "[DEBUG] Próba użycia lokalnej heurystyki do wygenerowania nazwy produktu...")
                final_name = self._enhance_name_with_local_heuristics(
                    original_name)
                logger.info(
                    f"Nazwa ulepszona lokalnie (heurystyka): {final_name}")
                print(
                    f"[DEBUG] Nazwa ulepszona lokalnie (heurystyka): {final_name}")
                return final_name
            except Exception as local_error:
                logger.error(
                    f"Błąd lokalnej heurystyki nazwy produktu: {local_error}")
                raise

    def _enhance_name_with_local_heuristics(self, original_name: str) -> str:
        """
        Lokalna heurystyka wyciągania nazwy modelu z oryginalnej nazwy produktu.

        Cel: Zwrócić nazwę w formacie 'Kostium kąpielowy [model_name]'
        bez użycia zewnętrznego API, gdy LLM zawiedzie.
        """
        import re

        if not original_name or not original_name.strip():
            raise ValueError("Oryginalna nazwa produktu jest pusta")

        name = original_name.strip()

        # 1. Spróbuj znaleźć nazwę modelu po słowie 'Model'
        model_name = ""
        match = re.search(
            r"\bModel\s+([A-Za-zĄĆĘŁŃÓŚŹŻąćęłńóśźż]+)", name, flags=re.IGNORECASE)
        if match:
            model_name = match.group(1).strip()

        # 2. Jeśli nie znaleziono po 'Model', użyj prostszej heurystyki:
        #    - usuń markę na końcu ('- Marko', '- Lupo', itp.)
        #    - usuń fragmenty w nawiasach
        #    - usuń kody typu 'M-803'
        #    - usuń słowa ogólne typu 'kostium', 'dwuczęściowy', 'kąpielowy', 'model'
        if not model_name:
            # Usuń część po myślniku (marka)
            base = re.split(r"\s*-\s*", name)[0]
            # Usuń fragmenty w nawiasach
            base = re.sub(r"\([^)]*\)", " ", base)
            # Usuń kody typu M-803
            base = re.sub(r"\b[A-Z]-\d+\b", " ", base)

            tokens = base.split()
            stop_words = {
                "kostium",
                "dwuczęściowy",
                "dwuczesciowy",
                "kąpielowy",
                "kapielowy",
                "model",
            }
            candidates = [
                t for t in tokens if t.lower() not in stop_words]

            # Wybierz pierwsze słowo zaczynające się wielką literą
            for t in candidates:
                if t and t[0].isalpha() and t[0].isupper():
                    model_name = t.strip()
                    break

        if not model_name:
            raise ValueError(
                f"Nie udało się wyodrębnić nazwy modelu z nazwy produktu: '{original_name}'")

        # Sprawdź czy to figi
        is_figi = is_figi_product(original_name)
        base_type = "Figi kąpielowe" if is_figi else "Kostium kąpielowy"
        
        # Zbuduj strukturę zgodnie z ProductNameStructure
        data = {
            "base_type": base_type,
            "model_name": model_name,
            "final_name": f"{base_type} {model_name}",
        }

        name_structure = ProductNameStructure(**data)
        return name_structure.to_final_name()

    def _enhance_name_legacy(self, original_name: str) -> str:
        """
        Legacy metoda ulepszania nazwy produktu (bez struktury Pydantic).
        """
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "Jesteś ekspertem od nazewnictwa produktów tekstylnych. "
                        "Ulepszaj nazwy produktów, czyniąc je bardziej atrakcyjnymi i profesjonalnymi, "
                        "ale zachowując oryginalne informacje. Odpowiadaj tylko ulepszoną nazwą, bez dodatkowych komentarzy."
                    },
                    {
                        "role": "user",
                        "content": f"Ulepsz tę nazwę produktu:\n\n{original_name}"
                    }
                ],
                temperature=0.7,
                max_tokens=200
            )

            if response.choices[0].message.content:
                enhanced = response.choices[0].message.content.strip()
            else:
                enhanced = original_name
            logger.info(f"Nazwa ulepszona przez AI (legacy): {enhanced}")
            return enhanced

        except Exception as e:
            logger.error(f"Błąd podczas ulepszania nazwy przez AI: {e}")
            raise Exception(
                f"Nie udało się ulepszyć nazwy produktu (legacy): {e}") from e

    def create_short_description(self, description: str, max_length: int = 250) -> str:
        """
        Tworzy krótki opis produktu na podstawie pełnego opisu.

        Args:
            description: Pełny opis produktu
            max_length: Maksymalna długość krótkiego opisu

        Returns:
            Krótki opis produktu
        """
        if not description or not description.strip():
            return ""

        try:
            if self.api_type == 'openai':
                model_name = "gpt-4o-mini"
                if os.getenv('OPENAI_API_KEY_NOVITA') == self.api_key:
                    model_name = "gpt-5.2"

                response = self.client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {
                            "role": "system",
                            "content": f"Jesteś ekspertem od tworzenia krótkich opisów produktów. "
                            f"Twórz zwięzłe, atrakcyjne opisy produktów tekstylnych o maksymalnej długości {max_length} znaków. "
                            f"Odpowiadaj tylko krótkim opisem, bez dodatkowych komentarzy."
                        },
                        {
                            "role": "user",
                            "content": f"Utwórz krótki opis produktu na podstawie tego opisu:\n\n{description}"
                        }
                    ],
                    temperature=0.7,
                    max_tokens=200
                )

                if response.choices[0].message.content:
                    short_desc = response.choices[0].message.content.strip()
                else:
                    short_desc = description[:max_length] if description else ""

            elif self.api_type == 'huggingface':
                # Użyj OpenAI API z modelem gpt-5.2 zamiast HuggingFace
                openai_key = os.getenv('OPENAI_API_KEY') or os.getenv(
                    'OPENAI_API_KEY_NOVITA')
                if not openai_key:
                    raise ValueError(
                        "Brak klucza OpenAI API dla modelu gpt-5.2")

                from openai import OpenAI
                openai_client = OpenAI(api_key=openai_key)

                # Użyj tego samego modelu co dla długiego opisu z retry logic
                max_retries = 5
                retry_delay = 5
                short_desc = None

                # Model do użycia
                model = "gpt-5.2"

                success = False
                for attempt in range(max_retries):
                    if success:
                        break

                    try:
                        response = openai_client.chat.completions.create(
                            model=model,
                            messages=[
                                {
                                    "role": "system",
                                    "content": f"Jesteś ekspertem od tworzenia krótkich opisów produktów. "
                                    f"Twórz zwięzłe, atrakcyjne opisy produktów tekstylnych o maksymalnej długości {max_length} znaków. "
                                    f"Odpowiadaj tylko krótkim opisem, bez dodatkowych komentarzy."
                                },
                                {
                                    "role": "user",
                                    "content": f"Utwórz krótki opis produktu na podstawie tego opisu:\n\n{description}"
                                }
                            ],
                            temperature=0.7,
                            # Zmienione z max_tokens na max_completion_tokens dla gpt-5.2
                            max_completion_tokens=200,
                            timeout=30  # Zmniejszone z 120 do 30 sekund
                        )
                        logger.info(
                            "Otrzymano odpowiedź dla krótkiego opisu z OpenAI API (model: gpt-5.2)")
                        print(
                            "[INFO] Otrzymano odpowiedź dla krótkiego opisu z OpenAI API (model: gpt-5.2)")

                        if response.choices[0].message.content:
                            short_desc = response.choices[0].message.content.strip(
                            )
                        else:
                            short_desc = description[:max_length] if description else ""

                        success = True
                        break

                    except Exception as e:
                        error_msg = str(e)
                        is_timeout = (
                            "504" in error_msg or "Gateway Timeout" in error_msg or
                            "timeout" in error_msg.lower() or "InternalServerError" in error_msg or
                            "Request timed out" in error_msg
                        )

                        if is_timeout:
                            if attempt < max_retries - 1:
                                time.sleep(retry_delay)
                                # Max 10s zamiast 60s
                                retry_delay = min(retry_delay * 2, 10)
                                continue
                            else:
                                short_desc = description[:max_length] if description else ""
                                success = True
                                break
                        else:
                            # Inny błąd - zwróć oryginalny opis
                            short_desc = description[:max_length] if description else ""
                            success = True
                            break

                # Jeśli HuggingFace nie zadziałało, spróbuj OpenAI jako fallback
                if not short_desc or short_desc == description[:max_length] if description else "":
                    openai_key = os.getenv(
                        'OPENAI_API_KEY_NOVITA') or os.getenv('OPENAI_API_KEY')
                    if openai_key and openai_key != self.api_key:
                        logger.info(
                            "Próba użycia OpenAI jako fallback dla krótkiego opisu...")
                        print(
                            "[DEBUG] Próba użycia OpenAI jako fallback dla krótkiego opisu...")
                        try:
                            from openai import OpenAI
                            openai_client = OpenAI(api_key=openai_key)

                            model_name = "gpt-4o-mini"
                            if os.getenv('OPENAI_API_KEY_NOVITA') == openai_key:
                                model_name = "gpt-5.2"

                            response = openai_client.chat.completions.create(
                                model=model_name,
                                messages=[
                                    {
                                        "role": "system",
                                        "content": f"Jesteś ekspertem od tworzenia krótkich opisów produktów. "
                                        f"Twórz zwięzłe, atrakcyjne opisy produktów tekstylnych o maksymalnej długości {max_length} znaków. "
                                        f"Odpowiadaj tylko krótkim opisem, bez dodatkowych komentarzy."
                                    },
                                    {
                                        "role": "user",
                                        "content": f"Utwórz krótki opis produktu na podstawie tego opisu:\n\n{description}"
                                    }
                                ],
                                temperature=0.7,
                                max_tokens=200,
                                timeout=30  # Zmniejszone z 120 do 30 sekund
                            )
                            logger.info(
                                "Otrzymano odpowiedź dla krótkiego opisu")
                            print(
                                "[DEBUG] Otrzymano odpowiedź dla krótkiego opisu")

                            if response.choices[0].message.content:
                                short_desc = response.choices[0].message.content.strip(
                                )
                                logger.info(
                                    "Użyto OpenAI jako fallback dla krótkiego opisu")
                                print(
                                    "[DEBUG] Użyto OpenAI jako fallback dla krótkiego opisu")
                        except Exception as fallback_error:
                            logger.error(
                                f"Błąd podczas fallback do OpenAI: {fallback_error}")
                            print(
                                f"[DEBUG] Błąd podczas fallback do OpenAI: {fallback_error}")

                if not short_desc:
                    short_desc = description[:max_length] if description else ""
            else:
                # Fallback: użyj pierwszych max_length znaków
                short_desc = description[:max_length] if description else ""

            # Obetnij do max_length jeśli za długi
            if len(short_desc) > max_length:
                short_desc = short_desc[:max_length].rsplit(' ', 1)[0] + '...'

            logger.info(
                f"Krótki opis utworzony przez AI (długość: {len(short_desc)})")
            return short_desc

        except Exception as e:
            logger.error(
                f"Błąd podczas tworzenia krótkiego opisu przez AI: {e}")
            # Jeśli HuggingFace nie działa, spróbuj OpenAI jako fallback
            if self.api_type == 'huggingface':
                openai_key = os.getenv(
                    'OPENAI_API_KEY_NOVITA') or os.getenv('OPENAI_API_KEY')
                if openai_key:
                    logger.info(
                        "Próba użycia OpenAI jako fallback dla krótkiego opisu...")
                    try:
                        from openai import OpenAI
                        openai_client = OpenAI(api_key=openai_key)

                        model_name = "gpt-4o-mini"
                        if os.getenv('OPENAI_API_KEY_NOVITA') == openai_key:
                            model_name = "gpt-5.2"

                        response = openai_client.chat.completions.create(
                            model=model_name,
                            messages=[
                                {
                                    "role": "system",
                                    "content": f"Jesteś ekspertem od tworzenia krótkich opisów produktów. "
                                    f"Twórz zwięzłe, atrakcyjne opisy produktów tekstylnych o maksymalnej długości {max_length} znaków. "
                                    f"Odpowiadaj tylko krótkim opisem, bez dodatkowych komentarzy."
                                },
                                {
                                    "role": "user",
                                    "content": f"Utwórz krótki opis produktu na podstawie tego opisu:\n\n{description}"
                                }
                            ],
                            temperature=0.7,
                            max_tokens=200,
                            timeout=120
                        )

                        if response.choices[0].message.content:
                            short_desc = response.choices[0].message.content.strip(
                            )
                            logger.info(
                                "Użyto OpenAI jako fallback dla krótkiego opisu")
                            return short_desc
                    except Exception as fallback_error:
                        logger.error(
                            f"Błąd podczas fallback do OpenAI: {fallback_error}")
            # Fallback: użyj pierwszych max_length znaków
            return description[:max_length] if description else ""

    def extract_attributes_from_description(self, description: str, available_attributes: List[Dict], similarity_threshold: float = 0.05, min_attributes: int = 3, max_attributes: int = 15) -> List[int]:
        """
        Wyciąga atrybuty z opisu produktu używając LLM (OpenAI API) jako głównej metody,
        z fallbackiem do TF-IDF i cosine similarity.

        Args:
            description: Opis produktu
            available_attributes: Lista dostępnych atrybutów z bazy MPD [{'id': int, 'name': str}, ...]
            similarity_threshold: Próg podobieństwa (0.0-1.0), domyślnie 0.05
            min_attributes: Minimalna liczba atrybutów do zwrócenia (jeśli są dostępne), domyślnie 3
            max_attributes: Maksymalna liczba atrybutów do zwrócenia, domyślnie 15

        Returns:
            Lista ID atrybutów do zaznaczenia (posortowane według podobieństwa)
        """
        if not description or not description.strip():
            return []

        if not available_attributes:
            return []

        # Najpierw spróbuj użyć LLM do wyodrębnienia atrybutów
        try:
            logger.info(
                "Próba wyodrębnienia atrybutów używając LLM (OpenAI API)...")
            print("[DEBUG] Próba wyodrębnienia atrybutów używając LLM (OpenAI API)...")
            llm_attributes = self._extract_attributes_with_llm(
                description, available_attributes)
            if llm_attributes:
                logger.info(f"LLM wyodrębnił {len(llm_attributes)} atrybutów")
                print(
                    f"[DEBUG] LLM wyodrębnił {len(llm_attributes)} atrybutów")
                return llm_attributes
        except Exception as e:
            logger.warning(
                f"Błąd podczas wyodrębniania atrybutów przez LLM: {e}, używam fallback do TF-IDF")
            print(
                f"[DEBUG] Błąd podczas wyodrębniania atrybutów przez LLM: {e}, używam fallback do TF-IDF")

        # Fallback do TF-IDF i cosine similarity
        try:
            # Spróbuj użyć sklearn jeśli dostępny
            try:
                from sklearn.feature_extraction.text import TfidfVectorizer
                from sklearn.metrics.pairwise import cosine_similarity

                logger.info(
                    "Wyciąganie atrybutów używając TF-IDF i cosine similarity...")
                print(
                    "[DEBUG] Wyciąganie atrybutów używając TF-IDF i cosine similarity...")

                # Debug: wyświetl wszystkie dostępne atrybuty
                logger.info(
                    f"Dostępne atrybuty ({len(available_attributes)}):")
                print(
                    f"[DEBUG] Dostępne atrybuty ({len(available_attributes)}):")
                for attr in available_attributes:
                    logger.info(f"  - {attr['name']} (ID: {attr['id']})")
                    print(f"[DEBUG]   - {attr['name']} (ID: {attr['id']})")

                # Przygotuj teksty do porównania
                description_text = description.lower().strip()
                attribute_texts = [attr['name'].lower().strip()
                                   for attr in available_attributes]

                # Użyj TF-IDF do wektoryzacji tekstów
                vectorizer = TfidfVectorizer(
                    analyzer='word', ngram_range=(1, 2), min_df=1, stop_words=None)

                # Wektoryzuj opis i nazwy atrybutów
                all_texts = [description_text] + attribute_texts
                tfidf_matrix = vectorizer.fit_transform(all_texts)

                # Oblicz cosine similarity między opisem a każdym atrybutem
                description_vector = tfidf_matrix[0:1]
                attributes_vectors = tfidf_matrix[1:]

                similarities = cosine_similarity(
                    description_vector, attributes_vectors)[0]

                # Sprawdź czy nazwa atrybutu występuje w opisie (proste dopasowanie tekstowe)
                # Jeśli tak, zwiększ podobieństwo dla tego atrybutu
                description_lower = description_text.lower()
                enhanced_similarities = []
                for idx, similarity in enumerate(similarities):
                    attr_name = available_attributes[idx]['name'].lower()
                    # Sprawdź czy nazwa atrybutu występuje w opisie (cała fraza lub wszystkie słowa)
                    attr_words = attr_name.split()
                    found_in_description = False

                    # Sprawdź czy cała fraza występuje
                    if attr_name in description_lower:
                        found_in_description = True
                    # Sprawdź czy wszystkie słowa z nazwy atrybutu występują w opisie
                    elif len(attr_words) > 1 and all(word in description_lower for word in attr_words if len(word) > 2):
                        found_in_description = True

                    if found_in_description:
                        # Jeśli nazwa atrybutu występuje w opisie, zwiększ podobieństwo do 0.5
                        enhanced_similarity = max(float(similarity), 0.5)
                        logger.info(
                            f"Znaleziono '{available_attributes[idx]['name']}' w opisie - zwiększam podobieństwo z {similarity:.3f} do {enhanced_similarity:.3f}")
                        print(
                            f"[DEBUG] Znaleziono '{available_attributes[idx]['name']}' w opisie - zwiększam podobieństwo z {similarity:.3f} do {enhanced_similarity:.3f}")
                    else:
                        enhanced_similarity = float(similarity)
                    enhanced_similarities.append(
                        (idx, enhanced_similarity, available_attributes[idx]['name']))

                # Debug: wyświetl top 15 najwyższych podobieństw (po wzmocnieniu)
                enhanced_similarities.sort(key=lambda x: x[1], reverse=True)
                logger.info(f"Top 15 podobieństw atrybutów (po wzmocnieniu):")
                print(f"[DEBUG] Top 15 podobieństw atrybutów (po wzmocnieniu):")
                for idx, sim, name in enhanced_similarities[:15]:
                    logger.info(f"  - {name}: {sim:.3f}")
                    print(f"[DEBUG]   - {name}: {sim:.3f}")

                # Zawsze weź top N atrybutów z najwyższym podobieństwem (ale tylko z podobieństwem > 0.01)
                # To zapewnia, że nie pominiemy ważnych atrybutów jak "niski stan"
                top_attributes = [
                    score for score in enhanced_similarities if score[1] > 0.01][:max_attributes]

                matched_attributes = []
                for idx, sim, name in top_attributes:
                    matched_attributes.append({
                        'id': available_attributes[idx]['id'],
                        'name': name,
                        'similarity': sim
                    })

                # Posortuj według podobieństwa (malejąco)
                matched_attributes.sort(
                    key=lambda x: x['similarity'], reverse=True)

                # Usuń wykluczające się atrybuty (zostaw tylko ten z wyższym podobieństwem)
                matched_attributes = self._remove_conflicting_attributes(
                    matched_attributes)

                min_similarity = min(
                    [a['similarity'] for a in matched_attributes]) if matched_attributes else 0.0
                logger.info(
                    f"Wybrano top {len(matched_attributes)} atrybutów z najwyższym podobieństwem (min: {min_similarity:.3f})")
                print(
                    f"[DEBUG] Wybrano top {len(matched_attributes)} atrybutów z najwyższym podobieństwem (min: {min_similarity:.3f})")

                # Zwróć tylko ID atrybutów
                attribute_ids = [attr['id'] for attr in matched_attributes]

                if attribute_ids:
                    logger.info(
                        f"Znaleziono {len(attribute_ids)} atrybutów z podobieństwem >= {similarity_threshold}")
                    for attr in matched_attributes:
                        logger.info(
                            f"  - {attr['name']} (ID: {attr['id']}, similarity: {attr['similarity']:.3f})")
                        print(
                            f"[DEBUG]   - {attr['name']} (ID: {attr['id']}, similarity: {attr['similarity']:.3f})")
                else:
                    logger.info(
                        f"Nie znaleziono atrybutów z podobieństwem >= {similarity_threshold}")
                    print(
                        f"[DEBUG] Nie znaleziono atrybutów z podobieństwem >= {similarity_threshold}")

                return attribute_ids

            except ImportError:
                # Fallback: użyj RapidFuzz dla podobieństwa tekstowego
                logger.info(
                    "Brak sklearn - używam RapidFuzz do podobieństwa tekstowego")
                print(
                    "[DEBUG] Brak sklearn - używam RapidFuzz do podobieństwa tekstowego")
                return self._extract_attributes_with_rapidfuzz(description, available_attributes, similarity_threshold, min_attributes, max_attributes)

        except Exception as e:
            logger.error(f"Błąd podczas wyciągania atrybutów z opisu: {e}")
            print(f"[DEBUG] Błąd podczas wyciągania atrybutów: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _extract_attributes_with_rapidfuzz(self, description: str, available_attributes: List[Dict], similarity_threshold: float = 0.05, min_attributes: int = 3, max_attributes: int = 15) -> List[int]:
        """
        Wyciąga atrybuty używając RapidFuzz do podobieństwa tekstowego (fallback gdy brak sklearn).
        """
        try:
            from rapidfuzz import fuzz, process

            logger.info("Wyciąganie atrybutów używając RapidFuzz...")
            print("[DEBUG] Wyciąganie atrybutów używając RapidFuzz...")

            description_lower = description.lower()
            attribute_names = {attr['id']: attr['name']
                               for attr in available_attributes}

            # Oblicz podobieństwo dla wszystkich atrybutów i wzmocnij te, które występują w opisie
            all_attributes = []
            for attr_id, attr_name in attribute_names.items():
                # Oblicz podobieństwo używając ratio (cosine-like similarity)
                similarity = fuzz.ratio(
                    description_lower, attr_name.lower()) / 100.0

                # Sprawdź czy nazwa atrybutu występuje w opisie (cała fraza lub wszystkie słowa)
                attr_name_lower = attr_name.lower()
                attr_words = attr_name_lower.split()
                found_in_description = False

                # Sprawdź czy cała fraza występuje
                if attr_name_lower in description_lower:
                    found_in_description = True
                # Sprawdź czy wszystkie słowa z nazwy atrybutu występują w opisie
                elif len(attr_words) > 1 and all(word in description_lower for word in attr_words if len(word) > 2):
                    found_in_description = True

                if found_in_description:
                    # Jeśli nazwa atrybutu występuje w opisie, zwiększ podobieństwo do 0.5
                    enhanced_similarity = max(similarity, 0.5)
                    logger.info(
                        f"Znaleziono '{attr_name}' w opisie - zwiększam podobieństwo z {similarity:.3f} do {enhanced_similarity:.3f}")
                    print(
                        f"[DEBUG] Znaleziono '{attr_name}' w opisie - zwiększam podobieństwo z {similarity:.3f} do {enhanced_similarity:.3f}")
                else:
                    enhanced_similarity = similarity

                all_attributes.append({
                    'id': attr_id,
                    'name': attr_name,
                    'similarity': enhanced_similarity
                })

            # Posortuj według podobieństwa (malejąco)
            all_attributes.sort(key=lambda x: x['similarity'], reverse=True)

            # Weź top N z podobieństwem > 0.01
            matched_attributes = [
                attr for attr in all_attributes if attr['similarity'] > 0.01][:max_attributes]

            # Usuń wykluczające się atrybuty (zostaw tylko ten z wyższym podobieństwem)
            matched_attributes = self._remove_conflicting_attributes(
                matched_attributes)

            min_similarity = min(
                [a['similarity'] for a in matched_attributes]) if matched_attributes else 0.0
            logger.info(
                f"Wybrano top {len(matched_attributes)} atrybutów z najwyższym podobieństwem (min: {min_similarity:.3f})")
            print(
                f"[DEBUG] Wybrano top {len(matched_attributes)} atrybutów z najwyższym podobieństwem (min: {min_similarity:.3f})")

            # Zwróć tylko ID atrybutów
            attribute_ids = [attr['id'] for attr in matched_attributes]

            if attribute_ids:
                logger.info(
                    f"Znaleziono {len(attribute_ids)} atrybutów z podobieństwem >= {similarity_threshold}")
                for attr in matched_attributes:
                    logger.info(
                        f"  - {attr['name']} (ID: {attr['id']}, similarity: {attr['similarity']:.3f})")
                    print(
                        f"[DEBUG]   - {attr['name']} (ID: {attr['id']}, similarity: {attr['similarity']:.3f})")
            else:
                logger.info(
                    f"Nie znaleziono atrybutów z podobieństwem >= {similarity_threshold}")
                print(
                    f"[DEBUG] Nie znaleziono atrybutów z podobieństwem >= {similarity_threshold}")

            return attribute_ids

        except ImportError:
            # Ostateczny fallback: proste dopasowanie tekstowe
            logger.warning(
                "Brak RapidFuzz - używam prostego dopasowania tekstowego")
            print("[DEBUG] Brak RapidFuzz - używam prostego dopasowania tekstowego")
            return self._extract_attributes_simple_match(description, available_attributes, similarity_threshold, min_attributes, max_attributes)

    def _extract_attributes_with_llm(self, description: str, available_attributes: List[Dict]) -> List[int]:
        """
        Wyodrębnia atrybuty z opisu produktu używając LLM (OpenAI API).

        Args:
            description: Opis produktu
            available_attributes: Lista dostępnych atrybutów z bazy MPD [{'id': int, 'name': str}, ...]

        Returns:
            Lista ID atrybutów do zaznaczenia
        """
        import json
        import os

        # Sprawdź czy mamy dostęp do OpenAI API
        # Dla atrybutów preferujemy zwykły OPENAI_API_KEY,
        # HF_TOKEN / NOVITA używamy osobno np. do opisów.
        openai_key = os.getenv('OPENAI_API_KEY') or os.getenv(
            'OPENAI_API_KEY_NOVITA')
        if not openai_key:
            raise ValueError("Brak klucza OpenAI API")

        from openai import OpenAI
        client = OpenAI(api_key=openai_key)

        # Przygotuj listę dostępnych atrybutów dla LLM
        available_attrs_names = [attr['name'] for attr in available_attributes]
        available_attrs_text = ", ".join(available_attrs_names)

        system_prompt = (
            "Jesteś ekspertem w ekstrakcji cech produktu tekstylnego. "
            "Wyodrębnij atrybuty kostiumu kąpielowego z poniższego opisu, "
            "zwracając wynik wyłącznie w formacie JSON. "
            "WAŻNE: Wybierz TYLKO atrybuty, które są BEZPOŚREDNIO i WYRAŹNIE wspomniane w opisie produktu. "
            "NIE wybieraj atrybutów na podstawie domysłów, interpretacji lub podobieństwa słów. "
            "NIE wybieraj atrybutów, które mogą być tylko implikowane - muszą być wyraźnie wspomniane. "
            "NIE myl PRZECIWNYCH atrybutów - \"wysoki stan\" to NIE \"niski stan\"!"
        )

        user_prompt = (
            f"Opis produktu: {description}\n\n"
            f"Dostępne atrybuty do wyboru: {available_attrs_text}\n\n"
            "Wyodrębnij listę kluczowych atrybutów, które są BEZPOŚREDNIO i WYRAŹNIE wspomniane w opisie produktu. "
            "Zwróć wynik w formacie JSON: {{\"attributes\": [\"nazwa atrybutu 1\", \"nazwa atrybutu 2\", ...]}}. "
            "Używaj dokładnie takich nazw atrybutów, jakie są w liście dostępnych atrybutów. "
            "\n"
            "KRYTYCZNE ZASADY - PRZECZYTAJ UWAŻNIE:\n"
            "1. \"WYSOKI STAN\" i \"NISKI STAN\" to PRZECIWNE atrybuty:\n"
            "   - Jeśli w opisie jest \"wysoki stan\" lub \"wysokie figi\" - NIE wybieraj \"niski stan\"!\n"
            "   - Jeśli w opisie jest \"niski stan\" lub \"niskie figi\" - wybierz \"niski stan\"\n"
            "   - Jeśli w opisie jest \"wysoki stan\" - NIE wybieraj \"niski stan\" (to są PRZECIWNE rzeczy!)\n"
            "\n"
            "2. Inne przykłady:\n"
            "   - Jeśli w opisie jest \"krój midi\" - NIE wybieraj \"niski stan\" (to są różne rzeczy)\n"
            "   - Jeśli w opisie jest \"gładkie\" - wybierz \"gładkie\"\n"
            "   - Jeśli w opisie jest \"bezszwowe\" - wybierz \"bezszwowe\"\n"
            "\n"
            "3. OGÓLNA ZASADA:\n"
            "   - Wybierz TYLKO atrybuty, które są WYRAŹNIE i BEZPOŚREDNIO wspomniane w tekście\n"
            "   - NIE wybieraj atrybutów na podstawie domysłów lub podobieństwa\n"
            "   - NIE myl przeciwnych atrybutów (wysoki ≠ niski)\n"
            "\n"
            "Wybierz tylko te atrybuty, które rzeczywiście są WYRAŹNIE wspomniane w opisie produktu."
        )

        # Określ model OpenAI
        model_name = "gpt-4o-mini"
        if os.getenv('OPENAI_API_KEY_NOVITA') == openai_key:
            model_name = "gpt-4o-mini"  # Można zmienić na inny model

        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.3,  # Niższa temperatura dla bardziej precyzyjnych wyników
                max_tokens=500
            )

            content = response.choices[0].message.content
            if not content:
                raise ValueError("Pusta odpowiedź z OpenAI API")

            # Upewnij się, że content jest prawidłowo zdekodowany jako UTF-8
            if isinstance(content, bytes):
                content = content.decode('utf-8')
            elif not isinstance(content, str):
                content = str(content)

            # Normalizuj Unicode przed parsowaniem (NFKC - kompatybilność + kompozycja)
            # To pomaga naprawić problemy z kodowaniem polskich znaków
            import unicodedata
            content_normalized = unicodedata.normalize('NFKC', content)

            # Parsuj JSON (Python 3 zawsze używa UTF-8)
            try:
                result = json.loads(content_normalized)
            except json.JSONDecodeError as e:
                # Jeśli parsowanie się nie powiodło, spróbuj bez normalizacji
                logger.warning(
                    f"Błąd parsowania JSON po normalizacji, próba bez normalizacji: {e}")
                result = json.loads(content)

            if 'attributes' not in result or not isinstance(result['attributes'], list):
                raise ValueError(
                    "Nieprawidłowy format odpowiedzi z OpenAI API")

            # Normalizuj i wyczyść nazwy atrybutów z problemami kodowania
            extracted_attr_names = []
            for attr in result['attributes']:
                if isinstance(attr, bytes):
                    attr = attr.decode('utf-8')
                attr_str = str(attr).strip()
                # Normalizuj Unicode (NFKC - kompatybilność + kompozycja)
                # To naprawia problemy z kodowaniem polskich znaków (np. "wiązane" -> "wiązane")
                attr_normalized = unicodedata.normalize('NFKC', attr_str)
                extracted_attr_names.append(attr_normalized)

            logger.info(
                f"LLM wyodrębnił następujące atrybuty: {extracted_attr_names}")
            print(
                f"[DEBUG] LLM wyodrębnił następujące atrybuty: {extracted_attr_names}")

            # Dopasuj wyodrębnione nazwy do dostępnych atrybutów
            matched_attr_ids = []
            attr_name_to_id = {attr['name'].lower(): attr['id']
                               for attr in available_attributes}

            # Przygotuj listę (id, name_lower) dla fuzzy matchingu
            available_for_fuzzy = [(attr['id'], attr['name'].lower())
                                   for attr in available_attributes]

            try:
                from rapidfuzz import fuzz  # type: ignore
                use_fuzzy = True
            except ImportError:
                use_fuzzy = False

            for extracted_name in extracted_attr_names:
                extracted_lower = extracted_name.lower()

                # 0) Reguły specjalne dla znanych synonimów
                # "wiązane po/na bokach" traktujemy jak atrybut "regulowane"
                if "wiąz" in extracted_lower and "bok" in extracted_lower and "regulowane" in attr_name_to_id:
                    reg_id = attr_name_to_id["regulowane"]
                    matched_attr_ids.append(reg_id)
                    logger.info(
                        f"Dopasowano regułą specjalną: '{extracted_name}' -> 'regulowane' (ID: {reg_id})")
                    print(
                        f"[DEBUG] Dopasowano regułą specjalną: '{extracted_name}' -> 'regulowane' (ID: {reg_id})")
                    continue

                # 1) Dokładne dopasowanie
                if extracted_lower in attr_name_to_id:
                    attr_id = attr_name_to_id[extracted_lower]
                    matched_attr_ids.append(attr_id)
                    logger.info(
                        f"Dopasowano: '{extracted_name}' -> ID: {attr_id}")
                    print(
                        f"[DEBUG] Dopasowano: '{extracted_name}' -> ID: {attr_id}")
                    continue

                # 2) Proste dopasowanie częściowe (contains)
                partial_match_id = None
                for attr_name, attr_id in attr_name_to_id.items():
                    if extracted_lower in attr_name or attr_name in extracted_lower:
                        partial_match_id = attr_id
                        logger.info(
                            f"Dopasowano częściowo (substring): '{extracted_name}' -> '{attr_name}' (ID: {attr_id})")
                        print(
                            f"[DEBUG] Dopasowano częściowo (substring): '{extracted_name}' -> '{attr_name}' (ID: {attr_id})")
                        break

                if partial_match_id is not None:
                    matched_attr_ids.append(partial_match_id)
                    continue

                # 3) Fuzzy matching dla literówek (np. 'uszywiane miseczki' -> 'usztywniane miseczki')
                if use_fuzzy:
                    from rapidfuzz import fuzz  # type: ignore
                    best_id = None
                    best_score = 0.0
                    for attr_id, attr_name_lower in available_for_fuzzy:
                        score = fuzz.ratio(extracted_lower,
                                           attr_name_lower) / 100.0
                        if score > best_score:
                            best_score = score
                            best_id = attr_id

                    # Ustal próg dla literówek – np. >= 0.75
                    if best_id is not None and best_score >= 0.75:
                        matched_attr_ids.append(best_id)
                        best_name = next(
                            a['name'] for a in available_attributes if a['id'] == best_id)
                        logger.info(
                            f"Dopasowano fuzzy: '{extracted_name}' -> '{best_name}' (ID: {best_id}, score: {best_score:.3f})")
                        print(
                            f"[DEBUG] Dopasowano fuzzy: '{extracted_name}' -> '{best_name}' (ID: {best_id}, score: {best_score:.3f})")
                        continue

                # 4) Nic nie znaleziono
                logger.warning(
                    f"Nie znaleziono dopasowania dla atrybutu: '{extracted_name}'")
                # Użyj bezpiecznego wypisywania dla polskich znaków
                try:
                    print(
                        f"[DEBUG] Nie znaleziono dopasowania dla atrybutu: '{extracted_name}'")
                except UnicodeEncodeError:
                    # Fallback: użyj logger zamiast print jeśli wystąpi błąd kodowania
                    logger.debug(
                        f"[DEBUG] Nie znaleziono dopasowania dla atrybutu: '{extracted_name}'")

            # Usuń duplikaty zachowując kolejność
            seen = set()
            unique_attr_ids = []
            for attr_id in matched_attr_ids:
                if attr_id not in seen:
                    seen.add(attr_id)
                    unique_attr_ids.append(attr_id)

            # Usuń wykluczające się atrybuty
            matched_attributes = [{'id': attr_id, 'name': next(attr['name'] for attr in available_attributes if attr['id'] == attr_id), 'similarity': 1.0}
                                  for attr_id in unique_attr_ids]
            matched_attributes = self._remove_conflicting_attributes(
                matched_attributes)

            final_attr_ids = [attr['id'] for attr in matched_attributes]

            logger.info(
                f"Finalna lista atrybutów po usunięciu konfliktów: {len(final_attr_ids)} atrybutów")
            print(
                f"[DEBUG] Finalna lista atrybutów po usunięciu konfliktów: {len(final_attr_ids)} atrybutów")

            return final_attr_ids

        except Exception as e:
            logger.error(
                f"Błąd podczas wyodrębniania atrybutów przez LLM: {e}")
            print(
                f"[DEBUG] Błąd podczas wyodrębniania atrybutów przez LLM: {e}")
            import traceback
            traceback.print_exc()
            raise

    def _remove_conflicting_attributes(self, matched_attributes: List[Dict]) -> List[Dict]:
        """
        Usuwa wykluczające się atrybuty, pozostawiając tylko ten z wyższym podobieństwem.

        Args:
            matched_attributes: Lista atrybutów z podobieństwem [{'id': int, 'name': str, 'similarity': float}, ...]

        Returns:
            Lista atrybutów bez wykluczających się
        """
        # Grupy wykluczających się atrybutów (ID atrybutów)
        conflicting_groups = [
            # Ramiączka - odpinane vs nieodpinane
            [12, 23],  # odpinane ramiączka vs nieodpinane ramiączka
            # Fiszbiny - na fiszbinach vs bez fiszbin
            [9, 2],  # na fiszbinach vs biustonosz bez fiszbin
            # Typy miseczek (wykluczające się)
            [7, 27, 22, 30],  # gładkie, miękkie, wyściełane, usztywniane miseczki
            # Stan - niski vs wyższy
            [28, 25],  # niski stan vs wyższy stan
        ]

        # Utwórz mapę ID -> atrybut dla szybkiego wyszukiwania
        attr_map = {attr['id']: attr for attr in matched_attributes}

        # Dla każdej grupy wykluczających się atrybutów, zostaw tylko ten z najwyższym podobieństwem
        for group in conflicting_groups:
            # Znajdź atrybuty z tej grupy, które są w matched_attributes
            group_attrs = [attr_map[attr_id]
                           for attr_id in group if attr_id in attr_map]

            if len(group_attrs) > 1:
                # Posortuj według podobieństwa (malejąco)
                group_attrs.sort(key=lambda x: x['similarity'], reverse=True)

                # Zostaw tylko pierwszy (z najwyższym podobieństwem)
                best_attr = group_attrs[0]
                removed_attrs = group_attrs[1:]

                logger.info(
                    f"Usuwam wykluczające się atrybuty z grupy {group}:")
                print(
                    f"[DEBUG] Usuwam wykluczające się atrybuty z grupy {group}:")
                logger.info(
                    f"  Zostawiam: {best_attr['name']} (ID: {best_attr['id']}, similarity: {best_attr['similarity']:.3f})")
                print(
                    f"[DEBUG]   Zostawiam: {best_attr['name']} (ID: {best_attr['id']}, similarity: {best_attr['similarity']:.3f})")

                for removed_attr in removed_attrs:
                    logger.info(
                        f"  Usuwam: {removed_attr['name']} (ID: {removed_attr['id']}, similarity: {removed_attr['similarity']:.3f})")
                    print(
                        f"[DEBUG]   Usuwam: {removed_attr['name']} (ID: {removed_attr['id']}, similarity: {removed_attr['similarity']:.3f})")
                    # Usuń z matched_attributes
                    matched_attributes = [
                        attr for attr in matched_attributes if attr['id'] != removed_attr['id']]

        return matched_attributes

    def _extract_attributes_simple_match(self, description: str, available_attributes: List[Dict], similarity_threshold: float = 0.05, min_attributes: int = 3, max_attributes: int = 15) -> List[int]:
        """
        Proste dopasowanie tekstowe jako ostateczny fallback.
        """
        description_lower = description.lower()
        matched_ids = []

        for attr in available_attributes:
            attr_name_lower = attr['name'].lower()
            # Sprawdź czy nazwa atrybutu występuje w opisie
            if attr_name_lower in description_lower:
                matched_ids.append(attr['id'])

        if matched_ids:
            logger.info(
                f"Znaleziono {len(matched_ids)} atrybutów przez proste dopasowanie: {matched_ids}")
            print(
                f"[DEBUG] Znaleziono {len(matched_ids)} atrybutów przez proste dopasowanie: {matched_ids}")

        return matched_ids

    def process_product_data(self, product_data: Dict) -> Dict:
        """
        Przetwarza wszystkie dane produktu przez AI.

        Args:
            product_data: Słownik z danymi produktu (name, description, etc.)

        Returns:
            Słownik z przetworzonymi danymi produktu
        """
        logger.info(
            f"Przetwarzanie danych produktu przez AI: {product_data.get('name', 'Unknown')}")

        processed_data = product_data.copy()

        # Ulepsz nazwę
        if 'name' in processed_data and processed_data['name']:
            processed_data['name'] = self.enhance_product_name(
                processed_data['name'])

        # Ulepsz opis
        if 'description' in processed_data and processed_data['description']:
            processed_data['description'] = self.enhance_product_description(
                processed_data['description'])

        # Utwórz krótki opis jeśli nie ma lub jest pusty
        if 'short_description' not in processed_data or not processed_data.get('short_description'):
            if processed_data.get('description'):
                processed_data['short_description'] = self.create_short_description(
                    processed_data['description']
                )

        logger.info("Dane produktu przetworzone przez AI")
        return processed_data
