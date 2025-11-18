"""
Moduł do automatyzacji przeglądarki używając Playwright
"""
import logging
import asyncio
from typing import Dict, List, Optional, Any
from playwright.async_api import async_playwright, Browser, Page, BrowserContext
from django.utils import timezone

logger = logging.getLogger(__name__)


class BrowserAutomation:
    """Klasa do zarządzania automatyzacją przeglądarki"""

    def __init__(self, headless: bool = True, browser_type: str = 'chromium'):
        """
        Inicjalizuje BrowserAutomation

        Args:
            headless: Czy uruchomić przeglądarkę w trybie headless
            browser_type: Typ przeglądarki ('chromium', 'firefox', 'webkit')
        """
        self.headless = headless
        self.browser_type = browser_type
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.playwright = None

    async def start(self):
        """Uruchamia przeglądarkę i tworzy kontekst"""
        try:
            self.playwright = await async_playwright().start()

            if self.browser_type == 'chromium':
                self.browser = await self.playwright.chromium.launch(headless=self.headless)
            elif self.browser_type == 'firefox':
                self.browser = await self.playwright.firefox.launch(headless=self.headless)
            elif self.browser_type == 'webkit':
                self.browser = await self.playwright.webkit.launch(headless=self.headless)
            else:
                raise ValueError(
                    f'Nieobsługiwany typ przeglądarki: {self.browser_type}')

            # Utwórz kontekst z domyślnymi ustawieniami
            self.context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )

            # Utwórz nową stronę
            self.page = await self.context.new_page()

            logger.info(f'Przeglądarka {self.browser_type} uruchomiona')

        except Exception as e:
            logger.error(f'Błąd podczas uruchamiania przeglądarki: {str(e)}')
            raise

    async def stop(self):
        """Zatrzymuje przeglądarkę i zwalnia zasoby"""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()

            logger.info('Przeglądarka zatrzymana')

        except Exception as e:
            logger.error(f'Błąd podczas zatrzymywania przeglądarki: {str(e)}')

    async def navigate(self, url: str, wait_until: str = 'load', timeout: int = 30000):
        """Nawiguje do podanego URL"""
        try:
            if not self.page:
                raise RuntimeError(
                    'Strona nie została utworzona. Wywołaj start() najpierw.')

            await self.page.goto(url, wait_until=wait_until, timeout=timeout)
            logger.info(f'Nawigacja do: {url}')

            return {
                'url': url,
                'final_url': self.page.url,
                'title': await self.page.title(),
                'timestamp': timezone.now().isoformat()
            }

        except Exception as e:
            logger.error(f'Błąd podczas nawigacji do {url}: {str(e)}')
            raise

    async def get_page_content(self, wait_for_selector: Optional[str] = None):
        """Pobiera zawartość strony"""
        try:
            if not self.page:
                raise RuntimeError('Strona nie została utworzona.')

            if wait_for_selector:
                await self.page.wait_for_selector(wait_for_selector, timeout=10000)

            content = await self.page.content()
            text = await self.page.inner_text('body')

            return {
                'html': content,
                'text': text[:5000],  # Ogranicz do 5000 znaków
                'url': self.page.url,
                'title': await self.page.title(),
                'timestamp': timezone.now().isoformat()
            }

        except Exception as e:
            logger.error(
                f'Błąd podczas pobierania zawartości strony: {str(e)}')
            raise

    async def click(self, selector: str, timeout: int = 10000):
        """Klikniecie w element"""
        try:
            if not self.page:
                raise RuntimeError('Strona nie została utworzona.')

            await self.page.click(selector, timeout=timeout)
            logger.info(f'Kliknięcie w element: {selector}')

            return {
                'action': 'click',
                'selector': selector,
                'success': True,
                'timestamp': timezone.now().isoformat()
            }

        except Exception as e:
            logger.error(f'Błąd podczas kliknięcia w {selector}: {str(e)}')
            raise

    async def fill(self, selector: str, value: str, timeout: int = 10000):
        """Wypełnia pole formularza"""
        try:
            if not self.page:
                raise RuntimeError('Strona nie została utworzona.')

            await self.page.fill(selector, value, timeout=timeout)
            logger.info(f'Wypełnienie pola {selector}')

            return {
                'action': 'fill',
                'selector': selector,
                'value': value,
                'success': True,
                'timestamp': timezone.now().isoformat()
            }

        except Exception as e:
            logger.error(f'Błąd podczas wypełniania {selector}: {str(e)}')
            raise

    async def fill_form(self, fields: List[Dict[str, str]], timeout: int = 10000):
        """Wypełnia formularz z wieloma polami"""
        try:
            if not self.page:
                raise RuntimeError('Strona nie została utworzona.')

            results = []
            for field in fields:
                selector = field.get('selector')
                value = field.get('value')

                if selector and value:
                    await self.page.fill(selector, value, timeout=timeout)
                    results.append({
                        'selector': selector,
                        'success': True
                    })

            logger.info(f'Wypełniono formularz: {len(fields)} pól')

            return {
                'action': 'fill_form',
                'fields_filled': len(results),
                'results': results,
                'timestamp': timezone.now().isoformat()
            }

        except Exception as e:
            logger.error(f'Błąd podczas wypełniania formularza: {str(e)}')
            raise

    async def wait_for(self, selector: Optional[str] = None, text: Optional[str] = None, timeout: int = 10000):
        """Czeka na element lub tekst"""
        try:
            if not self.page:
                raise RuntimeError('Strona nie została utworzona.')

            if selector:
                await self.page.wait_for_selector(selector, timeout=timeout)
                logger.info(f'Element pojawił się: {selector}')
            elif text:
                await self.page.wait_for_selector(f'text={text}', timeout=timeout)
                logger.info(f'Tekst pojawił się: {text}')
            else:
                await self.page.wait_for_timeout(timeout)

            return {
                'action': 'wait_for',
                'selector': selector,
                'text': text,
                'success': True,
                'timestamp': timezone.now().isoformat()
            }

        except Exception as e:
            logger.error(f'Błąd podczas oczekiwania: {str(e)}')
            raise

    async def take_screenshot(self, full_page: bool = False, path: Optional[str] = None):
        """Robię zrzut ekranu"""
        try:
            if not self.page:
                raise RuntimeError('Strona nie została utworzona.')

            await self.page.screenshot(full_page=full_page, path=path)

            return {
                'action': 'screenshot',
                'full_page': full_page,
                'path': path,
                'success': True,
                'timestamp': timezone.now().isoformat()
            }

        except Exception as e:
            logger.error(f'Błąd podczas robienia zrzutu ekranu: {str(e)}')
            raise

    async def evaluate(self, expression: str):
        """Wykonuje JavaScript na stronie"""
        try:
            if not self.page:
                raise RuntimeError('Strona nie została utworzona.')

            result = await self.page.evaluate(expression)

            return {
                'action': 'evaluate',
                'expression': expression,
                'result': result,
                'timestamp': timezone.now().isoformat()
            }

        except Exception as e:
            logger.error(f'Błąd podczas wykonywania JavaScript: {str(e)}')
            raise

    async def get_text(self, selector: str):
        """Pobiera tekst z elementu"""
        try:
            if not self.page:
                raise RuntimeError('Strona nie została utworzona.')

            text = await self.page.inner_text(selector)

            return {
                'action': 'get_text',
                'selector': selector,
                'text': text,
                'timestamp': timezone.now().isoformat()
            }

        except Exception as e:
            logger.error(
                f'Błąd podczas pobierania tekstu z {selector}: {str(e)}')
            raise

    async def execute_actions(self, actions: List[Dict[str, Any]]):
        """Wykonuje listę akcji z obsługą pętli dla produktów"""
        results = []

        # Znajdź indeks akcji która zaczyna sekwencję produktu
        # To jest akcja "Pobierz informacje o produkcie" - szukamy po komentarzu lub po unikalnym selektorze
        product_loop_start_index = None
        for i, action in enumerate(actions):
            # Szukamy akcji evaluate która pobiera informacje o produkcie
            if action.get('type') == 'evaluate':
                expr = action.get('expression', '')
                # Sprawdź czy to akcja która pobiera informacje o produkcie (zawiera "suggested_products")
                if 'suggested_products' in expr and 'productId' in expr:
                    product_loop_start_index = i
                    logger.info(
                        f'✅ Znaleziono początek pętli produktu na indeksie {i} (akcja: Pobierz informacje o produkcie)')
                    break

        # Jeśli nie znaleziono, użyj indeksu po kliknięciu pierwszego produktu (około akcja 20-25)
        if product_loop_start_index is None:
            # Szukamy akcji po kliknięciu pierwszego produktu z listy
            for i, action in enumerate(actions):
                if action.get('type') == 'click' and 'first-child' in str(action.get('selector', '')):
                    # Następna akcja po wait_for to początek sekwencji produktu
                    # +2 bo jest click, potem wait_for, potem evaluate
                    product_loop_start_index = i + 2
                    logger.info(
                        f'Znaleziono początek pętli produktu (po kliknięciu pierwszego) na indeksie {product_loop_start_index}')
                    break

        if product_loop_start_index is None:
            logger.warning(
                'Nie znaleziono początku pętli produktu - automatyzacja będzie działać bez pętli')
            product_loop_start_index = 0

        i = 0
        max_iterations = 1000  # Zabezpieczenie przed nieskończoną pętlą
        iteration = 0

        while i < len(actions) and iteration < max_iterations:
            iteration += 1
            action = actions[i]
            action_type = action.get('type')

            try:
                if action_type == 'navigate':
                    result = await self.navigate(
                        action.get('url'),
                        wait_until=action.get('wait_until', 'load'),
                        timeout=action.get('timeout', 30000)
                    )
                elif action_type == 'click':
                    result = await self.click(
                        action.get('selector'),
                        timeout=action.get('timeout', 10000)
                    )
                elif action_type == 'fill':
                    result = await self.fill(
                        action.get('selector'),
                        action.get('value'),
                        timeout=action.get('timeout', 10000)
                    )
                elif action_type == 'fill_form':
                    result = await self.fill_form(
                        action.get('fields', []),
                        timeout=action.get('timeout', 10000)
                    )
                elif action_type == 'wait_for':
                    # Sprawdź czy poprzednia akcja była evaluate i zwróciła skip_wait: true
                    should_skip = False
                    if i > 0 and results:
                        prev_result = results[-1]
                        if prev_result.get('action') == 'evaluate':
                            prev_result_data = prev_result.get('result', {})
                            # Użyj tej samej logiki co w linii 360 - wyciągnij evaluate_result
                            prev_eval_result = prev_result_data.get('result') if isinstance(
                                prev_result_data, dict) and 'result' in prev_result_data else prev_result_data

                            # Sprawdź czy wynik zawiera skip_wait
                            if isinstance(prev_eval_result, dict):
                                skip_wait = prev_eval_result.get(
                                    'skip_wait', False)
                                if skip_wait:
                                    should_skip = True
                                    reason = prev_eval_result.get(
                                        'reason', 'unknown')
                                    logger.info(
                                        f'Pomijam wait_for - poprzednia akcja zwróciła skip_wait: true ({reason})')

                    if should_skip:
                        result = {
                            'action': 'wait_for',
                            'selector': action.get('selector'),
                            'text': action.get('text'),
                            'success': True,
                            'skipped': True,
                            'reason': 'skip_wait_from_previous_action',
                            'timestamp': timezone.now().isoformat()
                        }
                    else:
                        result = await self.wait_for(
                            selector=action.get('selector'),
                            text=action.get('text'),
                            timeout=action.get('timeout', 10000)
                        )
                elif action_type == 'screenshot':
                    result = await self.take_screenshot(
                        full_page=action.get('full_page', False),
                        path=action.get('path')
                    )
                elif action_type == 'evaluate':
                    result = await self.evaluate(action.get('expression'))

                    # Sprawdź czy wynik zawiera żądanie edycji przez AI
                    # Uwaga: evaluate zwraca dict z kluczem 'result' zawierającym właściwy wynik
                    evaluate_result = result.get('result') if isinstance(
                        result, dict) and 'result' in result else result

                    logger.info(
                        f'BrowserAutomation: Sprawdzam wynik akcji evaluate...')
                    logger.info(
                        f'BrowserAutomation: Typ wyniku: {type(evaluate_result)}')
                    logger.info(
                        f'BrowserAutomation: Czy dict: {isinstance(evaluate_result, dict)}')
                    if isinstance(evaluate_result, dict):
                        logger.info(
                            f'BrowserAutomation: ai_request_prepared: {evaluate_result.get("ai_request_prepared")}')

                    if isinstance(evaluate_result, dict) and evaluate_result.get('ai_request_prepared'):
                        logger.info(
                            'BrowserAutomation: Wykryto żądanie edycji przez AI!')
                        # Wywołaj funkcję Python do edycji przez AI
                        from web_agent.brand_automation import edit_description_with_ai, generate_short_description_from_description

                        original_text = evaluate_result.get(
                            'original_text', '')
                        product_name = evaluate_result.get('product_name', '')
                        brand_name = evaluate_result.get('brand_name', '')

                        logger.info(
                            f'BrowserAutomation: Dane do edycji - długość tekstu: {len(original_text)}, produkt: {product_name}, marka: {brand_name}')

                        if original_text:
                            logger.info(
                                'BrowserAutomation: Wywołuję edit_description_with_ai...')
                            # Edytuj opis przez AI
                            edited_description = edit_description_with_ai(
                                original_description=original_text,
                                product_name=product_name,
                                brand_name=brand_name
                            )
                            logger.info(
                                f'BrowserAutomation: Opis zedytowany, długość: {len(edited_description)}')

                            logger.info(
                                'BrowserAutomation: Wywołuję generate_short_description_from_description...')
                            # Generuj krótki opis jako streszczenie
                            short_description = generate_short_description_from_description(
                                edited_description)
                            logger.info(
                                f'BrowserAutomation: Krótki opis wygenerowany, długość: {len(short_description)}')

                            logger.info(
                                'BrowserAutomation: Zapisuję wyniki z powrotem do przeglądarki...')
                            # Zapisz zedytowany opis z powrotem do przeglądarki
                            await self.page.evaluate(f'''
                                window.__editedDescription = {repr(edited_description)};
                                window.__shortDescription = {repr(short_description)};
                            ''')

                            evaluate_result['ai_edit_completed'] = True
                            evaluate_result['edited_description'] = edited_description
                            evaluate_result['short_description'] = short_description
                            result['result'] = evaluate_result
                            logger.info(
                                f'BrowserAutomation: Opis zedytowany przez AI: {len(edited_description)} znaków')
                            logger.info(
                                f'BrowserAutomation: Krótki opis wygenerowany: {len(short_description)} znaków')
                        else:
                            logger.warning(
                                'BrowserAutomation: Brak oryginalnego tekstu do edycji')
                    else:
                        logger.debug(
                            f'BrowserAutomation: Brak żądania AI - ai_request_prepared: {evaluate_result.get("ai_request_prepared") if isinstance(evaluate_result, dict) else "N/A"}')

                    # Sprawdź czy wynik zawiera żądanie wyciągnięcia atrybutów przez AI
                    if isinstance(evaluate_result, dict) and evaluate_result.get('ai_extraction_prepared'):
                        logger.info(
                            'BrowserAutomation: Wykryto żądanie wyciągnięcia atrybutów przez AI!')
                        # Wywołaj funkcję Python do wyciągnięcia atrybutów
                        from web_agent.brand_automation import extract_attributes_from_description

                        description = evaluate_result.get('description', '')
                        available_attributes = evaluate_result.get(
                            'available_attributes', [])
                        product_name = evaluate_result.get('product_name', '')
                        brand_name = evaluate_result.get('brand_name', '')

                        logger.info(
                            f'BrowserAutomation: Dane do wyciągnięcia atrybutów - długość opisu: {len(description)}, dostępnych atrybutów: {len(available_attributes)}, produkt: {product_name}, marka: {brand_name}')

                        if description and available_attributes:
                            logger.info(
                                'BrowserAutomation: Wywołuję extract_attributes_from_description...')
                            # Wyciągnij atrybuty przez AI
                            selected_attribute_ids = extract_attributes_from_description(
                                description=description,
                                available_attributes=available_attributes,
                                product_name=product_name,
                                brand_name=brand_name
                            )
                            logger.info(
                                f'BrowserAutomation: Wybrane atrybuty: {selected_attribute_ids}')

                            logger.info(
                                'BrowserAutomation: Zapisuję wybrane atrybuty z powrotem do przeglądarki...')
                            # Zapisz wybrane atrybuty z powrotem do przeglądarki
                            await self.page.evaluate(f'''
                                window.__selectedAttributeIds = {selected_attribute_ids};
                            ''')

                            evaluate_result['ai_extraction_completed'] = True
                            evaluate_result['selected_attribute_ids'] = selected_attribute_ids
                            result['result'] = evaluate_result
                            logger.info(
                                f'BrowserAutomation: Wybrano {len(selected_attribute_ids)} atrybutów przez AI')
                        else:
                            logger.warning(
                                'BrowserAutomation: Brak opisu lub dostępnych atrybutów do wyciągnięcia')
                    else:
                        logger.debug(
                            f'BrowserAutomation: Brak żądania wyciągnięcia atrybutów - ai_extraction_prepared: {evaluate_result.get("ai_extraction_prepared") if isinstance(evaluate_result, dict) else "N/A"}')

                    # Sprawdź czy wynik zawiera żądanie parsowania materiałów z size_table_txt
                    if isinstance(evaluate_result, dict) and evaluate_result.get('composition_prepared') and evaluate_result.get('needs_python_parsing'):
                        logger.info(
                            'BrowserAutomation: Wykryto żądanie parsowania materiałów z size_table_txt!')
                        # Wywołaj funkcję Python do parsowania materiałów
                        from web_agent.brand_automation import parse_materials_from_size_table_txt
                        from matterhorn1.models import Product

                        product_id = evaluate_result.get('product_id')

                        logger.info(
                            f'BrowserAutomation: Pobieranie size_table_txt dla product_id: {product_id}')

                        if product_id:
                            try:
                                from asgiref.sync import sync_to_async

                                # Funkcja synchroniczna do pobrania produktu
                                # Najpierw próbuj size_table_txt, potem size_table_html, na końcu size_table
                                def get_product_size_table_data(prod_id):
                                    try:
                                        product = Product.objects.get(
                                            id=prod_id)
                                        if hasattr(product, 'details'):
                                            # Najpierw spróbuj size_table_txt
                                            if product.details.size_table_txt:
                                                return product.details.size_table_txt, 'txt'
                                            # Jeśli nie ma txt, spróbuj size_table_html
                                            if product.details.size_table_html:
                                                return product.details.size_table_html, 'html'
                                            # Jeśli nie ma html, spróbuj size_table
                                            if product.details.size_table:
                                                return product.details.size_table, 'html'
                                        return None, None
                                    except Product.DoesNotExist:
                                        return None, None

                                # Wywołaj synchroniczną funkcję w kontekście asynchronicznym
                                size_table_data, data_type = await sync_to_async(get_product_size_table_data)(product_id)

                                # Jeśli mamy dane HTML, wyciągnij tekst ze składu
                                if size_table_data and data_type == 'html':
                                    import re as re_module
                                    # Wyciągnij skład z HTML (np. "<strong>Elastan</strong> 20% <br> <strong>Poliamid</strong> 80%")
                                    html_matches = re_module.findall(
                                        r'<strong>([^<]+)</strong>\s*(\d+(?:[.,]\d+)?)\s*%',
                                        size_table_data,
                                        re_module.IGNORECASE
                                    )
                                    if html_matches:
                                        # Przekształć na format tekstowy: "Elastan 20 % Poliamid 80 %"
                                        size_table_txt = ' '.join(
                                            [f'{mat.strip()} {perc} %' for mat, perc in html_matches])
                                    else:
                                        size_table_txt = size_table_data
                                else:
                                    size_table_txt = size_table_data

                                logger.info(
                                    f'BrowserAutomation: size_table_txt: {size_table_txt[:100] if size_table_txt else "None"}...')

                                if size_table_txt:
                                    logger.info(
                                        'BrowserAutomation: Wywołuję parse_materials_from_size_table_txt...')
                                    # Parsuj materiały (funkcja jest synchroniczna, ale nie używa Django ORM)
                                    materials = parse_materials_from_size_table_txt(
                                        size_table_txt)
                                    logger.info(
                                        f'BrowserAutomation: Wyciągnięto {len(materials)} materiałów')

                                    logger.info(
                                        'BrowserAutomation: Zapisuję sparsowane materiały z powrotem do przeglądarki...')
                                    # Zapisz sparsowane materiały z powrotem do przeglądarki
                                    await self.page.evaluate(f'''
                                        window.__parsedMaterials = {materials};
                                    ''')

                                    evaluate_result['materials_parsed'] = True
                                    evaluate_result['materials_count'] = len(
                                        materials)
                                    evaluate_result['materials'] = materials
                                    result['result'] = evaluate_result
                                    logger.info(
                                        f'BrowserAutomation: Sparsowano {len(materials)} materiałów z size_table_txt')
                                else:
                                    logger.warning(
                                        'BrowserAutomation: Brak size_table_txt dla produktu')
                                    await self.page.evaluate('window.__parsedMaterials = [];')
                                    evaluate_result['materials_parsed'] = False
                                    evaluate_result['materials_count'] = 0
                                    evaluate_result['reason'] = 'no_size_table_txt'
                                    result['result'] = evaluate_result
                            except Exception as e:
                                logger.error(
                                    f'BrowserAutomation: Błąd podczas parsowania materiałów: {str(e)}')
                                await self.page.evaluate('window.__parsedMaterials = [];')
                                evaluate_result['materials_parsed'] = False
                                evaluate_result['reason'] = f'error: {str(e)}'
                                result['result'] = evaluate_result
                        else:
                            logger.warning(
                                'BrowserAutomation: Brak product_id do parsowania materiałów')
                            await self.page.evaluate('window.__parsedMaterials = [];')
                            evaluate_result['materials_parsed'] = False
                            evaluate_result['reason'] = 'no_product_id'
                            result['result'] = evaluate_result
                    else:
                        logger.debug(
                            f'BrowserAutomation: Brak żądania parsowania materiałów - composition_prepared: {evaluate_result.get("composition_prepared") if isinstance(evaluate_result, dict) else "N/A"}')
                elif action_type == 'get_text':
                    result = await self.get_text(action.get('selector'))
                elif action_type == 'wait':
                    seconds = action.get('seconds', 1)
                    await asyncio.sleep(seconds)
                    result = {
                        'action': 'wait',
                        'seconds': seconds,
                        'timestamp': timezone.now().isoformat()
                    }
                else:
                    result = {'error': f'Nieznany typ akcji: {action_type}'}

                results.append({
                    'action': action_type,
                    'result': result,
                    'success': 'error' not in result,
                    'index': i
                })

                # Sprawdź czy ostatnia akcja zwróciła informację o kontynuacji pętli
                if action_type == 'evaluate' and isinstance(result, dict):
                    evaluate_result = result.get('result') if isinstance(
                        result, dict) and 'result' in result else result
                    if isinstance(evaluate_result, dict):
                        # Sprawdź czy automatyzacja powinna kontynuować (przejść do następnego produktu)
                        automation_completed = evaluate_result.get(
                            'automation_completed', False)
                        can_continue = evaluate_result.get(
                            'can_continue', False)
                        next_product_found = evaluate_result.get(
                            'next_product_found', False)

                        # Jeśli osiągnięto limit lub nie ma więcej produktów, zakończ
                        if automation_completed:
                            logger.info(
                                f'Automatyzacja zakończona: {evaluate_result.get("reason", "unknown")}')
                            break

                        # Sprawdź również poprzednie akcje evaluate czy zwróciły next_product_found
                        # (może być że nawigacja była w poprzedniej akcji, a obecna tylko sprawdza status)
                        if not next_product_found and can_continue:
                            # Sprawdź poprzednie akcje evaluate
                            # Sprawdź ostatnie 5 akcji
                            for prev_result in reversed(results[-5:]):
                                if prev_result.get('action') == 'evaluate':
                                    prev_result_data = prev_result.get(
                                        'result', {})
                                    prev_eval_result = prev_result_data.get('result') if isinstance(
                                        prev_result_data, dict) and 'result' in prev_result_data else prev_result_data
                                    if isinstance(prev_eval_result, dict):
                                        prev_next_found = prev_eval_result.get(
                                            'next_product_found', False)
                                        if prev_next_found:
                                            next_product_found = True
                                            logger.info(
                                                'Znaleziono next_product_found w poprzedniej akcji')
                                            break

                        # Jeśli znaleziono następny produkt i możemy kontynuować, wróć do początku sekwencji produktu
                        if next_product_found and can_continue and i >= product_loop_start_index:
                            products_processed = evaluate_result.get(
                                "products_processed", 0)
                            max_products = evaluate_result.get(
                                "max_products", 10)
                            logger.info(
                                f'🔄 Przechodzę do następnego produktu - wracam do indeksu {product_loop_start_index} (obecny: {i}, products_processed: {products_processed}/{max_products})')
                            i = product_loop_start_index - 1  # -1 bo na końcu będzie i += 1
                            continue

                        # Jeśli can_continue jest True ale nie ma next_product_found, sprawdź czy to ostatnia akcja
                        # i czy powinniśmy wrócić do początku (np. po nawigacji do następnego produktu)
                        if can_continue and not automation_completed and i == len(actions) - 1:
                            # To ostatnia akcja i możemy kontynuować - sprawdź czy jesteśmy na stronie produktu
                            products_processed = evaluate_result.get(
                                "products_processed", 0)
                            max_products = evaluate_result.get(
                                "max_products", 10)
                            logger.info(
                                f'🔍 Ostatnia akcja z can_continue=True (products_processed: {products_processed}/{max_products}) - sprawdzam czy wrócić do początku pętli')
                            # Sprawdź w przeglądarce czy jesteśmy na stronie produktu
                            try:
                                page_check = await self.page.evaluate('''() => {
                                    const isProductPage = window.location.pathname.match(/\\/\\d+\\/change\\//);
                                    return { is_product_page: !!isProductPage, pathname: window.location.pathname };
                                }''')
                                if page_check.get('is_product_page'):
                                    logger.info(
                                        f'✅ Jesteśmy na stronie produktu ({page_check.get("pathname")}) - wracam do początku pętli (indeks {product_loop_start_index})')
                                    i = product_loop_start_index - 1
                                    continue
                                else:
                                    logger.info(
                                        f'⚠️ Nie jesteśmy na stronie produktu ({page_check.get("pathname")}) - nie wracam do pętli')
                            except Exception as e:
                                logger.warning(
                                    f'Błąd podczas sprawdzania strony: {str(e)}')

            except Exception as e:
                # Jeśli akcja jest opcjonalna, nie traktuj błędu jako krytyczny
                if action.get('optional', False):
                    results.append({
                        'action': action_type,
                        'error': str(e),
                        'success': False,
                        'skipped': True
                    })
                else:
                    results.append({
                        'action': action_type,
                        'error': str(e),
                        'success': False,
                        'index': i
                    })

            i += 1

        logger.info(
            f'Zakończono wykonanie akcji. Wykonano {iteration} iteracji, przetworzono {len(results)} akcji.')
        return results


