"""
Moduł przetwarzania danych produktów przez OpenAI/HuggingFace.
"""
import logging
from typing import Dict, Optional
import os
import time

logger = logging.getLogger(__name__)


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

    def enhance_product_description(self, original_description: str) -> str:
        """
        Ulepsza opis produktu przez AI.

        Args:
            original_description: Oryginalny opis produktu

        Returns:
            Ulepszony opis produktu
        """
        if not original_description or not original_description.strip():
            return ""

        try:
            if self.api_type == 'openai':
                # Sprawdź czy używamy klucza Novita (może obsługiwać model KIMI-K2-THINKING)
                # Spróbuj najpierw KIMI-K2-THINKING jeśli klucz to OPENAI_API_KEY_NOVITA
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
                max_retries = 3
                retry_delay = 2  # sekundy
                enhanced = None

                for attempt in range(max_retries):
                    try:
                        response = self.client.chat.completions.create(
                            model="moonshotai/Kimi-K2-Thinking",
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
                            timeout=60  # Zwiększony timeout
                        )

                        if response.choices[0].message.content:
                            enhanced = response.choices[0].message.content.strip(
                            )
                        else:
                            enhanced = original_description
                        break  # Sukces - wyjdź z pętli retry

                    except Exception as e:
                        error_msg = str(e)
                        if "504" in error_msg or "Gateway Timeout" in error_msg or "timeout" in error_msg.lower() or "InternalServerError" in error_msg:
                            if attempt < max_retries - 1:
                                logger.warning(
                                    f"Błąd 504/timeout HuggingFace (próba {attempt + 1}/{max_retries}), czekam {retry_delay}s i ponawiam...")
                                print(
                                    f"[DEBUG] Błąd 504/timeout HuggingFace (próba {attempt + 1}/{max_retries}), czekam {retry_delay}s i ponawiam...")
                                time.sleep(retry_delay)
                                retry_delay *= 2  # Exponential backoff
                                continue
                            else:
                                logger.error(
                                    f"Błąd 504/timeout HuggingFace po {max_retries} próbach: {e}")
                                print(
                                    f"[DEBUG] Błąd 504/timeout HuggingFace po {max_retries} próbach")
                                # Zwróć oryginalny opis jako fallback
                                enhanced = original_description
                                break
                        else:
                            # Inny błąd - nie retry, zwróć oryginalny opis
                            logger.error(f"Błąd HuggingFace API: {e}")
                            print(f"[DEBUG] Błąd HuggingFace API: {e}")
                            enhanced = original_description
                            break

                if not enhanced:
                    enhanced = original_description
            else:
                raise ValueError(f"Nieobsługiwany typ API: {self.api_type}")

            logger.info(f"Opis ulepszony przez AI (długość: {len(enhanced)})")
            return enhanced

        except Exception as e:
            logger.error(f"Błąd podczas ulepszania opisu przez AI: {e}")
            # Jeśli OpenAI nie działa, spróbuj HuggingFace jako fallback
            if self.api_type == 'openai':
                hf_token = os.getenv('HF_TOKEN')
                if hf_token:
                    logger.info("Próba użycia HuggingFace jako fallback...")
                    try:
                        fallback_processor = AIProcessor(
                            api_key=hf_token, api_type='huggingface')
                        enhanced = fallback_processor.enhance_product_description(
                            original_description)
                        if enhanced and enhanced != original_description:
                            logger.info("Użyto HuggingFace jako fallback")
                            return enhanced
                    except Exception as fallback_error:
                        logger.error(
                            f"Błąd podczas fallback do HuggingFace: {fallback_error}")

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

    def create_short_description(self, description: str, max_length: int = 500) -> str:
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
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
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
            # Obetnij do max_length jeśli za długi
            if len(short_desc) > max_length:
                short_desc = short_desc[:max_length].rsplit(' ', 1)[0] + '...'

            logger.info(
                f"Krótki opis utworzony przez AI (długość: {len(short_desc)})")
            return short_desc

        except Exception as e:
            logger.error(
                f"Błąd podczas tworzenia krótkiego opisu przez AI: {e}")
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
