"""
Moduł przetwarzania danych produktów przez OpenAI.
"""
import logging
from typing import Dict, Optional
from openai import OpenAI

logger = logging.getLogger(__name__)


class AIProcessor:
    """Klasa do modyfikacji danych produktów przez OpenAI"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Inicjalizacja procesora AI.
        
        Args:
            api_key: Klucz API OpenAI. Jeśli None, próbuje pobrać z zmiennych środowiskowych.
        """
        if api_key is None:
            import os
            api_key = os.getenv('OPENAI_API_KEY')
        
        if not api_key:
            raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY environment variable.")
        
        self.client = OpenAI(api_key=api_key)
        logger.info("AIProcessor zainicjalizowany")
    
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
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "Jesteś ekspertem od opisu produktów tekstylnych. Ulepszaj opisy produktów, "
                                 "zachowując oryginalne informacje, ale czyniąc je bardziej atrakcyjnymi i profesjonalnymi. "
                                 "Odpowiadaj tylko ulepszonym opisem, bez dodatkowych komentarzy."
                    },
                    {
                        "role": "user",
                        "content": f"Ulepsz ten opis produktu:\n\n{original_description}"
                    }
                ],
                temperature=0.7,
                max_tokens=1000
            )
            
            enhanced = response.choices[0].message.content.strip()
            logger.info(f"Opis ulepszony przez AI (długość: {len(enhanced)})")
            return enhanced
            
        except Exception as e:
            logger.error(f"Błąd podczas ulepszania opisu przez AI: {e}")
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
            
            enhanced = response.choices[0].message.content.strip()
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
            
            short_desc = response.choices[0].message.content.strip()
            # Obetnij do max_length jeśli za długi
            if len(short_desc) > max_length:
                short_desc = short_desc[:max_length].rsplit(' ', 1)[0] + '...'
            
            logger.info(f"Krótki opis utworzony przez AI (długość: {len(short_desc)})")
            return short_desc
            
        except Exception as e:
            logger.error(f"Błąd podczas tworzenia krótkiego opisu przez AI: {e}")
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
        logger.info(f"Przetwarzanie danych produktu przez AI: {product_data.get('name', 'Unknown')}")
        
        processed_data = product_data.copy()
        
        # Ulepsz nazwę
        if 'name' in processed_data and processed_data['name']:
            processed_data['name'] = self.enhance_product_name(processed_data['name'])
        
        # Ulepsz opis
        if 'description' in processed_data and processed_data['description']:
            processed_data['description'] = self.enhance_product_description(processed_data['description'])
        
        # Utwórz krótki opis jeśli nie ma lub jest pusty
        if 'short_description' not in processed_data or not processed_data.get('short_description'):
            if processed_data.get('description'):
                processed_data['short_description'] = self.create_short_description(
                    processed_data['description']
                )
        
        logger.info("Dane produktu przetworzone przez AI")
        return processed_data

