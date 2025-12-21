"""
Moduł automatyzacji działający w tle (bez przeglądarki).
Wykonuje te same operacje co browser_automation.py, ale bezpośrednio przez Django ORM i API.
"""
import logging
from typing import Dict, Optional, List
from django.db import connections
from matterhorn1.models import Product, Brand, Category
from matterhorn1.saga import SagaService
from web_agent.automation.ai_processor import AIProcessor
from web_agent.models import ProducerColor, BrandConfig
from rapidfuzz import fuzz

logger = logging.getLogger(__name__)


class BackgroundAutomation:
    """Klasa do automatyzacji w tle (bez przeglądarki)"""

    def __init__(self, ai_processor: Optional[AIProcessor] = None):
        """
        Inicjalizacja automatyzacji w tle.

        Args:
            ai_processor: Instancja AIProcessor do ulepszania nazw/opisów. Jeśli None, tworzy nową.
        """
        self.ai_processor = ai_processor or AIProcessor()
        self._original_product_name = None
        logger.info("BackgroundAutomation zainicjalizowany")

    def get_products_by_filters(self, filters: Dict) -> List[Product]:
        """
        Pobiera produkty z bazy danych na podstawie filtrów (zamiast navigate_to_product_list).

        Args:
            filters: Słownik z filtrami (brand_id, category_id, active, is_mapped, brand_name, category_name)

        Returns:
            Lista produktów
        """
        try:
            queryset = Product.objects.all()

            if filters.get('brand_id'):
                queryset = queryset.filter(brand__brand_id=filters['brand_id'])
            elif filters.get('brand_name'):
                queryset = queryset.filter(brand__name__iexact=filters['brand_name'])

            if filters.get('category_id'):
                queryset = queryset.filter(category__category_id=filters['category_id'])
            elif filters.get('category_name'):
                queryset = queryset.filter(category__name__icontains=filters['category_name'])

            if filters.get('active') is not None:
                queryset = queryset.filter(active=filters['active'])

            if filters.get('is_mapped') is not None:
                queryset = queryset.filter(is_mapped=filters['is_mapped'])

            # Sortowanie zgodne z Django admin (ordering = ['-product_uid'])
            queryset = queryset.order_by('-product_uid')

            products = list(queryset[:100])  # Limit dla bezpieczeństwa
            logger.info(f"Znaleziono {len(products)} produktów z filtrami (sortowanie: -product_uid)")
            if products:
                logger.info(f"Pierwszy produkt: ID={products[0].id}, product_uid={products[0].product_uid}, name={products[0].name[:50]}")
                if len(products) > 1:
                    logger.info(f"Drugi produkt: ID={products[1].id}, product_uid={products[1].product_uid}, name={products[1].name[:50]}")
                if len(products) > 2:
                    logger.info(f"Trzeci produkt: ID={products[2].id}, product_uid={products[2].product_uid}, name={products[2].name[:50]}")
            return products
        except Exception as e:
            logger.error(f"Błąd podczas pobierania produktów: {e}")
            return []

    def get_product_from_database(self, product_id: int) -> Optional[Dict]:
        """
        Pobiera dane produktu z bazy danych (zamiast open_product_from_list_by_index).

        Args:
            product_id: ID produktu w matterhorn1

        Returns:
            Słownik z danymi produktu lub None
        """
        try:
            product = Product.objects.get(id=product_id)
            
            # Pobierz szczegóły produktu (size_table_html)
            size_table_html = None
            try:
                from django.conf import settings
                matterhorn1_db = (
                    'zzz_matterhorn1'
                    if 'zzz_matterhorn1' in settings.DATABASES
                    else 'matterhorn1'
                )
                with connections[matterhorn1_db].cursor() as cursor:
                    cursor.execute("""
                        SELECT pd.size_table, pd.size_table_html, pd.size_table_txt
                        FROM productdetails pd
                        WHERE pd.product_id = %s
                    """, [product_id])
                    row = cursor.fetchone()
                    if row:
                        size_table_html = row[0] or row[1] or row[2] or ""
            except Exception as e:
                logger.warning(f"Nie udało się pobrać szczegółów produktu: {e}")

            return {
                'id': product.id,
                'product_uid': product.product_uid,
                'name': product.name,
                'description': product.description or '',
                'color': product.color or '',
                'brand_id': product.brand.brand_id if product.brand else None,
                'brand_name': product.brand.name if product.brand else None,
                'category_id': product.category.category_id if product.category else None,
                'category_name': product.category.name if product.category else None,
                'is_mapped': product.is_mapped,
                'mapped_product_uid': product.mapped_product_uid,
                'size_table_html': size_table_html or ''
            }
        except Product.DoesNotExist:
            logger.error(f"Produkt {product_id} nie istnieje")
            return None
        except Exception as e:
            logger.error(f"Błąd podczas pobierania produktu {product_id}: {e}")
            return None

    def get_suggested_mpd_products(self, product: Product) -> List[Dict]:
        """
        Pobiera sugerowane produkty MPD dla przypisania (zamiast handle_assign_scenario z przeglądarki).
        Sprawdza zarówno podobieństwo nazw jak i kod producenta (M-XXX) dla wariantów.

        Args:
            product: Obiekt produktu z matterhorn1

        Returns:
            Lista słowników z sugerowanymi produktami [{'id': int, 'name': str, 'similarity': float, 'coverage': float}, ...]
        """
        try:
            suggestions = []
            suggestion_ids = set()  # Aby uniknąć duplikatów
            
            # Wyodrębnij kod producenta z nazwy produktu (np. M-809)
            producer_code = self.extract_producer_code_from_name(product.name)
            logger.info(f"Wyodrębniony kod producenta: {producer_code}")
            
            with connections['MPD'].cursor() as cursor:
                # PRIORYTET 1: Szukaj produktów z tym samym kodem producenta (warianty)
                if producer_code:
                    logger.info(f"Szukanie wariantów z kodem producenta: {producer_code}")
                    cursor.execute("""
                        SELECT DISTINCT p.id, p.name, b.name as brand_name
                        FROM products p 
                        LEFT JOIN brands b ON p.brand_id = b.id 
                        INNER JOIN product_variants pv ON p.id = pv.product_id
                        WHERE pv.producer_code = %s
                        ORDER BY p.name
                        LIMIT 10
                    """, [producer_code])
                    
                    for row in cursor.fetchall():
                        if row[0] not in suggestion_ids:
                            # Produkty z tym samym kodem producenta to warianty - 100% pokrycie
                            similarity = fuzz.ratio(product.name.lower(), row[1].lower())
                            coverage = 100.0  # Warianty zawsze mają 100% pokrycie
                            
                            suggestions.append({
                                'id': row[0],
                                'name': row[1],
                                'brand': row[2] or '',
                                'similarity': similarity,
                                'coverage': coverage,
                                'is_variant': True
                            })
                            suggestion_ids.add(row[0])
                            logger.info(f"Znaleziono wariant: ID={row[0]}, name={row[1]}, coverage=100%")
                
                # PRIORYTET 2: Wyszukaj podobne produkty w MPD po nazwie (jeśli nie znaleziono wariantów)
                if not suggestions or not producer_code:
                    logger.info(f"Szukanie podobnych produktów po nazwie: {product.name[:20]}")
                    cursor.execute("""
                        SELECT p.id, p.name, b.name as brand_name
                        FROM products p 
                        LEFT JOIN brands b ON p.brand_id = b.id 
                        WHERE LOWER(p.name) LIKE LOWER(%s)
                        ORDER BY p.name
                        LIMIT 10
                    """, [f'%{product.name[:20]}%'])

                    for row in cursor.fetchall():
                        if row[0] not in suggestion_ids:
                            similarity = fuzz.ratio(product.name.lower(), row[1].lower())
                            
                            # Oblicz "pokrycie" (coverage) - podobieństwo w %
                            # W przeglądarce pokrycie 100% oznacza pełne dopasowanie
                            coverage = similarity
                            
                            suggestions.append({
                                'id': row[0],
                                'name': row[1],
                                'brand': row[2] or '',
                                'similarity': similarity,
                                'coverage': coverage,
                                'is_variant': False
                            })
                            suggestion_ids.add(row[0])

            # Sortuj według pokrycia (najpierw warianty z 100%, potem podobne)
            return sorted(suggestions, key=lambda x: (x['coverage'], x.get('is_variant', False)), reverse=True)
        except Exception as e:
            logger.error(f"Błąd podczas pobierania sugerowanych produktów: {e}")
            import traceback
            traceback.print_exc()
            return []

    def enhance_product_name(self, original_name: str) -> str:
        """
        Ulepsza nazwę produktu przez AI.

        Args:
            original_name: Oryginalna nazwa produktu

        Returns:
            Ulepszona nazwa produktu
        """
        try:
            enhanced_name = self.ai_processor.enhance_product_name(
                original_name, use_structured=True
            )
            if not enhanced_name:
                logger.warning("AI nie zwróciło ulepszonej nazwy, używam oryginalnej")
                return original_name
            return enhanced_name
        except Exception as e:
            logger.error(f"Błąd podczas ulepszania nazwy: {e}")
            return original_name

    def enhance_product_description(self, description: str) -> str:
        """
        Ulepsza opis produktu przez AI.

        Args:
            description: Oryginalny opis produktu

        Returns:
            Ulepszony opis produktu
        """
        try:
            enhanced_description = self.ai_processor.enhance_product_description(description)
            if not enhanced_description:
                return description
            return enhanced_description
        except Exception as e:
            logger.error(f"Błąd podczas ulepszania opisu: {e}")
            return description

    def create_short_description(self, full_description: str) -> str:
        """
        Tworzy krótki opis produktu przez AI.

        Args:
            full_description: Pełny opis produktu

        Returns:
            Krótki opis produktu
        """
        try:
            short_description = self.ai_processor.create_short_description(
                full_description, max_length=250
            )
            if not short_description:
                return full_description[:250] if full_description else ''
            return short_description
        except Exception as e:
            logger.error(f"Błąd podczas tworzenia krótkiego opisu: {e}")
            return full_description[:250] if full_description else ''

    def extract_color_from_name(self, name: str) -> str:
        """
        Wyodrębnia kolor producenta z nazwy produktu (ta sama logika co w browser_automation.py).

        Args:
            name: Pełna nazwa produktu

        Returns:
            Nazwa koloru producenta lub pusty string
        """
        if not name:
            return ""

        import re
        name = name.strip()

        # Wzorzec 1: "Kolor - Marka" na końcu (obsługuje kolory z "/")
        match = re.search(
            r'([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+(?:\/[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+)*(?:\s+[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+(?:\/[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+)*)*)\s*-\s*[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+$', name)
        if match:
            color = match.group(1).strip()
            if len(color) > 1 and len(color) < 50:
                return color

        # Wzorzec 2: "(liczba) Kolor"
        match = re.search(
            r'\([^)]+\)\s+([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+(?:\/[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+)*(?:\s+[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+(?:\/[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+)*)*)\s*-\s*[A-ZĄĆĘŁŃÓŚŹŻ]', name)
        if match:
            color = match.group(1).strip()
            if len(color) > 1 and len(color) < 50:
                return color

        # Wzorzec 3: Ostatnie słowo przed ostatnim "-"
        parts = name.split(' - ')
        if len(parts) >= 2:
            before_last_dash = parts[-2].strip()
            words = before_last_dash.split()
            if words:
                last_word = words[-1]
                if last_word and last_word[0].isupper() and not last_word.replace('(', '').replace(')', '').replace('/', '').isdigit():
                    if len(last_word) > 1 and len(last_word) < 50:
                        return last_word

        return ""

    def extract_producer_code_from_name(self, name: str) -> str:
        """
        Wyodrębnia kod producenta z nazwy produktu (pattern: M-XXX).

        Args:
            name: Pełna nazwa produktu

        Returns:
            Kod producenta (np. "M-803") lub pusty string
        """
        if not name:
            return ""

        import re
        pattern = r'\bM-\d+(?:-\d+)?\b'
        match = re.search(pattern, name, re.IGNORECASE)
        if match:
            return match.group(0).upper()
        return ""

    def get_main_color_id(self, color_name: str) -> Optional[int]:
        """
        Pobiera ID głównego koloru z bazy MPD na podstawie nazwy.

        Args:
            color_name: Nazwa koloru

        Returns:
            ID koloru w MPD lub None
        """
        try:
            with connections['MPD'].cursor() as cursor:
                cursor.execute("""
                    SELECT id FROM colors 
                    WHERE LOWER(name) = LOWER(%s) AND parent_id IS NULL
                    LIMIT 1
                """, [color_name])
                result = cursor.fetchone()
                if result:
                    return result[0]
        except Exception as e:
            logger.warning(f"Błąd podczas pobierania koloru {color_name}: {e}")
        return None

    def extract_attributes_from_description(self, description: str) -> List[int]:
        """
        Wyciąga atrybuty z opisu produktu przez AI.

        Args:
            description: Opis produktu

        Returns:
            Lista ID atrybutów
        """
        try:
            # Pobierz dostępne atrybuty z MPD
            available_attributes = self.get_available_attributes()
            if not available_attributes:
                return []

            attribute_ids = self.ai_processor.extract_attributes_from_description(
                description, available_attributes
            )
            return attribute_ids or []
        except Exception as e:
            logger.error(f"Błąd podczas wyciągania atrybutów: {e}")
            return []

    def get_available_attributes(self) -> List[Dict]:
        """
        Pobiera listę dostępnych atrybutów z bazy MPD.

        Returns:
            Lista słowników z atrybutami [{'id': int, 'name': str}, ...]
        """
        try:
            with connections['MPD'].cursor() as cursor:
                cursor.execute("""
                    SELECT id, name FROM attributes 
                    ORDER BY name
                """)
                attributes = []
                for row in cursor.fetchall():
                    attributes.append({'id': row[0], 'name': row[1]})
                return attributes
        except Exception as e:
            logger.error(f"Błąd podczas pobierania atrybutów: {e}")
            return []

    def extract_fabric_materials(self, size_table_html: str) -> List[Dict]:
        """
        Wyodrębnia materiały i procenty z HTML (ta sama logika co w browser_automation.py).

        Args:
            size_table_html: Zawartość HTML z materiałami

        Returns:
            Lista słowników [{'component_id': int, 'percentage': int}, ...]
        """
        if not size_table_html:
            return []

        import re
        materials = []

        # Wzorzec 1: <strong>Materiał</strong> XX %
        pattern1 = r'<strong>([^<]+)</strong>\s*(\d+)\s*%'
        matches1 = re.findall(pattern1, size_table_html, re.IGNORECASE)

        for material_name, percentage_str in matches1:
            try:
                percentage = int(percentage_str)
                # Mapowanie nazw materiałów na ID w MPD
                material_mapping = {
                    "elastan": 1,
                    "poliamid": 2,
                }
                material_lower = material_name.lower().strip()
                component_id = None
                for key, value in material_mapping.items():
                    if key in material_lower:
                        component_id = value
                        break

                if component_id:
                    materials.append({
                        'component_id': component_id,
                        'percentage': percentage
                    })
            except ValueError:
                continue

        return materials

    def handle_assign_scenario(self, product_id: int, brand_id: int = None, brand_name: str = None) -> bool:
        """
        SCENARIUSZ ASSIGN: Sprawdza sugerowane produkty i przypisuje produkt do istniejącego w MPD.

        Args:
            product_id: ID produktu w matterhorn1
            brand_id: ID marki (opcjonalne)
            brand_name: Nazwa marki (opcjonalne)

        Returns:
            True jeśli znaleziono i przypisano produkt, False jeśli nie
        """
        try:
            logger.info("=" * 50)
            logger.info("SCENARIUSZ ASSIGN: Sprawdzanie sugerowanych produktów")
            logger.info("=" * 50)

            product = Product.objects.get(id=product_id)
            suggested_products = self.get_suggested_mpd_products(product)

            if not suggested_products:
                logger.info("Brak sugerowanych produktów w MPD")
                return False

            # Znajdź produkt z pokryciem 100% (lub najbliższy 100%)
            for suggested in suggested_products:
                if suggested['coverage'] >= 100.0:
                    mpd_product_id = suggested['id']
                    logger.info(f"Znaleziono produkt MPD z pokryciem 100%: {mpd_product_id}")

                    # Pobierz dane produktu
                    product_data = self.get_product_from_database(product_id)
                    if not product_data:
                        continue

                    # Wyodrębnij dane potrzebne do przypisania
                    original_name = product_data.get('name', '')
                    self._original_product_name = original_name

                    # KROK ASSIGN 1: Główny kolor
                    color_name = product_data.get('color', '')
                    main_color_id = None
                    if color_name:
                        main_color_id = self.get_main_color_id(color_name)

                    # KROK ASSIGN 2: Kolor producenta
                    producer_color_name = self.extract_color_from_name(original_name)
                    if producer_color_name and brand_id and brand_name:
                        # Sprawdź czy kolor istnieje w bazie
                        try:
                            color_obj = ProducerColor.objects.get(
                                brand_id=brand_id,
                                color_name=producer_color_name
                            )
                            color_obj.usage_count += 1
                            color_obj.save(update_fields=['usage_count', 'updated_at'])
                        except ProducerColor.DoesNotExist:
                            ProducerColor.objects.create(
                                brand_id=brand_id,
                                brand_name=brand_name,
                                color_name=producer_color_name
                            )

                    # KROK ASSIGN 3: Kod producenta
                    producer_code = self.extract_producer_code_from_name(original_name)

                    # Wywołaj assign_mapping bezpośrednio (zamiast klikania przycisku)
                    try:
                        from django.test import RequestFactory
                        from matterhorn1.admin import ProductAdmin
                        from django.http import QueryDict
                        
                        # Utwórz mock request (assign_mapping wymaga request.POST)
                        factory = RequestFactory()
                        post_data = QueryDict(mutable=True)
                        if producer_code:
                            post_data['producer_code'] = producer_code
                        if producer_color_name:
                            post_data['producer_color_name'] = producer_color_name
                        if main_color_id:
                            post_data['main_color_id'] = str(main_color_id)
                        
                        request = factory.post(
                            f'/admin/matterhorn1/product/assign-mapping/{product_id}/{mpd_product_id}/',
                            post_data
                        )

                        # Wywołaj metodę assign_mapping bezpośrednio
                        admin_instance = ProductAdmin(Product, None)
                        response = admin_instance.assign_mapping(request, product_id, mpd_product_id)
                        
                        # Sprawdź czy się powiodło
                        import json
                        if hasattr(response, 'content'):
                            response_data = json.loads(response.content)
                            if response_data.get('success'):
                                logger.info(f"✓ Przypisano produkt do MPD ID: {mpd_product_id}")
                                return True
                    except Exception as e:
                        logger.error(f"Błąd podczas przypisywania produktu: {e}")
                        import traceback
                        traceback.print_exc()
                        return False

            logger.info("Nie znaleziono produktu z pokryciem 100%")
            return False

        except Exception as e:
            logger.error(f"Błąd podczas obsługi scenariusza ASSIGN: {e}")
            import traceback
            traceback.print_exc()
            return False

    def create_mpd_product(self, product_id: int, product_data: Dict, brand_id: int = None, brand_name: str = None) -> Dict:
        """
        SCENARIUSZ CREATE: Tworzy nowy produkt w MPD.

        Args:
            product_id: ID produktu w matterhorn1
            product_data: Słownik z danymi produktu (name, description, etc.)
            brand_id: ID marki (opcjonalne)
            brand_name: Nazwa marki (opcjonalne)

        Returns:
            Słownik z wynikiem (success, mpd_product_id, error_message)
        """
        try:
            logger.info(f"Tworzenie produktu MPD dla produktu {product_id}")

            # Pobierz oryginalną nazwę produktu
            original_name = product_data.get('name', '')
            self._original_product_name = original_name

            # KROK 1: Ulepsz nazwę produktu
            enhanced_name = self.enhance_product_name(original_name)
            logger.info(f"Ulepszona nazwa: {enhanced_name}")

            # KROK 2: Ulepsz opis produktu
            original_description = product_data.get('description', '')
            enhanced_description = self.enhance_product_description(original_description)
            logger.info(f"Ulepszony opis (długość: {len(enhanced_description)})")

            # KROK 3: Utwórz krótki opis
            short_description = self.create_short_description(enhanced_description)
            logger.info(f"Krótki opis (długość: {len(short_description)})")

            # KROK 4: Wyciągnij atrybuty z opisu
            attribute_ids = self.extract_attributes_from_description(enhanced_description)
            logger.info(f"Wyodrębniono {len(attribute_ids)} atrybutów: {attribute_ids}")

            # KROK 5: Pobierz markę
            brand_name_final = brand_name or product_data.get('brand_name', '')
            if not brand_name_final and brand_id:
                try:
                    brand = Brand.objects.get(brand_id=brand_id)
                    brand_name_final = brand.name
                except Brand.DoesNotExist:
                    pass

            # KROK 6: Grupa rozmiarowa (domyślnie "bielizna" dla kostiumów)
            size_category = "bielizna"

            # KROK 7: Główny kolor
            color_name = product_data.get('color', '')
            main_color_id = None
            if color_name:
                main_color_id = self.get_main_color_id(color_name)

            # KROK 8: Kolor producenta
            producer_color_name = self.extract_color_from_name(original_name)
            if producer_color_name and brand_id and brand_name:
                # Sprawdź czy kolor istnieje w bazie
                try:
                    color_obj = ProducerColor.objects.get(
                        brand_id=brand_id,
                        color_name=producer_color_name
                    )
                    color_obj.usage_count += 1
                    color_obj.save(update_fields=['usage_count', 'updated_at'])
                except ProducerColor.DoesNotExist:
                    ProducerColor.objects.create(
                        brand_id=brand_id,
                        brand_name=brand_name,
                        color_name=producer_color_name
                    )

            # KROK 9: Kod producenta
            producer_code = self.extract_producer_code_from_name(original_name)

            # KROK 10: Series name (placeholder - puste)
            series_name = ""

            # KROK 11: Ścieżka produktu (domyślnie "5" dla Dwuczęściowe)
            path_ids = ["5"]

            # KROK 12: Jednostka (domyślnie "0" dla szt.)
            unit_id = 0

            # KROK 13: Materiały (skład)
            size_table_html = product_data.get('size_table_html', '')
            fabric_data = self.extract_fabric_materials(size_table_html)

            # Przygotuj dane dla MPD
            mpd_product_data = {
                'name': enhanced_name,
                'description': enhanced_description,
                'short_description': short_description,
                'brand_name': brand_name_final,
                'size_category': size_category,
                'main_color_id': main_color_id,
                'producer_color_name': producer_color_name,
                'producer_code': producer_code,
                'series_name': series_name,
                'unit_id': unit_id,
                'visibility': False,
                'attributes': [str(aid) for aid in attribute_ids],  # Konwertuj na stringi
                'paths': path_ids,
                'fabric': fabric_data
            }

            # Przygotuj dane dla Matterhorn
            matterhorn_data = {
                'product_id': product_id
            }

            # Użyj Saga Pattern do utworzenia produktu
            logger.info(f"Wysyłanie danych do Saga - MPD: {mpd_product_data}")
            saga_result = SagaService.create_product_with_mapping(
                matterhorn_data, mpd_product_data
            )

            if saga_result.status.value != 'completed':
                error_msg = f"Saga failed: {saga_result.error}"
                logger.error(error_msg)
                return {
                    'success': False,
                    'mpd_product_id': None,
                    'error_message': error_msg
                }

            # Pobierz mpd_product_id z wyniku Sagi
            mpd_product_id = None
            for step in saga_result.steps:
                if step.name == 'create_mpd_product' and step.result:
                    mpd_product_id = step.result.get('mpd_product_id')
                    break

            if not mpd_product_id:
                return {
                    'success': False,
                    'mpd_product_id': None,
                    'error_message': 'Nie udało się pobrać ID produktu MPD'
                }

            logger.info(f"✅ Utworzono produkt MPD z ID: {mpd_product_id}")

            return {
                'success': True,
                'mpd_product_id': mpd_product_id,
                'error_message': None
            }

        except Exception as e:
            logger.error(f"Błąd podczas tworzenia produktu MPD: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'mpd_product_id': None,
                'error_message': str(e)
            }

