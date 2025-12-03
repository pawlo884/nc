"""
Moduł przetwarzania produktów - łączy automatyzację przeglądarki z AI.
"""
import logging
from typing import Dict, List, Optional
from .browser_automation import BrowserAutomation
from .ai_processor import AIProcessor

logger = logging.getLogger(__name__)


class ProductProcessor:
    """Klasa do przetwarzania produktów - łączy automatyzację przeglądarki z AI"""
    
    def __init__(self, browser_automation: BrowserAutomation, ai_processor: AIProcessor):
        """
        Inicjalizacja procesora produktów.
        
        Args:
            browser_automation: Instancja BrowserAutomation
            ai_processor: Instancja AIProcessor
        """
        self.browser_automation = browser_automation
        self.ai_processor = ai_processor
        logger.info("ProductProcessor zainicjalizowany")
    
    def get_product_from_database(self, product_id: int) -> Optional[Dict]:
        """
        Pobiera dane produktu z bazy matterhorn1.
        
        Args:
            product_id: ID produktu
            
        Returns:
            Słownik z danymi produktu lub None
        """
        try:
            from django.db import connections
            with connections['matterhorn1'].cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        p.id,
                        p.product_uid,
                        p.name,
                        p.description,
                        p.color,
                        p.active,
                        p.is_mapped,
                        b.name as brand_name,
                        c.name as category_name,
                        c.category_id as category_id,
                        b.id as brand_db_id
                    FROM product p
                    LEFT JOIN brand b ON p.brand_id = b.id
                    LEFT JOIN category c ON p.category_id = c.id
                    WHERE p.id = %s
                """, [product_id])
                
                row = cursor.fetchone()
                if not row:
                    logger.warning(f"Produkt {product_id} nie znaleziony w bazie")
                    return None
                
                product_data = {
                    'id': row[0],
                    'product_uid': row[1],
                    'name': row[2] or '',
                    'description': row[3] or '',
                    'color': row[4] or '',
                    'active': row[5],
                    'is_mapped': row[6],
                    'brand_name': row[7] or '',
                    'category_name': row[8] or '',
                    'category_id': row[9],
                    'brand_id': row[10],
                }
                
                logger.info(f"Pobrano dane produktu {product_id} z bazy")
                return product_data
                
        except Exception as e:
            logger.error(f"Błąd podczas pobierania produktu {product_id} z bazy: {e}")
            return None
    
    def get_product_variants(self, product_id: int) -> List[Dict]:
        """
        Pobiera warianty produktu z bazy matterhorn1.
        
        Args:
            product_id: ID produktu
            
        Returns:
            Lista słowników z danymi wariantów
        """
        try:
            from django.db import connections
            with connections['matterhorn1'].cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        pv.id,
                        pv.name,
                        pv.stock,
                        pv.variant_uid,
                        pv.ean
                    FROM productvariant pv
                    WHERE pv.product_id = %s
                """, [product_id])
                
                rows = cursor.fetchall()
                variants = []
                
                for row in rows:
                    variants.append({
                        'id': row[0],
                        'size': row[1] or '',
                        'stock': row[2] or 0,
                        'variant_uid': row[3] or '',
                        'producer_code': row[4] or '',  # EAN jako producer_code
                    })
                
                logger.info(f"Pobrano {len(variants)} wariantów produktu {product_id}")
                return variants
                
        except Exception as e:
            logger.error(f"Błąd podczas pobierania wariantów produktu {product_id}: {e}")
            return []
    
    def prepare_mpd_form_data(self, product_data: Dict, variants: List[Dict] = None) -> Dict:
        """
        Przygotowuje dane do wypełnienia formularza MPD.
        
        Args:
            product_data: Dane produktu z bazy
            variants: Lista wariantów produktu
            
        Returns:
            Słownik z danymi do formularza MPD
        """
        # Przetwórz dane przez AI
        processed_data = self.ai_processor.process_product_data({
            'name': product_data.get('name', ''),
            'description': product_data.get('description', ''),
            'short_description': '',  # Zostanie utworzony przez AI
        })
        
        # Przygotuj dane formularza
        form_data = {
            'name': processed_data.get('name', ''),
            'description': processed_data.get('description', ''),
            'short_description': processed_data.get('short_description', ''),
            'brand_name': product_data.get('brand_name', ''),
            'size_category': self._determine_size_category(product_data, variants),
            'producer_code': self._get_producer_code_from_variants(variants) if variants else '',
            'producer_color_name': product_data.get('color', ''),
            'series_name': self._extract_series_name(product_data.get('name', '')),
        }
        
        logger.info(f"Przygotowano dane formularza MPD dla produktu {product_data.get('id')}")
        return form_data
    
    def _determine_size_category(self, product_data: Dict, variants: List[Dict] = None) -> str:
        """
        Określa kategorię rozmiarową na podstawie danych produktu.
        
        Args:
            product_data: Dane produktu
            variants: Lista wariantów
            
        Returns:
            Nazwa kategorii rozmiarowej
        """
        # Logika określania kategorii rozmiarowej
        # Można rozszerzyć o bardziej zaawansowaną logikę
        name = product_data.get('name', '').lower()
        category = product_data.get('category_name', '').lower()
        
        if 'strój kąpielowy' in name or 'bikini' in name or 'kostium' in name:
            return 'strój kąpielowy'
        elif 'sukienka' in name or 'dress' in name:
            return 'sukienka'
        elif 'spódnica' in name or 'skirt' in name:
            return 'spódnica'
        elif 'spodnie' in name or 'pants' in name or 'trousers' in name:
            return 'spodnie'
        elif 'bluzka' in name or 'top' in name or 'shirt' in name:
            return 'bluzka'
        else:
            return 'inne'
    
    def _get_producer_code_from_variants(self, variants: List[Dict]) -> str:
        """
        Pobiera kod producenta z wariantów.
        
        Args:
            variants: Lista wariantów
            
        Returns:
            Kod producenta lub pusty string
        """
        if not variants:
            return ''
        
        # Weź kod z pierwszego wariantu, który ma kod
        for variant in variants:
            if variant.get('producer_code'):
                return variant['producer_code']
        
        return ''
    
    def _extract_series_name(self, product_name: str) -> str:
        """
        Wyciąga nazwę serii z nazwy produktu.
        
        Args:
            product_name: Nazwa produktu
            
        Returns:
            Nazwa serii lub pusty string
        """
        # Przykładowa logika - można rozszerzyć
        # Szukaj wzorców typu "Lupo Line", "Collection 2024", etc.
        import re
        
        # Wzorce do wykrywania serii
        patterns = [
            r'Lupo\s+Line',
            r'Collection\s+\d{4}',
            r'Series\s+\w+',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, product_name, re.IGNORECASE)
            if match:
                return match.group(0)
        
        return ''
    
    def process_product(self, product_id: int) -> Dict:
        """
        Główna metoda przetwarzania produktu.
        
        Args:
            product_id: ID produktu
            
        Returns:
            Słownik z wynikiem przetwarzania (success, mpd_product_id, error_message)
        """
        try:
            logger.info(f"Rozpoczęcie przetwarzania produktu {product_id}")
            
            # Pobierz dane z bazy
            product_data = self.get_product_from_database(product_id)
            if not product_data:
                return {
                    'success': False,
                    'mpd_product_id': None,
                    'error_message': f'Produkt {product_id} nie znaleziony w bazie'
                }
            
            # Pobierz warianty
            variants = self.get_product_variants(product_id)
            
            # Przygotuj dane formularza
            form_data = self.prepare_mpd_form_data(product_data, variants)
            
            # Przejdź do strony produktu
            self.browser_automation.navigate_to_product_change(product_id)
            
            # Wypełnij formularz MPD
            self.browser_automation.fill_mpd_form(form_data)
            
            # Wyślij formularz
            self.browser_automation.submit_mpd_form()
            
            # Czekaj na wynik
            result = self.browser_automation.wait_for_submission_result()
            
            logger.info(f"Przetwarzanie produktu {product_id} zakończone: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Błąd podczas przetwarzania produktu {product_id}: {e}")
            return {
                'success': False,
                'mpd_product_id': None,
                'error_message': str(e)
            }
    
    def process_product_list(self, product_ids: List[int]) -> Dict:
        """
        Przetwarzanie listy produktów.
        
        Args:
            product_ids: Lista ID produktów
            
        Returns:
            Słownik ze statystykami przetwarzania
        """
        stats = {
            'total': len(product_ids),
            'success': 0,
            'failed': 0,
            'results': []
        }
        
        logger.info(f"Rozpoczęcie przetwarzania {len(product_ids)} produktów")
        
        for product_id in product_ids:
            result = self.process_product(product_id)
            stats['results'].append({
                'product_id': product_id,
                'success': result['success'],
                'mpd_product_id': result.get('mpd_product_id'),
                'error_message': result.get('error_message')
            })
            
            if result['success']:
                stats['success'] += 1
            else:
                stats['failed'] += 1
        
        logger.info(f"Przetwarzanie zakończone: {stats['success']} sukcesów, {stats['failed']} błędów")
        return stats