# Funkcje pomocnicze dla synchronicznego użycia w Celery
def run_async(coro):
    """Uruchamia funkcję async w synchronicznym kontekście"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def scrape_with_browser(url: str, wait_for_selector: Optional[str] = None, headless: bool = True) -> Dict:
    """
    Scrapuje stronę używając przeglądarki (synchroniczna funkcja dla Celery)

    Args:
        url: URL do scrapowania
        wait_for_selector: Opcjonalny selektor CSS do oczekiwania
        headless: Czy uruchomić w trybie headless

    Returns:
        Słownik z zawartością strony
    """
    async def _scrape():
        automation = BrowserAutomation(headless=headless)
        try:
            await automation.start()
            await automation.navigate(url)
            content = await automation.get_page_content(wait_for_selector)
            return content
        finally:
            await automation.stop()

    return run_async(_scrape())


def execute_browser_actions(actions: List[Dict[str, Any]], headless: bool = True) -> List[Dict]:
    """
    Wykonuje listę akcji w przeglądarce (synchroniczna funkcja dla Celery)

    Args:
        actions: Lista akcji do wykonania
        headless: Czy uruchomić w trybie headless

    Returns:
        Lista wyników akcji
    """
    async def _execute():
        automation = BrowserAutomation(headless=headless)
        try:
            await automation.start()
            results = await automation.execute_actions(actions)
            return results
        finally:
            await automation.stop()

    return run_async(_execute())
