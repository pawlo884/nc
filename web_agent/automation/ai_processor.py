"""
Moduł przetwarzania danych produktów przez OpenAI/HuggingFace.
"""
import logging
from typing import Dict, Optional, List
import os
import time
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


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

2. STRUKTURA (JSON):
- introduction: Chwytliwe otwarcie (1-2 zdania, 50-200 znaków)
- key_features: Lista 3-5 kluczowych cech i korzyści (każda jako osobny string)
- technical_details: Szczegóły techniczne - materiał, krój, dopasowanie, konstrukcja (100-300 znaków)
- target_audience: Dla kogo (typ sylwetki, styl życia) (50-150 znaków)
- occasions: Okazje do noszenia (plaża, basen, wakacje) (50-150 znaków)
- call_to_action: Zachęta do zakupu (1 zdanie, 20-100 znaków)

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

                        # Parsuj i waliduj
                        data = json.loads(content)
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

    def enhance_product_name(self, original_name: str) -> str:
        """
        Ulepsza nazwę produktu przez AI.

        Args:
            original_name: Oryginalna nazwa produktu

        Returns:
            Ulepszona nazwa produktu
        """
        if not original_name or not original_name.strip():
            return ""

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
            logger.info(f"Nazwa ulepszona przez AI: {enhanced}")
            return enhanced

        except Exception as e:
            logger.error(f"Błąd podczas ulepszania nazwy przez AI: {e}")
            return original_name

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
