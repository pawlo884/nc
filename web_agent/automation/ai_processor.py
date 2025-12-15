"""
Moduł przetwarzania danych produktów przez OpenAI/HuggingFace.
"""
import logging
from typing import Dict, Optional, List
import os
import time
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


class ProductNameStructure(BaseModel):
    """
    Struktura nazwy produktu zapewniająca spójność i profesjonalizm.
    Format: "Kostium kąpielowy [nazwa_modelu]"
    """
    base_type: str = Field(
        ...,
        description="Podstawowy typ produktu - zawsze 'Kostium kąpielowy'",
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
        Zwraca finalną nazwę produktu w formacie 'Kostium kąpielowy [nazwa_modelu]'.
        Zawsze buduje z base_type i model_name, ignorując final_name z JSON.
        """
        # Zawsze buduj z base_type i model_name
        base = "Kostium kąpielowy"  # Zawsze "Kostium kąpielowy"
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
        """Walidacja base_type - zawsze zwraca 'Kostium kąpielowy'"""
        # Zawsze zwracaj "Kostium kąpielowy" niezależnie od inputu
        return "Kostium kąpielowy"


class ProductDescriptionStructure(BaseModel):
    """
    Struktura opisu produktu zapewniająca spójność dla wszystkich produktów.
    """
    introduction: str = Field(
        ...,
        description="Chwytliwe otwarcie (1-2 zdania) przyciągające uwagę klienta",
        min_length=50,
        max_length=200
    )
    key_features: List[str] = Field(
        ...,
        description="Lista 3-5 kluczowych cech i korzyści produktu",
        min_length=3,
        max_length=5
    )
    technical_details: str = Field(
        ...,
        description="Szczegóły techniczne: materiał, krój, dopasowanie, konstrukcja",
        min_length=100,
        max_length=300
    )
    target_audience: str = Field(
        ...,
        description="Dla kogo jest produkt (typ sylwetki, styl życia)",
        min_length=50,
        max_length=150
    )
    occasions: str = Field(
        ...,
        description="Okazje do noszenia (plaża, basen, wakacje, sesje zdjęciowe)",
        min_length=50,
        max_length=150
    )
    call_to_action: str = Field(
        ...,
        description="Zachęta do zakupu (1 zdanie)",
        min_length=20,
        max_length=100
    )

    def to_formatted_text(self) -> str:
        """
        Konwertuje strukturę na sformatowany tekst opisu produktu.
        """
        lines = [
            self.introduction,
            "",
            "Kluczowe cechy:",
            *[f"• {feature}" for feature in self.key_features],
            "",
            self.technical_details,
            "",
            f"Dla kogo: {self.target_audience}",
            "",
            f"Okazje: {self.occasions}",
            "",
            self.call_to_action
        ]
        return "\n".join(lines)

    @field_validator('introduction', 'technical_details', 'target_audience', 'occasions', 'call_to_action')
    @classmethod
    def validate_text_fields(cls, v: str) -> str:
        """Walidacja i normalizacja pól tekstowych"""
        if not v or not v.strip():
            raise ValueError("Pole nie może być puste")
        return v.strip()

    @field_validator('key_features')
    @classmethod
    def validate_key_features(cls, v: List[str]) -> List[str]:
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

    def enhance_product_description(self, original_description: str, use_structured: bool = True) -> str:
        """
        Ulepsza opis produktu przez AI z użyciem strukturyzowanej formy (Pydantic).

        Args:
            original_description: Oryginalny opis produktu
            use_structured: Czy używać strukturyzowanej formy (Pydantic). Domyślnie True.

        Returns:
            Ulepszony opis produktu
        """
        if not original_description or not original_description.strip():
            return ""

        try:
            if use_structured:
                return self._enhance_with_structure(original_description)
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
            'technical_details': 300,
            'target_audience': 150,
            'occasions': 150,
            'call_to_action': 100
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

        # Skróć również key_features jeśli są zbyt długie
        if 'key_features' in truncated_data and isinstance(truncated_data['key_features'], list):
            truncated_data['key_features'] = [
                feature[:200] + '...' if len(feature) > 200 else feature
                for feature in truncated_data['key_features']
            ]

        return truncated_data

    def _enhance_with_structure(self, original_description: str) -> str:
        """
        Ulepsza opis produktu używając strukturyzowanej formy (Pydantic).
        """
        import json

        system_prompt = """Jesteś ekspertem od copywritingu e-commerce specjalizującym się w modzie plażowej i strojach kąpielowych.

TWOJE ZADANIE:
Przekształć podany opis produktu w strukturęzowany, atrakcyjny tekst dla sklepu online.

WYTYCZNE:

1. STYL I TON:
- Przyjazny, inspirujący, lekko lifestyle'owy
- Zwracaj się do klienta w sposób naturalny
- Buduj emocjonalny związek z produktem

2. STRUKTURA (JSON) - WAŻNE: PRZESTRZEGAJ DOKŁADNIE LIMITÓW ZNAKÓW:
- introduction: Chwytliwe otwarcie (1-2 zdania, MAKSYMALNIE 200 znaków - nie przekraczaj!)
- key_features: Lista 3-5 kluczowych cech i korzyści (każda jako osobny string, max 200 znaków każda)
- technical_details: Szczegóły techniczne - materiał, krój, dopasowanie, konstrukcja (100-300 znaków, MAKSYMALNIE 300 znaków!)
- target_audience: Dla kogo (typ sylwetki, styl życia) (50-150 znaków, MAKSYMALNIE 150 znaków - bardzo ważne!)
- occasions: Okazje do noszenia (plaża, basen, wakacje) (50-150 znaków, MAKSYMALNIE 150 znaków!)
- call_to_action: Zachęta do zakupu (1 zdanie, 20-100 znaków, MAKSYMALNIE 100 znaków!)

UWAGA: Jeśli przekroczysz limity znaków, odpowiedź zostanie odrzucona. Bądź zwięzły i precyzyjny!

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

5. CZEGO UNIKAĆ:
- Przesadnych obietnic
- Sztampowych frazesów
- Zbyt technicznego języka
- Powtórzeń

ODPOWIEDŹ MUSI BYĆ W FORMACIE JSON zgodnym z podanym schematem."""

        user_prompt = f"Przekształć ten opis produktu w strukturęzowany format JSON:\n\n{original_description}"

        # Próba użycia structured output (jeśli dostępne)
        try:
            if self.api_type == 'openai':
                model_name = "gpt-4o-mini"
                if os.getenv('OPENAI_API_KEY_NOVITA') == self.api_key:
                    model_name = "KIMI-K2-THINKING"

                # Spróbuj użyć response_format dla structured output
                try:
                    response = self.client.chat.completions.create(
                        model=model_name,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        response_format={"type": "json_object"},
                        temperature=0.7,
                        max_tokens=1500,
                        timeout=120
                    )
                except Exception:
                    # Fallback - zwykłe wywołanie bez response_format
                    response = self.client.chat.completions.create(
                        model=model_name,
                        messages=[
                            {"role": "system", "content": system_prompt +
                                "\n\nODPOWIEDŹ MUSI BYĆ TYLKO JSON, BEZ ŻADNYCH DODATKOWYCH KOMENTARZY."},
                            {"role": "user", "content": user_prompt}
                        ],
                        temperature=0.7,
                        max_tokens=1500,
                        timeout=120
                    )

                content = response.choices[0].message.content
                if not content:
                    raise ValueError("Pusta odpowiedź z API")

                content = content.strip()

                # Wyciągnij JSON z odpowiedzi (może być otoczony markdown)
                if "```json" in content:
                    content = content.split("```json")[
                        1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()

                # Parsuj JSON
                data = json.loads(content)

                # Skróć pola do limitów przed walidacją
                data = self._truncate_fields_to_limits(data)

                # Waliduj przez Pydantic
                description_structure = ProductDescriptionStructure(**data)

                # Konwertuj na tekst
                formatted_text = description_structure.to_formatted_text()

                logger.info(
                    f"Opis ulepszony przez AI ze strukturą (długość: {len(formatted_text)})")
                return formatted_text

            elif self.api_type == 'huggingface':
                # HuggingFace - użyj tego samego podejścia
                max_retries = 5
                retry_delay = 5

                for attempt in range(max_retries):
                    try:
                        response = self.client.chat.completions.create(
                            model="moonshotai/Kimi-K2-Thinking",
                            messages=[
                                {"role": "system", "content": system_prompt +
                                    "\n\nODPOWIEDŹ MUSI BYĆ TYLKO JSON, BEZ ŻADNYCH DODATKOWYCH KOMENTARZY."},
                                {"role": "user", "content": user_prompt}
                            ],
                            temperature=0.7,
                            max_tokens=1500,
                            timeout=120
                        )

                        content = response.choices[0].message.content
                        if not content:
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

                        # Skróć pola do limitów przed walidacją
                        data = self._truncate_fields_to_limits(data)

                        # Waliduj przez Pydantic
                        description_structure = ProductDescriptionStructure(
                            **data)
                        formatted_text = description_structure.to_formatted_text()

                        logger.info(
                            f"Opis ulepszony przez AI ze strukturą (długość: {len(formatted_text)})")
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
                # Sprawdź czy używamy klucza Novita (może obsługiwać model KIMI-K2-THINKING)
                model_name = "gpt-4o-mini"  # Domyślny model
                if os.getenv('OPENAI_API_KEY_NOVITA') == self.api_key:
                    model_name = "KIMI-K2-THINKING"  # Spróbuj użyć modelu KIMI

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
                # Użyj HuggingFace Router API z modelem KIMI-K2-THINKING
                # Spróbuj kilka razy z retry w przypadku błędów 504/timeout
                max_retries = 5  # Zwiększona liczba prób
                # Zwiększony początkowy delay (5, 10, 20, 40, 60 sekund)
                retry_delay = 5
                enhanced = None

                # Lista modeli do próby
                # Bez :novita HuggingFace Router automatycznie wybiera najlepszy dostępny model
                models_to_try = [
                    # Główny model (automatyczny wybór)
                    "moonshotai/Kimi-K2-Thinking",
                ]

                success = False
                for attempt in range(max_retries):
                    if success:
                        break

                    for model in models_to_try:
                        if success:
                            break

                        try:
                            logger.info(
                                f"Próba {attempt + 1}/{max_retries} z modelem {model}")
                            print(
                                f"[DEBUG] Próba {attempt + 1}/{max_retries} z modelem {model}")

                            response = self.client.chat.completions.create(
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
                                max_tokens=1000,
                                timeout=120  # Zwiększony timeout do 120 sekund
                            )

                            if response.choices[0].message.content:
                                enhanced = response.choices[0].message.content.strip(
                                )
                            else:
                                enhanced = original_description

                            # Sukces - wyjdź z obu pętli
                            logger.info(f"Sukces z modelem {model}")
                            print(f"[DEBUG] Sukces z modelem {model}")
                            success = True
                            break

                        except Exception as e:
                            error_msg = str(e)
                            logger.warning(
                                f"Błąd z modelem {model}: {error_msg[:100]}")
                            print(
                                f"[DEBUG] Błąd z modelem {model}: {error_msg[:100]}")

                            # Jeśli to timeout/504, spróbuj następnego modelu lub retry
                            is_timeout = (
                                "504" in error_msg or "Gateway Timeout" in error_msg or
                                "timeout" in error_msg.lower() or "InternalServerError" in error_msg or
                                "Request timed out" in error_msg
                            )

                            if is_timeout:
                                # Spróbuj następnego modelu w tej samej próbie
                                if model != models_to_try[-1]:
                                    continue  # Spróbuj następnego modelu
                                # Jeśli to ostatni model, przejdź do retry
                                if attempt < max_retries - 1:
                                    logger.warning(
                                        f"Błąd 504/timeout HuggingFace (próba {attempt + 1}/{max_retries}), "
                                        f"czekam {retry_delay}s i ponawiam...")
                                    print(
                                        f"[DEBUG] Błąd 504/timeout HuggingFace (próba {attempt + 1}/{max_retries}), "
                                        f"czekam {retry_delay}s i ponawiam...")
                                    time.sleep(retry_delay)
                                    # Exponential backoff, max 60s
                                    retry_delay = min(retry_delay * 2, 60)
                                    break  # Wyjdź z pętli modeli, przejdź do następnej próby
                                else:
                                    # Ostatnia próba - zwróć oryginalny opis
                                    logger.error(
                                        f"Błąd 504/timeout HuggingFace po {max_retries} próbach z wszystkimi modelami")
                                    print(
                                        f"[DEBUG] Błąd 504/timeout HuggingFace po {max_retries} próbach z wszystkimi modelami")
                                    enhanced = original_description
                                    success = True  # Zakończ pętle
                                    break
                            else:
                                # Inny błąd - spróbuj następnego modelu
                                if model != models_to_try[-1]:
                                    continue  # Spróbuj następnego modelu
                                else:
                                    # Ostatni model, inny błąd - zwróć oryginalny opis
                                    logger.error(
                                        f"Błąd HuggingFace API z wszystkimi modelami: {e}")
                                    print(
                                        "[DEBUG] Błąd HuggingFace API z wszystkimi modelami")
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
                                model_name = "KIMI-K2-THINKING"

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
                            model_name = "KIMI-K2-THINKING"

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

        system_prompt = """Jesteś ekspertem od nazewnictwa produktów tekstylnych i modowych.

TWOJE ZADANIE:
Przekształć podaną nazwę produktu w profesjonalną nazwę dla sklepu online.

WYTYCZNE:

1. STRUKTURA (JSON) - WAŻNE: PRZESTRZEGAJ DOKŁADNIE LIMITÓW ZNAKÓW:
- base_type: ZAWSZE "Kostium kąpielowy" (nie zmieniaj tego!)
- model_name: Nazwa modelu (np. 'Ada', 'Lupo', 'Elegant') - WYMAGANE, 1-30 znaków
- final_name: Finalna nazwa w formacie "Kostium kąpielowy [model_name]" - 5-100 znaków, MAKSYMALNIE 100 znaków!

2. FORMAT FINALNEJ NAZWY:
- Format: "Kostium kąpielowy [model_name]" (np. "Kostium kąpielowy Ada")
- ZAWSZE zaczynaj od "Kostium kąpielowy"
- NIE dodawaj koloru, kodu produktu, numerów w nawiasach, marki
- NIE dodawaj niczego poza "Kostium kąpielowy" i nazwą modelu
- Używaj wielkich liter tylko na początku wyrazów (Title Case)

3. PRZYKŁADY:
- Input: "Kostium dwuczęściowy Kostium kąpielowy Model Ada M-803 (1) Lilia - Marko"
- Output: {"base_type": "Kostium kąpielowy", "model_name": "Ada", "final_name": "Kostium kąpielowy Ada"}

- Input: "Kostium kąpielowy Model Elegant Czarny"
- Output: {"base_type": "Kostium kąpielowy", "model_name": "Elegant", "final_name": "Kostium kąpielowy Elegant"}

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
                    model_name = "KIMI-K2-THINKING"

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
                        max_tokens=300,
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
                max_retries = 5
                retry_delay = 5

                logger.info(
                    f"Używam API: {self.api_type}, model: moonshotai/Kimi-K2-Thinking")
                print(
                    f"[DEBUG] Używam API: {self.api_type}, model: moonshotai/Kimi-K2-Thinking")

                for attempt in range(max_retries):
                    try:
                        response = self.client.chat.completions.create(
                            model="moonshotai/Kimi-K2-Thinking",
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

        # Zbuduj strukturę zgodnie z ProductNameStructure
        data = {
            "base_type": "Kostium kąpielowy",
            "model_name": model_name,
            "final_name": f"Kostium kąpielowy {model_name}",
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
                    model_name = "KIMI-K2-THINKING"

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
                # Użyj tego samego modelu co dla długiego opisu z retry logic
                max_retries = 5
                retry_delay = 5
                short_desc = None

                # Bez :novita HuggingFace Router automatycznie wybiera najlepszy dostępny model
                models_to_try = [
                    # Główny model (automatyczny wybór)
                    "moonshotai/Kimi-K2-Thinking",
                ]

                success = False
                for attempt in range(max_retries):
                    if success:
                        break

                    for model in models_to_try:
                        if success:
                            break

                        try:
                            response = self.client.chat.completions.create(
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
                                max_tokens=200,
                                timeout=120
                            )

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
                                if model != models_to_try[-1]:
                                    continue
                                if attempt < max_retries - 1:
                                    time.sleep(retry_delay)
                                    retry_delay = min(retry_delay * 2, 60)
                                    break
                                else:
                                    short_desc = description[:max_length] if description else ""
                                    success = True
                                    break
                            else:
                                if model != models_to_try[-1]:
                                    continue
                                else:
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
                                model_name = "KIMI-K2-THINKING"

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
                            model_name = "KIMI-K2-THINKING"

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
            "Wybierz tylko atrybuty, które rzeczywiście występują w opisie produktu."
        )

        user_prompt = (
            f"Opis produktu: {description}\n\n"
            f"Dostępne atrybuty do wyboru: {available_attrs_text}\n\n"
            "Wyodrębnij listę kluczowych atrybutów, które pasują do opisu produktu. "
            "Zwróć wynik w formacie JSON: {\"attributes\": [\"nazwa atrybutu 1\", \"nazwa atrybutu 2\", ...]}. "
            "Używaj dokładnie takich nazw atrybutów, jakie są w liście dostępnych atrybutów. "
            "Wybierz tylko te atrybuty, które rzeczywiście są wspomniane w opisie produktu."
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

            # Parsuj JSON
            result = json.loads(content)

            if 'attributes' not in result or not isinstance(result['attributes'], list):
                raise ValueError(
                    "Nieprawidłowy format odpowiedzi z OpenAI API")

            extracted_attr_names = [attr.strip()
                                    for attr in result['attributes']]

            logger.info(
                f"LLM wyodrębnił następujące atrybuty: {extracted_attr_names}")
            print(
                f"[DEBUG] LLM wyodrębnił następujące atrybuty: {extracted_attr_names}")

            # Dopasuj wyodrębnione nazwy do dostępnych atrybutów
            matched_attr_ids = []
            attr_name_to_id = {attr['name'].lower(): attr['id']
                               for attr in available_attributes}

            for extracted_name in extracted_attr_names:
                extracted_lower = extracted_name.lower()
                # Dokładne dopasowanie
                if extracted_lower in attr_name_to_id:
                    matched_attr_ids.append(attr_name_to_id[extracted_lower])
                    logger.info(
                        f"Dopasowano: '{extracted_name}' -> ID: {attr_name_to_id[extracted_lower]}")
                    print(
                        f"[DEBUG] Dopasowano: '{extracted_name}' -> ID: {attr_name_to_id[extracted_lower]}")
                else:
                    # Próba częściowego dopasowania
                    matched = False
                    for attr_name, attr_id in attr_name_to_id.items():
                        if extracted_lower in attr_name or attr_name in extracted_lower:
                            matched_attr_ids.append(attr_id)
                            logger.info(
                                f"Dopasowano częściowo: '{extracted_name}' -> '{attr_name}' (ID: {attr_id})")
                            print(
                                f"[DEBUG] Dopasowano częściowo: '{extracted_name}' -> '{attr_name}' (ID: {attr_id})")
                            matched = True
                            break
                    if not matched:
                        logger.warning(
                            f"Nie znaleziono dopasowania dla atrybutu: '{extracted_name}'")
                        print(
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
