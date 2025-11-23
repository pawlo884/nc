"""
Moduł do automatyzacji dla każdej marki (brand) osobno
"""
import os
import re
import logging
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
from openai import OpenAI

logger = logging.getLogger(__name__)

# Słownik mapowania kolorów dla marki Marko (polski -> angielski)
MARKO_COLOR_MAPPING = {
    'żółty': 'Yellow',
    'yellow': 'Yellow',
    'żółta': 'Yellow',
    'żółte': 'Yellow',
    'czerwony': 'Red',
    'red': 'Red',
    'czerwona': 'Red',
    'czerwone': 'Red',
    'czarny': 'Black',
    'black': 'Black',
    'czarna': 'Black',
    'czarne': 'Black',
    'biały': 'White',
    'white': 'White',
    'biała': 'White',
    'białe': 'White',
    'różowy': 'Pink',
    'pink': 'Pink',
    'różowa': 'Pink',
    'różowe': 'Pink',
    'light pink': 'Light Pink',
    'jasnoróżowy': 'Light Pink',
    'niebieski': 'Blue',
    'blue': 'Blue',
    'niebieska': 'Blue',
    'niebieskie': 'Blue',
    'zielony': 'Green',
    'green': 'Green',
    'zielona': 'Green',
    'zielone': 'Green',
    'pomarańczowy': 'Orange',
    'orange': 'Orange',
    'pomarańczowa': 'Orange',
    'pomarańczowe': 'Orange',
    'fioletowy': 'Violet',
    'violet': 'Violet',
    'fioletowa': 'Violet',
    'fioletowe': 'Violet',
    'coral': 'Coral',
    'koralowy': 'Coral',
    'koralowa': 'Coral',
    'koralowe': 'Coral',
    'mięta': 'Mint',
    'mint': 'Mint',
    'morski': 'Navy',
    'navy': 'Navy',
    'mocca': 'Mocca',
    'mokka': 'Mocca',
}


def extract_producer_color_from_name(product_name: str, brand_name: str = 'Marko') -> Optional[str]:
    """
    Wyciąga kolor producenta z nazwy produktu (pełna nazwa koloru, np. "Red Ferrari")

    Używa wzorców z brand_patterns.py

    Args:
        product_name: Nazwa produktu (np. "Kostium dwuczęściowy Model Aitana M-813 (2) Red Ferrari - Marko")
        brand_name: Nazwa marki (domyślnie 'Marko')

    Returns:
        Pełna nazwa koloru producenta (np. "Red Ferrari", "Light Pink", "Violet/Red") lub None
    """
    return extract_producer_color(product_name, brand_name)


def extract_producer_code_from_name(product_name: str, brand_name: str = 'Marko') -> Optional[str]:
    """
    Wyciąga kod producenta z nazwy produktu (format M-XXX)

    Używa wzorców z brand_patterns.py

    Args:
        product_name: Nazwa produktu (np. "Kostium dwuczęściowy Model Hasanna M-809 (3) Yellow - Marko")
        brand_name: Nazwa marki (domyślnie 'Marko')

    Returns:
        Kod producenta (np. "M-809") lub None
    """
    return extract_producer_code(product_name, brand_name)


def edit_description_with_ai(original_description: str, product_name: str = '', brand_name: str = '') -> str:
    """
    Edytuje opis produktu używając OpenAI API

    Args:
        original_description: Oryginalny opis produktu
        product_name: Nazwa produktu (dla kontekstu)
        brand_name: Nazwa marki (dla kontekstu)

    Returns:
        Zedytowany opis produktu
    """
    if not original_description:
        return ''

    try:
        logger.info(f'edit_description_with_ai: Rozpoczynam edycję opisu')
        logger.info(
            f'edit_description_with_ai: Długość oryginalnego opisu: {len(original_description)}')
        logger.info(
            f'edit_description_with_ai: Nazwa produktu: {product_name}')
        logger.info(f'edit_description_with_ai: Marka: {brand_name}')

        # Pobierz klucz API z .env.dev
        load_dotenv('.env.dev')
        api_key = os.getenv('OPENAI_API_KEY')

        logger.info(
            f'edit_description_with_ai: API key obecny: {bool(api_key)}')
        logger.info(
            f'edit_description_with_ai: API key długość: {len(api_key) if api_key else 0}')

        if not api_key:
            logger.warning(
                'edit_description_with_ai: OPENAI_API_KEY nie znaleziony w .env.dev - zwracam oryginalny opis')
            logger.warning(
                'OPENAI_API_KEY nie znaleziony w .env.dev - zwracam oryginalny opis')
            return original_description.strip()

        logger.info('edit_description_with_ai: Inicjalizuję klienta OpenAI...')
        # Inicjalizuj klient OpenAI
        client = OpenAI(api_key=api_key)
        logger.info('edit_description_with_ai: Klient OpenAI zainicjalizowany')

        # Przygotuj prompt do edycji opisu
        prompt = f"""Edytuj i ulepsz opis produktu, zachowując wszystkie ważne informacje techniczne i funkcjonalne. 
Opis powinien być profesjonalny, atrakcyjny dla klienta i dobrze sformatowany.

Nazwa produktu: {product_name}
Marka: {brand_name}

Oryginalny opis:
{original_description}

Zwróć tylko zedytowany opis, bez dodatkowych komentarzy."""

        logger.info(
            'edit_description_with_ai: Wywołuję OpenAI API z modelem gpt-5.1...')
        # Wywołaj OpenAI API z modelem GPT-5.1
        response = client.chat.completions.create(
            model="gpt-5.1",  # Używamy GPT-5.1
            messages=[
                {"role": "system", "content": "Jesteś ekspertem od pisania profesjonalnych opisów produktów. Edytujesz opisy produktów, zachowując wszystkie ważne informacje techniczne i funkcjonalne."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_completion_tokens=2000  # GPT-5.1 używa max_completion_tokens zamiast max_tokens
        )

        logger.info(
            f'edit_description_with_ai: Odpowiedź otrzymana z OpenAI API')
        logger.info(
            f'edit_description_with_ai: Liczba wyborów: {len(response.choices)}')

        edited_description = response.choices[0].message.content.strip()

        logger.info(
            f'edit_description_with_ai: Opis zedytowany: {len(original_description)} -> {len(edited_description)} znaków')
        logger.info(
            f'edit_description_with_ai: Pierwsze 100 znaków: {edited_description[:100]}...')

        # Loguj informacje o edycji
        logger.info(
            f'Opis zedytowany przez OpenAI: {len(original_description)} -> {len(edited_description)} znaków')

        return edited_description

    except Exception as e:
        # W przypadku błędu zwróć oryginalny opis
        logger.error(
            f'edit_description_with_ai: Błąd podczas edycji opisu przez OpenAI: {str(e)}')
        logger.error(
            f'edit_description_with_ai: Typ błędu: {type(e).__name__}')
        import traceback
        logger.error(
            f'edit_description_with_ai: Traceback: {traceback.format_exc()}')
        return original_description.strip()


def extract_attributes_from_description(
    description: str,
    available_attributes: List[Dict[str, Any]],
    product_name: str = '',
    brand_name: str = ''
) -> List[int]:
    """
    Wyciąga pasujące atrybuty z opisu produktu używając AI.

    Args:
        description: Opis produktu
        available_attributes: Lista dostępnych atrybutów w formacie [{'id': int, 'name': str}, ...]
        product_name: Nazwa produktu (opcjonalne)
        brand_name: Nazwa marki (opcjonalne)

    Returns:
        Lista ID atrybutów do zaznaczenia
    """
    if not description or not available_attributes:
        logger.warning(
            'extract_attributes_from_description: Brak opisu lub dostępnych atrybutów')
        return []

    try:
        # Załaduj klucz API OpenAI z .env.dev
        env_file = os.path.join(os.path.dirname(
            os.path.dirname(__file__)), '.env.dev')
        load_dotenv(env_file)
        api_key = os.getenv('OPENAI_API_KEY')

        if not api_key:
            logger.error(
                'extract_attributes_from_description: Brak OPENAI_API_KEY w .env.dev')
            return []

        # Przygotuj listę dostępnych atrybutów jako tekst
        attributes_list = '\n'.join(
            [f"- {attr['id']}: {attr['name']}" for attr in available_attributes])

        # Przygotuj prompt do wyciągnięcia atrybutów
        prompt = f"""Przeanalizuj opis produktu i wybierz WSZYSTKIE pasujące atrybuty z dostępnej listy.

Dostępne atrybuty:
{attributes_list}

Opis produktu:
{description}

{'Nazwa produktu: ' + product_name if product_name else ''}
{'Marka: ' + brand_name if brand_name else ''}

Zadanie:
1. Przeanalizuj opis produktu semantycznie i szczegółowo
2. Znajdź WSZYSTKIE atrybuty z listy, które pasują do opisu - zarówno te bezpośrednio wspomniane, jak i te sugerowane przez kontekst
3. Zwróć TYLKO numery ID pasujących atrybutów oddzielone przecinkami (np. "1, 5, 12, 29")
4. Jeśli żaden atrybut nie pasuje, zwróć pustą linię
5. Bądź dokładny i wybierz wszystkie pasujące atrybuty, np.:
   - Jeśli opis wspomina o "fiszbinach" lub "fiszbiny" → wybierz "na fiszbinach"
   - Jeśli opis wspomina o "usztywnianych miseczkach" → wybierz "usztywniane miseczki"
   - Jeśli opis wspomina o "niski krój" lub "niski stan" → wybierz "niski stan"
   - Jeśli opis wspomina o "wiązanie na szyi" → wybierz "wiązane na szyi"
   - Jeśli opis wspomina o "regulowane" → wybierz "regulowane"
   - Jeśli opis wspomina o "gładkie" → wybierz "gładkie" lub "gładkie miseczki"
   - I tak dalej - wybierz wszystkie pasujące atrybuty!

WAŻNE: Wybierz wszystkie atrybuty, które pasują do opisu, nawet jeśli są tylko sugerowane przez kontekst. 
Bądź hojny w wyborze - lepiej wybrać więcej pasujących atrybutów niż za mało.

Zwróć tylko numery ID oddzielone przecinkami, bez dodatkowych komentarzy."""

        # Inicjalizuj klient OpenAI
        client = OpenAI(api_key=api_key)

        # Wywołaj OpenAI API z modelem GPT-5.1
        response = client.chat.completions.create(
            model="gpt-5.1",
            messages=[
                {"role": "system", "content": "Jesteś ekspertem w analizie tekstów produktowych i wyciąganiu atrybutów. Zwracasz tylko numery ID atrybutów oddzielone przecinkami."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_completion_tokens=200
        )

        # Pobierz odpowiedź
        result_text = response.choices[0].message.content.strip()
        logger.info(
            f'extract_attributes_from_description: Odpowiedź AI: {result_text}')

        # Parsuj odpowiedź - wyciągnij numery ID
        attribute_ids = []
        if result_text:
            # Usuń wszystkie znaki niebędące cyframi i przecinkami
            cleaned = re.sub(r'[^\d,]', '', result_text)
            # Podziel po przecinkach i konwertuj na int
            for attr_id_str in cleaned.split(','):
                attr_id_str = attr_id_str.strip()
                if attr_id_str:
                    try:
                        attr_id = int(attr_id_str)
                        # Sprawdź czy atrybut istnieje w dostępnych
                        if any(attr['id'] == attr_id for attr in available_attributes):
                            attribute_ids.append(attr_id)
                    except ValueError:
                        continue

        logger.info(
            f'extract_attributes_from_description: Wybrane atrybuty: {attribute_ids}')
        return attribute_ids

    except Exception as e:
        logger.error(
            f'extract_attributes_from_description: Błąd podczas wyciągania atrybutów: {e}', exc_info=True)
        return []


def generate_short_description_from_description(description: str, max_length: int = 200) -> str:
    """
    Generuje krótki opis jako streszczenie z długiego opisu używając OpenAI API

    Args:
        description: Długi opis produktu
        max_length: Maksymalna długość krótkiego opisu

    Returns:
        Krótki opis (streszczenie)
    """
    if not description:
        return ''

    try:
        # Pobierz klucz API z .env.dev
        load_dotenv('.env.dev')
        api_key = os.getenv('OPENAI_API_KEY')

        if not api_key:
            logger.warning(
                'OPENAI_API_KEY nie znaleziony w .env.dev - używam prostego skrócenia')
            # Fallback do prostego skrócenia
            description_clean = description.strip()
            if len(description_clean) <= max_length:
                return description_clean

            truncated = description_clean[:max_length]
            last_period = truncated.rfind('.')
            last_space = truncated.rfind(' ')

            if last_period > max_length * 0.7:
                return truncated[:last_period + 1]
            elif last_space > max_length * 0.7:
                return truncated[:last_space] + '...'

            return truncated + '...'

        # Inicjalizuj klient OpenAI
        client = OpenAI(api_key=api_key)

        # Przygotuj prompt do generowania streszczenia
        prompt = f"""Stwórz krótkie, atrakcyjne streszczenie opisu produktu. 
Streszczenie powinno zawierać najważniejsze informacje i być maksymalnie {max_length} znaków długie.

WAŻNE: Pomiń wszystkie informacje o rozmiarze, wskazówkach dotyczących rozmiaru, zaleceniach dotyczących wyboru rozmiaru (np. "wybierz rozmiar większy niż zwykle", "model wypada mniejszy", itp.).

Długi opis:
{description}

Zwróć tylko streszczenie, bez dodatkowych komentarzy i bez informacji o rozmiarze."""

        # Wywołaj OpenAI API z modelem GPT-5.1
        response = client.chat.completions.create(
            model="gpt-5.1",  # Używamy GPT-5.1
            messages=[
                {"role": "system", "content": "Jesteś ekspertem od tworzenia krótkich, atrakcyjnych streszczeń opisów produktów. Tworzysz zwięzłe streszczenia zawierające najważniejsze informacje."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_completion_tokens=300  # GPT-5.1 używa max_completion_tokens zamiast max_tokens
        )

        short_description = response.choices[0].message.content.strip()

        # Upewnij się, że nie przekracza max_length
        if len(short_description) > max_length:
            short_description = short_description[:max_length].rsplit(' ', 1)[
                0] + '...'

        # Loguj informacje o generowaniu
        logger.info(
            f'Krótki opis wygenerowany przez OpenAI: {len(short_description)} znaków')

        return short_description

    except Exception as e:
        # W przypadku błędu użyj prostego skrócenia
        logger.error(
            f'Błąd podczas generowania krótkiego opisu przez OpenAI: {str(e)}')

        # Fallback do prostego skrócenia
        description_clean = description.strip()
        if len(description_clean) <= max_length:
            return description_clean

        truncated = description_clean[:max_length]
        last_period = truncated.rfind('.')
        last_space = truncated.rfind(' ')

        if last_period > max_length * 0.7:
            return truncated[:last_period + 1]
        elif last_space > max_length * 0.7:
            return truncated[:last_space] + '...'

        return truncated + '...'


def parse_materials_from_size_table_txt(size_table_txt: str) -> List[Dict[str, Any]]:
    """
    Parsuje size_table_txt i wyciąga materiały z procentami

    Args:
        size_table_txt: Tekst z size_table_txt (np. "Skład: 80% poliester, 20% elastan")

    Returns:
        Lista słowników z materiałami: [{'name': 'poliester', 'percentage': 80}, ...]
    """
    if not size_table_txt:
        return []

    materials = []

    # Usuń "Skład:" lub podobne prefiksy
    text = size_table_txt.strip()
    text = re.sub(r'^skład\s*:?\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'^composition\s*:?\s*', '', text, flags=re.IGNORECASE)

    # Znajdź sekcję ze składem (przed tabelą rozmiarów)
    # Szukaj wzorców typu "Skład:", "Composition:" lub procentów na początku
    # Jeśli znajdziemy "Rozmiar", "Size", "cm", "obwód" - to prawdopodobnie tabela rozmiarów, więc przetnij tekst przed nią
    size_markers = ['rozmiar', 'size', 'obwód',
                    'cm', 'bioder', 'biustem', 'biuście']
    for marker in size_markers:
        marker_pos = text.lower().find(marker)
        if marker_pos > 0:
            # Sprawdź czy przed markerem jest skład (czyli marker jest w tabeli rozmiarów)
            text_before = text[:marker_pos].strip()
            if re.search(r'\d+\s*%', text_before, re.IGNORECASE):
                # Przed markerem jest skład, więc przetnij tekst
                text = text_before
                break

    # Jeśli tekst jest bardzo długi i zawiera wiele linii/tabulacji, może to być tabela rozmiarów
    # Szukaj tylko w pierwszych liniach (do 500 znaków lub do pierwszej linii z "Rozmiar")
    lines = text.split('\n')
    composition_lines = []
    for line in lines:
        line_lower = line.lower().strip()
        # Jeśli linia zawiera markery tabeli rozmiarów, przestań zbierać linie
        if any(marker in line_lower for marker in size_markers) and len(line) > 20:
            break
        # Jeśli linia zawiera procenty lub nazwy materiałów, dodaj ją
        if re.search(r'\d+\s*%', line, re.IGNORECASE) or any(mat in line_lower for mat in ['poliester', 'elastan', 'poliamid', 'bawełna', 'cotton', 'polyester', 'elastane', 'polyamide']):
            composition_lines.append(line)

    # Jeśli znaleźliśmy linie ze składem, użyj ich zamiast całego tekstu
    if composition_lines:
        text = ' '.join(composition_lines)

    # Najpierw spróbuj wzorca dla formatu "Elastan 20 % Poliamid 80 %" (materiał X % materiał Y %)
    # Ten wzorzec powinien być pierwszy, bo jest bardziej specyficzny
    pattern_material_percent = r'([A-Za-ząćęłńóśźżĄĆĘŁŃÓŚŹŻ]+(?:\s+[A-Za-ząćęłńóśźżĄĆĘŁŃÓŚŹŻ]+)*?)\s+(\d+(?:[.,]\d+)?)\s*%'
    matches_material_percent = re.findall(
        pattern_material_percent, text, re.IGNORECASE)

    # Jeśli znaleziono materiały w formacie "materiał X %", użyj ich
    if matches_material_percent:
        for match in matches_material_percent:
            material_name = match[0].strip()
            percentage_str = match[1].replace(',', '.')

            # Odrzuć jeśli nazwa materiału zawiera markery tabeli rozmiarów
            material_name_lower = material_name.lower()
            if any(marker in material_name_lower for marker in size_markers):
                continue

            # Odrzuć jeśli nazwa jest zbyt długa (prawdopodobnie tabela rozmiarów)
            if len(material_name) > 50:
                continue

            # Odrzuć jeśli nazwa zawiera wiele cyfr (prawdopodobnie tabela rozmiarów)
            if len(re.findall(r'\d+', material_name)) > 0:
                continue

            try:
                percentage = float(percentage_str)
                if percentage > 0 and percentage <= 100:
                    materials.append({
                        'name': material_name,
                        'percentage': int(percentage)
                    })
            except ValueError:
                continue

    # Jeśli nie znaleziono materiałów w formacie "materiał X %", spróbuj innych wzorców
    if not materials:
        # Wzorzec 1: "80% poliester, 20% elastan"
        pattern1 = r'(\d+(?:[.,]\d+)?)\s*%\s*([^,\d]+?)(?=\s*\d+\s*%|,|$)'
        matches1 = re.findall(pattern1, text, re.IGNORECASE)

        for match in matches1:
            percentage_str = match[0].replace(',', '.')
            material_name = match[1].strip()

            # Odrzuć jeśli nazwa materiału zawiera markery tabeli rozmiarów
            material_name_lower = material_name.lower()
            if any(marker in material_name_lower for marker in size_markers):
                continue

            # Odrzuć jeśli nazwa jest zbyt długa (prawdopodobnie tabela rozmiarów)
            if len(material_name) > 50:
                continue

            # Odrzuć jeśli nazwa zawiera wiele cyfr lub jednostek (prawdopodobnie tabela rozmiarów)
            if len(re.findall(r'\d+', material_name)) > 2:
                continue

            try:
                percentage = float(percentage_str)
                if percentage > 0 and percentage <= 100:
                    materials.append({
                        'name': material_name,
                        # Zaokrąglij do liczby całkowitej
                        'percentage': int(percentage)
                    })
            except ValueError:
                continue

    # Wzorzec 2: "poliester 80%, elastan 20%" (z przecinkami)
    if not materials:
        pattern2 = r'([^,\d]+?)\s+(\d+(?:[.,]\d+)?)\s*%'
        matches2 = re.findall(pattern2, text, re.IGNORECASE)

        for match in matches2:
            material_name = match[0].strip()
            percentage_str = match[1].replace(',', '.')

            # Odrzuć jeśli nazwa materiału zawiera markery tabeli rozmiarów
            material_name_lower = material_name.lower()
            if any(marker in material_name_lower for marker in size_markers):
                continue

            # Odrzuć jeśli nazwa jest zbyt długa (prawdopodobnie tabela rozmiarów)
            if len(material_name) > 50:
                continue

            # Odrzuć jeśli nazwa zawiera wiele cyfr lub jednostek (prawdopodobnie tabela rozmiarów)
            if len(re.findall(r'\d+', material_name)) > 2:
                continue

            try:
                percentage = float(percentage_str)
                if percentage > 0 and percentage <= 100:
                    materials.append({
                        'name': material_name,
                        'percentage': int(percentage)
                    })
            except ValueError:
                continue

    # Jeśli nie znaleziono wzorców, spróbuj prostszego parsowania
    if not materials:
        # Podziel po przecinku i szukaj procentów
        parts = re.split(r'[,;]', text)
        for part in parts:
            part = part.strip()
            # Szukaj "X% materiał" lub "materiał X%"
            match = re.search(r'(\d+(?:[.,]\d+)?)\s*%', part, re.IGNORECASE)
            if match:
                percentage_str = match.group(1).replace(',', '.')
                material_name = part.replace(match.group(0), '').strip()
                material_name = re.sub(
                    r'^\d+\s*%\s*', '', material_name, flags=re.IGNORECASE)
                material_name = re.sub(
                    r'\s*\d+\s*%$', '', material_name, flags=re.IGNORECASE)
                material_name = material_name.strip()

                # Odrzuć jeśli nazwa materiału zawiera markery tabeli rozmiarów
                material_name_lower = material_name.lower()
                if any(marker in material_name_lower for marker in size_markers):
                    continue

                # Odrzuć jeśli nazwa jest zbyt długa (prawdopodobnie tabela rozmiarów)
                if len(material_name) > 50:
                    continue

                # Odrzuć jeśli nazwa zawiera wiele cyfr lub jednostek (prawdopodobnie tabela rozmiarów)
                if len(re.findall(r'\d+', material_name)) > 2:
                    continue

                if material_name:
                    try:
                        percentage = float(percentage_str)
                        if percentage > 0 and percentage <= 100:
                            materials.append({
                                'name': material_name,
                                'percentage': int(percentage)
                            })
                    except ValueError:
                        continue

    logger.info(
        f'parse_materials_from_size_table_txt: Wyciągnięto {len(materials)} materiałów z size_table_txt')
    for mat in materials:
        logger.debug(f'  - {mat["name"]}: {mat["percentage"]}%')

    return materials


def format_product_name_for_mpd(product_name: str, brand_name: str = 'Marko') -> str:
    """
    Formatuje nazwę produktu dla MPD zgodnie z szablonem marki

    Używa wzorców z brand_patterns.py

    Dla Marko:
    - Wejście: "Kostium dwuczęściowy Kostium kąpielowy Model Aitana M-813 (1) Red - Marko"
    - Wyjście: "Kostium kąpielowy Aitana"

    Args:
        product_name: Oryginalna nazwa produktu
        brand_name: Nazwa marki (domyślnie 'Marko')

    Returns:
        Sformatowana nazwa produktu dla MPD
    """
    return format_product_name(product_name, brand_name)


def get_all_brands(using='matterhorn1') -> List[Dict[str, Any]]:
    """
    Pobiera wszystkie marki z bazy danych

    Args:
        using: Nazwa bazy danych (domyślnie: 'matterhorn1')

    Returns:
        Lista słowników z danymi mark: [{'id': 1, 'name': 'Axami'}, ...]
    """
    from matterhorn1.models import Brand

    brands = Brand.objects.using(using).all().values(
        'id', 'name').order_by('name')
    return list(brands)


def get_all_categories(using='matterhorn1') -> List[Dict[str, Any]]:
    """
    Pobiera wszystkie kategorie z bazy danych

    Args:
        using: Nazwa bazy danych (domyślnie: 'matterhorn1')

    Returns:
        Lista słowników z danymi kategorii: [{'id': 1, 'name': 'Biustonosze'}, ...]
    """
    from matterhorn1.models import Category

    categories = Category.objects.using(using).all().values(
        'id', 'name', 'path').order_by('name')
    return list(categories)


def build_filter_url(
    base_url: str,
    brand_id: int = None,
    category_id: int = None,
    active: bool = None,
    is_mapped: bool = None
) -> str:
    """
    Buduje URL z filtrami dla Django Admin

    Args:
        base_url: Bazowy URL
        brand_id: ID marki (opcjonalne)
        category_id: ID kategorii (opcjonalne)
        active: Status aktywności (True/False, opcjonalne)
        is_mapped: Status mapowania (True/False, opcjonalne)

    Returns:
        URL z parametrami filtrowania
    """
    from urllib.parse import urlencode

    params = {}

    if brand_id is not None:
        params['brand__id__exact'] = brand_id

    if category_id is not None:
        params['category__id__exact'] = category_id

    if active is not None:
        # Django Admin używa 1/0 dla BooleanField
        params['active__exact'] = 1 if active else 0

    if is_mapped is not None:
        # Django Admin używa 1/0 dla BooleanField
        params['is_mapped__exact'] = 1 if is_mapped else 0

    products_url = f'{base_url}/admin/matterhorn1/product/'
    if params:
        products_url += '?' + urlencode(params)

    return products_url


def get_brand_filter_config(
    brand_id: int,
    brand_name: str = None,
    category_id: int = None,
    category_name: str = None,
    active: bool = True,
    is_mapped: bool = False,
    base_url: str = 'http://localhost:8080',
    username: str = None,
    password: str = None,
    env_file: str = '.env.dev',
    max_products: int = 10
) -> Dict[str, Any]:
    """
    Zwraca konfigurację zadania automatyzacji dla konkretnej marki z opcjonalnymi filtrami

    Args:
        brand_id: ID marki w bazie danych
        brand_name: Nazwa marki (do wyświetlenia, opcjonalne)
        category_id: ID kategorii (opcjonalne)
        category_name: Nazwa kategorii (do wyświetlenia, opcjonalne)
        active: Filtrowanie po statusie aktywności (domyślnie: True)
        is_mapped: Filtrowanie po statusie mapowania (domyślnie: False - tylko niezmapowane)
        base_url: URL aplikacji Django
        username: Nazwa użytkownika (opcjonalne)
        password: Hasło (opcjonalne)
        env_file: Ścieżka do pliku .env

    Returns:
        Słownik z konfiguracją zadania automatyzacji
    """
    # Pobierz dane logowania jeśli nie podano
    if username is None or password is None:
        load_dotenv(env_file)
        username = username or os.getenv('DJANGO_ADMIN_USERNAME', '')
        password = password or os.getenv('DJANGO_ADMIN_PASSWORD', '')

    # URL do produktów z filtrami
    products_url = build_filter_url(
        base_url=base_url,
        brand_id=brand_id,
        category_id=category_id,
        active=active,
        is_mapped=is_mapped
    )

    config = {
        'headless': False,
        'actions': [
            {
                'type': 'navigate',
                'url': base_url,
                'wait_until': 'load',
                'timeout': 30000
            },
            {
                'type': 'wait_for',
                'selector': 'a[href="/admin/"]',
                'timeout': 10000
            },
            {
                'type': 'click',
                'selector': 'a[href="/admin/"]',
                'timeout': 10000
            },
            {
                'type': 'wait_for',
                'selector': 'input[name="username"]',
                'timeout': 10000
            },
            {
                'type': 'fill',
                'selector': 'input[name="username"]',
                'value': username,
                'timeout': 10000
            },
            {
                'type': 'fill',
                'selector': 'input[name="password"]',
                'value': password,
                'timeout': 10000
            },
            {
                'type': 'click',
                'selector': 'input[type="submit"], button[type="submit"]',
                'timeout': 10000
            },
            {
                'type': 'wait_for',
                'selector': '.user-tools, a[href*="/admin/matterhorn1"]',
                'timeout': 15000
            },
            # Przejdź bezpośrednio do produktów z filtrem po brand
            {
                'type': 'navigate',
                'url': products_url,
                'wait_until': 'load',
                'timeout': 30000
            },
            {
                'type': 'wait_for',
                'selector': 'table thead, .changelist-search',
                'timeout': 15000
            },
            # Sprawdź czy filtry są aktywne
            {
                'type': 'wait_for',
                'selector': 'table thead, .changelist-filters',
                'timeout': 10000
            },
            # Pobierz dane o produktach i filtrach
            {
                'type': 'evaluate',
                'expression': '''(() => {
                    const url = new URL(window.location.href);
                    return {
                        title: document.title,
                        url: window.location.href,
                        rowCount: document.querySelectorAll("table tbody tr").length,
                        filters: {
                            brandId: url.searchParams.get('brand__id__exact') || null,
                            categoryId: url.searchParams.get('category__id__exact') || null,
                            active: url.searchParams.get('active__exact') || null,
                            isMapped: url.searchParams.get('is_mapped__exact') || null
                        },
                        brandFilterText: document.querySelector('select[name="brand__id__exact"]')?.options[document.querySelector('select[name="brand__id__exact"]')?.selectedIndex]?.text || '',
                        categoryFilterText: document.querySelector('select[name="category__id__exact"]')?.options[document.querySelector('select[name="category__id__exact"]')?.selectedIndex]?.text || '',
                        activeFilterText: document.querySelector('select[name="active__exact"]')?.options[document.querySelector('select[name="active__exact"]')?.selectedIndex]?.text || '',
                        isMappedFilterText: document.querySelector('select[name="is_mapped__exact"]')?.options[document.querySelector('select[name="is_mapped__exact"]')?.selectedIndex]?.text || '',
                        currentPage: document.querySelector('.paginator .this-page')?.textContent || '1',
                        totalResults: document.querySelector('.paginator')?.textContent.match(/\\d+\\s+(?:produkt|product)/i)?.[0] || ''
                    };
                })()'''
            },
            # Screenshot
            {
                'type': 'screenshot',
                'full_page': True,
                'path': None
            },
            # Pobierz listę produktów (pierwsza strona)
            {
                'type': 'evaluate',
                'expression': '''(() => {
                    const rows = Array.from(document.querySelectorAll("table tbody tr"));
                    return rows.slice(0, 20).map(row => {
                        const cells = row.querySelectorAll("td");
                        const firstLink = row.querySelector("td a");
                        return {
                            product_uid: cells[1]?.textContent.trim() || '',
                            name: cells[2]?.textContent.trim() || '',
                            brand: cells[3]?.textContent.trim() || '',
                            link_href: firstLink?.href || ''
                        };
                    });
                })()'''
            },
            # Zapisz URL listingu do sessionStorage (do późniejszego powrotu)
            {
                'type': 'evaluate',
                'expression': f'''(() => {{
                    const currentUrl = window.location.href;
                    sessionStorage.setItem('changelist_url', currentUrl);
                    // Zainicjalizuj licznik przetworzonych produktów jeśli nie istnieje
                    if (!sessionStorage.getItem('products_processed')) {{
                        sessionStorage.setItem('products_processed', '0');
                    }}
                    return {{ 
                        changelist_url_saved: true, 
                        url: currentUrl,
                        max_products: {max_products},
                        products_processed: parseInt(sessionStorage.getItem('products_processed') || '0')
                    }};
                }})()'''
            },
            # Kliknij w pierwszy produkt z listy
            {
                'type': 'wait_for',
                'selector': 'table.changelist tbody tr, table#result_list tbody tr, table tbody tr',
                'timeout': 10000
            },
            {
                'type': 'click',
                'selector': 'table.changelist tbody tr:first-child td a, table#result_list tbody tr:first-child td a, table tbody tr:first-child td a',
                'timeout': 10000
            },
            # Poczekaj na załadowanie strony szczegółów produktu
            {
                'type': 'wait_for',
                'selector': '.form-row, fieldset, input[name="name"]',
                'timeout': 15000
            },
            # Sprawdź czy produkt został zmapowany po przeładowaniu strony (po kliknięciu "Przypisz")
            {
                'type': 'evaluate',
                'expression': '''(() => {
                    // Poczekaj chwilę na przeładowanie strony po kliknięciu "Przypisz"
                    // Sprawdź czy produkt jest zmapowany - różne sposoby sprawdzania
                    const isMappedInput = document.querySelector('input[name="is_mapped"]');
                    const isMappedValue = isMappedInput?.value === 'True' || isMappedInput?.checked === true;
                    const isMappedDisplay = document.querySelector('.field-is_mapped')?.textContent?.trim() === 'True' ||
                                          document.querySelector('.field-is_mapped img[alt="True"]') !== null;
                    const isMapped = isMappedValue || isMappedDisplay;
                    
                    // Sprawdź czy jest mapped_product_uid (produkt został zmapowany)
                    // 1. Sprawdź input field
                    const mappedProductUidInput = document.querySelector('input[name="mapped_product_uid"]');
                    const mappedProductUidFromInput = mappedProductUidInput?.value || '';
                    
                    // 2. Sprawdź sekcję "Mapowanie MPD" - znajdź fieldset i sprawdź wartość
                    let mappingFieldset = document.querySelector('#fieldset-0-3');
                    // Jeśli nie znaleziono po ID, szukaj po tekście nagłówka
                    if (!mappingFieldset) {
                        const fieldsets = document.querySelectorAll('fieldset');
                        for (const fs of fieldsets) {
                            const heading = fs.querySelector('h2.fieldset-heading, h2');
                            if (heading && heading.textContent.includes('Mapowanie MPD')) {
                                mappingFieldset = fs;
                                break;
                            }
                        }
                    }
                    let mappedProductUidFromFieldset = '';
                    if (mappingFieldset) {
                        // Szukaj wartości w sekcji - może być w input, div, lub jako tekst
                        const fieldsetInput = mappingFieldset.querySelector('input[name="mapped_product_uid"]');
                        const fieldsetDiv = mappingFieldset.querySelector('.field-mapped_product_uid');
                        const fieldsetText = mappingFieldset.textContent || '';
                        
                        if (fieldsetInput) {
                            mappedProductUidFromFieldset = fieldsetInput.value || '';
                        } else if (fieldsetDiv) {
                            mappedProductUidFromFieldset = fieldsetDiv.textContent.trim() || '';
                        } else {
                            // Spróbuj wyciągnąć wartość z tekstu sekcji (np. "Mapped product uid: 1234")
                            const uidMatch = fieldsetText.match(/mapped.*product.*uid[\\s:]*([0-9]+)/i);
                            if (uidMatch) {
                                mappedProductUidFromFieldset = uidMatch[1];
                            }
                        }
                    }
                    
                    // 3. Sprawdź czy wartość jest różna od "-" lub pustej
                    // Wyczyść wartość z fieldsetu - usuń tekst etykiety i sprawdź tylko wartość
                    let cleanFieldsetValue = '';
                    if (mappedProductUidFromFieldset) {
                        // Usuń tekst etykiety i zostaw tylko wartość (może być liczba lub "-")
                            const valueMatch = mappedProductUidFromFieldset.match(/Mapped product uid[:\\s]*([0-9]+|-)/i);
                        if (valueMatch) {
                            cleanFieldsetValue = valueMatch[1];
                        } else {
                            // Jeśli nie ma matcha, sprawdź czy jest liczba w tekście
                            const numberMatch = mappedProductUidFromFieldset.match(/(\\d+)/);
                            if (numberMatch) {
                                cleanFieldsetValue = numberMatch[1];
                            } else {
                                cleanFieldsetValue = mappedProductUidFromFieldset.trim();
                            }
                        }
                    }
                    
                    const hasMappedUid = (mappedProductUidFromInput && mappedProductUidFromInput.trim() !== '' && mappedProductUidFromInput.trim() !== '-') ||
                                       (cleanFieldsetValue && cleanFieldsetValue !== '' && cleanFieldsetValue !== '-' && /^\\d+$/.test(cleanFieldsetValue));
                    
                    // Sprawdź komunikat sukcesu
                    const statusMsg = document.getElementById('status-message');
                    const statusText = statusMsg ? statusMsg.textContent.trim() : '';
                    const hasSuccessMessage = statusText && (
                        statusText.toLowerCase().includes('przypisano') || 
                        statusText.toLowerCase().includes('zmapowano') ||
                        statusText.toLowerCase().includes('success') ||
                        statusText.toLowerCase().includes('sukces')
                    );
                    
                    // Produkt jest zmapowany jeśli:
                    // 1. isMapped jest true LUB
                    // 2. Jest mapped_product_uid (różny od "-" lub pustej) LUB
                    // 3. Jest komunikat sukcesu o mapowaniu
                    const productMapped = isMapped || hasMappedUid || hasSuccessMessage;
                    
                    if (productMapped) {
                        // Produkt został zmapowany - zwiększ licznik i przejdź do następnego
                        const productsProcessed = parseInt(sessionStorage.getItem('products_processed') || '0') + 1;
                        sessionStorage.setItem('products_processed', productsProcessed.toString());
                        
                        // Zapisz informację że produkt został zmapowany
                        window.__productMapped = true;
                        
                        return {
                            product_mapped: true,
                            products_processed: productsProcessed,
                            is_mapped: isMapped,
                            has_mapped_uid: hasMappedUid,
                            mapped_uid_input: mappedProductUidFromInput,
                            mapped_uid_fieldset: mappedProductUidFromFieldset,
                            has_success_message: hasSuccessMessage,
                            note: 'Produkt został zmapowany - przejdź do następnego produktu'
                        };
                    }
                    
                    return {
                        product_mapped: false,
                        is_mapped: isMapped,
                        has_mapped_uid: hasMappedUid,
                        mapped_uid_input: mappedProductUidFromInput,
                        mapped_uid_fieldset: mappedProductUidFromFieldset,
                        has_success_message: hasSuccessMessage,
                        note: 'Produkt nie jest jeszcze zmapowany'
                    };
                })()'''
            },
            # Jeśli produkt został zmapowany, wróć do listingu i przejdź do następnego
            {
                'type': 'evaluate',
                'expression': '''(() => {
                    const productMapped = window.__productMapped;
                    
                    if (productMapped) {
                        const changelistUrl = sessionStorage.getItem('changelist_url');
                        if (changelistUrl) {
                            console.log('Produkt został zmapowany - zwracam URL do nawigacji przez Playwright:', changelistUrl);
                            return {
                                navigating_to_changelist: true,
                                navigate_to_url: changelistUrl  // URL do nawigacji przez Playwright
                            };
                        }
                    }
                    
                    return {
                        navigating_to_changelist: false,
                        reason: !productMapped ? 'product_not_mapped' : 'no_changelist_url'
                    };
                })()'''
            },
            # Poczekaj na załadowanie listingu jeśli nawigowaliśmy
            {
                'type': 'wait_for',
                'selector': 'table.changelist tbody tr, table#result_list tbody tr, table tbody tr',
                'timeout': 15000,
                'optional': True
            },
            # Dodatkowe oczekiwanie po nawigacji do changelist
            {
                'type': 'wait',
                'seconds': 2
            },
            # Przejdź do następnego niezmapowanego produktu jeśli produkt został zmapowany
            {
                'type': 'evaluate',
                'expression': f'''(() => {{
                    const productMapped = window.__productMapped;
                    
                    if (!productMapped) {{
                        return {{
                            next_product_found: false,
                            reason: 'product_not_mapped_yet'
                        }};
                    }}
                    
                    // Sprawdź czy jesteśmy na liście produktów
                    const isChangelist = window.location.pathname.includes('/admin/matterhorn1/product/') && 
                                       !window.location.pathname.match(/\\/\\d+\\/change\\//);
                    
                    if (!isChangelist) {{
                        return {{ next_product_found: false, reason: 'not_on_changelist', current_path: window.location.pathname }};
                    }}
                    
                    // Sprawdź limit przetworzonych produktów
                    const productsProcessed = parseInt(sessionStorage.getItem('products_processed') || '0');
                    const maxProducts = {max_products};
                    
                    if (productsProcessed >= maxProducts) {{
                        return {{
                            next_product_found: false,
                            reason: 'max_products_reached',
                            products_processed: productsProcessed,
                            max_products: maxProducts,
                            message: `Osiągnięto limit ${{maxProducts}} produktów`
                        }};
                    }}
                    
                    // Znajdź pierwszy produkt z listy, który nie jest jeszcze zmapowany
                    // Użyj różnych selektorów dla kompatybilności
                    let rows = document.querySelectorAll('table#result_list tbody tr');
                    if (rows.length === 0) {{
                        rows = document.querySelectorAll('table.changelist tbody tr');
                    }}
                    if (rows.length === 0) {{
                        rows = document.querySelectorAll('table tbody tr');
                    }}
                    let nextProductLink = null;
                    
                    for (const row of rows) {{
                        const link = row.querySelector('td.field-name a');
                        const isMappedCell = row.querySelector('td.field-is_mapped');
                        const isMapped = isMappedCell?.textContent?.trim() === 'True' || 
                                        isMappedCell?.querySelector('img[alt="True"]') !== null;
                        
                        if (link && !isMapped) {{
                            nextProductLink = link.href;
                            console.log('Znaleziono następny niezmapowany produkt:', nextProductLink);
                            break;
                        }}
                    }}
                    
                    if (nextProductLink) {{
                        console.log('Przechodzę do następnego produktu - zwracam URL do nawigacji przez Playwright:', nextProductLink);
                        return {{
                            next_product_found: true,
                            next_product_url: nextProductLink,
                            navigate_to_url: nextProductLink,  // URL do nawigacji przez Playwright
                            products_processed: productsProcessed,
                            max_products: maxProducts
                        }};
                    }}
                    
                    return {{
                        next_product_found: false,
                        reason: 'no_unmapped_products',
                        total_rows: rows.length,
                        products_processed: productsProcessed
                    }};
                }})()'''
            },
            # Poczekaj na przeładowanie strony po nawigacji
            {
                'type': 'wait',
                'seconds': 3
            },
            # Poczekaj na załadowanie strony następnego produktu
            {
                'type': 'wait_for',
                'selector': '.form-row, fieldset, input[name="name"]',
                'timeout': 15000,
                'optional': True
            },
            # Pobierz informacje o produkcie i sprawdź suggested_products z tabeli HTML
            {
                'type': 'evaluate',
                'expression': '''(() => {
                    const url = new URL(window.location.href);
                    const productId = url.pathname.match(/\\/(\\d+)\\/change\\//)?.[1];
                    
                    // Pobierz dane produktu
                    const productName = document.querySelector('input[name="name"]')?.value || '';
                    const productUid = document.querySelector('input[name="product_uid"]')?.value || '';
                    const productColor = document.querySelector('input[name="color"]')?.value || '';
                    const isMapped = document.querySelector('input[name="is_mapped"]')?.checked || false;
                    
                    // WAŻNE: Sprawdź czy produkt jest już zmapowany PRZED dalszym przetwarzaniem
                    // Jeśli jest zmapowany, pomiń ten produkt i przejdź do następnego
                    // Sprawdź również mapped_product_uid - jeśli istnieje, produkt jest zmapowany
                    const mappedProductUid = document.querySelector('input[name="mapped_product_uid"]')?.value || '';
                    const hasMappedUid = mappedProductUid && mappedProductUid.trim() !== '' && mappedProductUid.trim() !== '-';
                    
                    // Sprawdź również w fieldset (może być wyświetlony inaczej)
                    const fieldsetText = document.querySelector('.field-mapped_product_uid')?.textContent || '';
                    const hasMappedUidInFieldset = fieldsetText && fieldsetText.trim() !== '' && fieldsetText.trim() !== '-';
                    
                    const isReallyMapped = isMapped || hasMappedUid || hasMappedUidInFieldset;
                    
                    console.log('=== SPRAWDZANIE CZY PRODUKT JEST ZMAPOWANY ===');
                    console.log('isMapped (checkbox):', isMapped);
                    console.log('mapped_product_uid (input):', mappedProductUid);
                    console.log('hasMappedUid:', hasMappedUid);
                    console.log('hasMappedUidInFieldset:', hasMappedUidInFieldset);
                    console.log('isReallyMapped:', isReallyMapped);
                    
                    if (isReallyMapped) {
                        console.log('✅ Produkt jest już zmapowany - pomijam i przechodzę do następnego');
                        
                        // Zwiększ licznik przetworzonych produktów (pomijamy ten, ale liczymy go jako przetworzony)
                        const productsProcessed = parseInt(sessionStorage.getItem('products_processed') || '0') + 1;
                        sessionStorage.setItem('products_processed', productsProcessed.toString());
                        
                        // Zwróć informację o potrzebie nawigacji do listy produktów
                        // NIE używamy window.location.href - zamiast tego zwracamy URL do nawigacji przez Playwright
                        const changelistUrl = sessionStorage.getItem('changelist_url');
                        if (changelistUrl) {
                            console.log('Produkt jest zmapowany - zwracam URL do nawigacji przez Playwright:', changelistUrl);
                            return {
                                product_id: productId,
                                product_name: productName,
                                is_mapped: true,
                                has_mapped_uid: hasMappedUid || hasMappedUidInFieldset,
                                skip: true,
                                reason: 'already_mapped',
                                message: 'Produkt jest już zmapowany - przechodzę do następnego',
                                can_continue: true,
                                next_product_found: true,  // Przechodzimy do następnego produktu
                                navigate_to_url: changelistUrl,  // URL do nawigacji przez Playwright
                                products_processed: productsProcessed
                            };
                        }
                        
                        // Jeśli nie ma changelist_url, zwróć informację że trzeba przejść do następnego
                        return {
                            product_id: productId,
                            product_name: productName,
                            is_mapped: true,
                            has_mapped_uid: hasMappedUid || hasMappedUidInFieldset,
                            skip: true,
                            reason: 'already_mapped',
                            message: 'Produkt jest już zmapowany - pomijam',
                            can_continue: true,
                            next_product_found: true  // Agent powinien przejść do następnego produktu
                        };
                    }
                    
                    console.log('❌ Produkt NIE jest zmapowany - przetwarzam dalej');
                    
                    // Pobierz suggested_products z tabeli HTML
                    const suggestedTable = document.querySelector('table tbody');
                    const suggestedProducts = [];
                    
                    if (suggestedTable) {
                        const rows = Array.from(suggestedTable.querySelectorAll('tr'));
                        rows.forEach((row, index) => {
                            const cells = row.querySelectorAll('td');
                            if (cells.length >= 4) {
                                // Kolumny: Nazwa, Marka, Podob., Pokrycie, Główny kolor, Kolor prod., Kod prod., Akcja
                                const nameCell = cells[0]?.textContent?.trim() || '';
                                const similarityCell = cells[2]?.textContent?.trim() || '0';
                                const coverageCell = cells[3]?.textContent?.trim() || '0';
                                
                                // Wyciągnij wartości procentowe (obsługa polskiego formatu z przecinkiem)
                                const similarity = parseFloat(similarityCell.replace('%', '').replace(',', '.')) || 0;
                                const coverage = parseFloat(coverageCell.replace('%', '').replace(',', '.')) || 0;
                                
                                // Pobierz mpd_id z przycisku
                                const assignBtn = row.querySelector('.assign-mapping-btn');
                                const mpdId = assignBtn?.getAttribute('data-mpd-id');
                                
                                if (mpdId) {
                                    suggestedProducts.push({
                                        index: index,
                                        mpd_id: mpdId,
                                        name: nameCell,
                                        similarity: similarity,
                                        coverage: coverage,
                                        is_100_percent: coverage === 100,  // Tylko coverage musi być 100%
                                        row_element: row
                                    });
                                }
                            }
                        });
                    }
                    
                    // Pobierz dostępne główne kolory
                    const mainColorSelect = document.querySelector('select[name="main_color_id"]');
                    const mainColorOptions = mainColorSelect ? Array.from(mainColorSelect.options).map(opt => ({
                        value: opt.value,
                        text: opt.text.trim()
                    })) : [];
                    
                    // Znajdź główny kolor pasujący do koloru produktu
                    let matchedMainColorId = null;
                    if (productColor && mainColorOptions.length > 0) {
                        const colorLower = productColor.toLowerCase();
                        const matched = mainColorOptions.find(opt => 
                            opt.text.toLowerCase().includes(colorLower) || 
                            colorLower.includes(opt.text.toLowerCase())
                        );
                        if (matched && matched.value) {
                            matchedMainColorId = matched.value;
                        }
                    }
                    
                    // Jeśli nie znaleziono dopasowania, użyj pierwszego dostępnego koloru
                    if (!matchedMainColorId && mainColorOptions.length > 0 && mainColorOptions[0].value) {
                        matchedMainColorId = mainColorOptions[0].value;
                    }
                    
                    // Wyciągnij kolor producenta z nazwy produktu (dla marki Marko)
                    const brandName = document.querySelector('select[name="brand"]')?.options[document.querySelector('select[name="brand"]')?.selectedIndex]?.text || '';
                    let producerColorFromName = null;
                    let producerCodeFromName = null;
                    
                    // Słownik mapowania kolorów dla Marko (polski -> angielski)
                    const markoColorMapping = {
                        'żółty': 'Yellow', 'yellow': 'Yellow', 'żółta': 'Yellow', 'żółte': 'Yellow',
                        'czerwony': 'Red', 'red': 'Red', 'czerwona': 'Red', 'czerwone': 'Red',
                        'czarny': 'Black', 'black': 'Black', 'czarna': 'Black', 'czarne': 'Black',
                        'biały': 'White', 'white': 'White', 'biała': 'White', 'białe': 'White',
                        'różowy': 'Pink', 'pink': 'Pink', 'różowa': 'Pink', 'różowe': 'Pink',
                        'light pink': 'Light Pink', 'jasnoróżowy': 'Light Pink',
                        'niebieski': 'Blue', 'blue': 'Blue', 'niebieska': 'Blue', 'niebieskie': 'Blue',
                        'zielony': 'Green', 'green': 'Green', 'zielona': 'Green', 'zielone': 'Green',
                        'pomarańczowy': 'Orange', 'orange': 'Orange', 'pomarańczowa': 'Orange', 'pomarańczowe': 'Orange',
                        'fioletowy': 'Violet', 'violet': 'Violet', 'fioletowa': 'Violet', 'fioletowe': 'Violet',
                        'coral': 'Coral', 'koralowy': 'Coral', 'koralowa': 'Coral', 'koralowe': 'Coral',
                        'mięta': 'Mint', 'mint': 'Mint', 'morski': 'Navy', 'navy': 'Navy',
                        'mocca': 'Mocca', 'mokka': 'Mocca'
                    };
                    
                    if (brandName.toLowerCase().includes('marko')) {
                        // Wyciągnij pełny kolor producenta z nazwy produktu
                        // Format: "... M-XXX (N) COLOR - Marko"
                        // Przykład: "Kostium dwuczęściowy Model Aitana M-813 (2) Red Ferrari - Marko"
                        // Wyciągamy wszystko między nawiasem z numerem a myślnikiem przed "Marko"
                        const colorPattern = /\\([^)]+\\)\\s+([^-]+?)\\s*-\\s*Marko/i;
                        const colorMatch = productName.match(colorPattern);
                        
                        if (colorMatch) {
                            producerColorFromName = colorMatch[1].trim();
                        } else {
                            // Alternatywny wzorzec: jeśli nie ma " - Marko" na końcu, szukaj po nawiasie
                            const colorPattern2 = /\\([^)]+\\)\\s+([A-Za-z/]+(?:\\s+[A-Za-z]+)*)/;
                            const colorMatch2 = productName.match(colorPattern2);
                            
                            if (colorMatch2) {
                                const colorPart = colorMatch2[1].trim();
                                // Sprawdź czy to nie jest kod (M-XXX)
                                if (!/^M-\\d+/.test(colorPart)) {
                                    producerColorFromName = colorPart;
                                }
                            }
                        }
                        
                        // Wyciągnij kod producenta (format M-XXX)
                        const codeMatch = productName.match(/M-(\\d{3})/);
                        if (codeMatch) {
                            producerCodeFromName = 'M-' + codeMatch[1];
                        }
                    }
                    
                    // Zapisz dane do użycia w następnych krokach
                    window.__productData = {
                        product_id: productId,
                        product_name: productName,
                        product_uid: productUid,
                        product_color: productColor,
                        is_mapped: isMapped,
                        suggested_products: suggestedProducts,
                        matched_main_color_id: matchedMainColorId,
                        main_color_options: mainColorOptions,
                        producer_color_from_name: producerColorFromName,
                        producer_code_from_name: producerCodeFromName,
                        brand_name: brandName
                    };
                    
                    return {
                        product_id: productId,
                        product_name: productName,
                        product_uid: productUid,
                        product_color: productColor,
                        is_mapped: isMapped,
                        suggested_count: suggestedProducts.length,
                        first_suggestion: suggestedProducts[0] || null,
                        should_assign: suggestedProducts[0]?.coverage === 100 || false,
                        matched_main_color_id: matchedMainColorId,
                        producer_color_from_name: producerColorFromName,
                        producer_code_from_name: producerCodeFromName
                    };
                })()'''
            },
            # Jeśli pierwszy suggested product ma 100% coverage (pokrycie), wypełnij pola i przypisz mapowanie
            {
                'type': 'evaluate',
                'expression': '''(() => {
                    const data = window.__productData || {};
                    const firstSuggestion = data.suggested_products?.[0];
                    
                    // Sprawdź czy produkt jest już zmapowany
                    const isMapped = document.querySelector('input[name="is_mapped"]')?.checked || false;
                    if (isMapped) {
                        return { action: 'skip', reason: 'already_mapped', should_click: false };
                    }
                    
                    // Sprawdź czy są suggested products
                    if (!firstSuggestion) {
                        return {
                            action: 'skip',
                            reason: 'no_suggestions',
                            should_click: false
                        };
                    }
                    
                    // Znajdź pierwszy wiersz tabeli suggested products
                    const suggestedTable = document.querySelector('.mpd-form table tbody');
                    if (!suggestedTable) {
                        return { action: 'skip', reason: 'no_table', should_click: false };
                    }
                    
                    const firstRow = suggestedTable.querySelector('tr:first-child');
                    if (!firstRow) {
                        return { action: 'skip', reason: 'no_rows', should_click: false };
                    }
                    
                    // Sprawdź wartości similarity i coverage bezpośrednio z tabeli
                    const cells = firstRow.querySelectorAll('td');
                    if (cells.length < 4) {
                        return { action: 'skip', reason: 'invalid_row', should_click: false };
                    }
                    
                    const similarityText = cells[2]?.textContent?.trim() || '0';
                    const coverageText = cells[3]?.textContent?.trim() || '0';
                    
                    // Parsuj coverage - usuń wszystkie znaki niebędące cyframi lub kropką/przecinkiem
                    const cleanCoverageText = coverageText.replace(/[^0-9.,]/g, '').replace(',', '.');
                    const coverage = parseFloat(cleanCoverageText) || 0;
                    
                    // Parsuj similarity podobnie
                    const cleanSimilarityText = similarityText.replace(/[^0-9.,]/g, '').replace(',', '.');
                    const similarity = parseFloat(cleanSimilarityText) || 0;
                    
                    console.log(`Coverage: "${coverageText}" -> ${coverage}%, Similarity: "${similarityText}" -> ${similarity}%`);
                    
                    // Sprawdź coverage - jeśli jest 100% (lub bardzo blisko 100%), przypisujemy istniejący produkt
                    // Jeśli coverage != 100%, produkt nie istnieje i trzeba go utworzyć
                    // Używamy >= 99.5 aby obsłużyć zaokrąglenia (np. 99.9% lub 100.0%)
                    const isCoverage100 = coverage >= 99.5;
                    
                    let action = 'assign';
                    if (!isCoverage100) {
                        action = 'create_new';
                        // Zapisz action do window.__productData
                        if (window.__productData) {
                            window.__productData.action = 'create_new';
                        }
                        console.log(`Coverage ${coverage}% < 100% - produkt nie istnieje, trzeba utworzyć`);
                        return {
                            action: 'create_new',
                            reason: `coverage=${coverage}% (produkt nie istnieje w MPD)`,
                            should_click: false,
                            needs_creation: true,
                            similarity: similarity,
                            coverage: coverage
                        };
                    }
                    
                    console.log(`Coverage ${coverage}% >= 99.5% - produkt istnieje, przypisujemy mapowanie`);
                    
                    // Zapisz action do window.__productData
                    if (window.__productData) {
                        window.__productData.action = 'assign';
                    }
                    
                    const mainColorSelect = firstRow.querySelector('.main-color-select');
                    const producerColorInput = firstRow.querySelector('.producer-color-input');
                    const producerCodeInput = firstRow.querySelector('.producer-code-input');
                    
                    // Wypełnij pola
                    let mainColorValue = null;
                    if (mainColorSelect && data.matched_main_color_id) {
                        mainColorSelect.value = data.matched_main_color_id;
                        mainColorSelect.dispatchEvent(new Event('change', { bubbles: true }));
                        mainColorValue = data.matched_main_color_id;
                    }
                    
                    // Wypełnij kolor producenta - użyj koloru z nazwy produktu, jeśli dostępny, w przeciwnym razie użyj koloru z pola
                    const producerColorValue = data.producer_color_from_name || data.product_color || '';
                    if (producerColorInput && producerColorValue) {
                        producerColorInput.value = producerColorValue;
                        producerColorInput.dispatchEvent(new Event('input', { bubbles: true }));
                    }
                    
                    // Wypełnij kod producenta - użyj kodu z nazwy produktu, jeśli dostępny, w przeciwnym razie użyj product_uid
                    const producerCodeValue = data.producer_code_from_name || data.product_uid || '';
                    if (producerCodeInput && producerCodeValue) {
                        producerCodeInput.value = producerCodeValue;
                        producerCodeInput.dispatchEvent(new Event('input', { bubbles: true }));
                    }
                    
                    // Sprawdź czy wszystkie pola są wypełnione (wartości muszą być niepuste)
                    const allFieldsFilled = !!(mainColorValue && producerColorValue && producerCodeValue);
                    
                    // Oznacz wiersz jako gotowy do przypisania tylko jeśli wszystkie pola są wypełnione
                    if (allFieldsFilled) {
                        firstRow.setAttribute('data-auto-assign', 'true');
                    }
                    
                    return {
                        action: allFieldsFilled ? 'assign' : 'skip',
                        mpd_id: firstSuggestion.mpd_id,
                        main_color_id: mainColorValue,
                        producer_color_name: producerColorValue,
                        producer_code: producerCodeValue,
                        fields_filled: allFieldsFilled,
                        should_click: allFieldsFilled,
                        similarity: similarity,
                        coverage: coverage,
                        missing_fields: {
                            main_color: !mainColorValue,
                            producer_color: !producerColorValue,
                            producer_code: !producerCodeValue
                        }
                    };
                })()'''
            },
            # Poczekaj chwilę na wypełnienie pól
            {
                'type': 'wait',
                'seconds': 1
            },
            # Sprawdź czy wszystkie pola są wypełnione i czy przycisk istnieje
            {
                'type': 'evaluate',
                'expression': '''(() => {
                    const firstRow = document.querySelector('.mpd-form table tbody tr:first-child');
                    if (!firstRow) {
                        return { can_click: false, reason: 'no_row' };
                    }
                    
                    const mainColorSelect = firstRow.querySelector('.main-color-select');
                    const producerColorInput = firstRow.querySelector('.producer-color-input');
                    const producerCodeInput = firstRow.querySelector('.producer-code-input');
                    const assignBtn = firstRow.querySelector('.assign-mapping-btn');
                    
                    const mainColorValue = mainColorSelect?.value || '';
                    const producerColorValue = producerColorInput?.value?.trim() || '';
                    const producerCodeValue = producerCodeInput?.value?.trim() || '';
                    
                    const allFieldsFilled = mainColorValue && producerColorValue && producerCodeValue;
                    
                    if (!assignBtn) {
                        return { can_click: false, reason: 'button_not_found' };
                    }
                    
                    return {
                        can_click: allFieldsFilled,
                        button_found: true,
                        button_text: assignBtn.textContent.trim(),
                        button_visible: assignBtn.offsetParent !== null,
                        mpd_id: assignBtn.getAttribute('data-mpd-id'),
                        fields_status: {
                            main_color: !!mainColorValue,
                            producer_color: !!producerColorValue,
                            producer_code: !!producerCodeValue
                        },
                        field_values: {
                            main_color: mainColorValue,
                            producer_color: producerColorValue,
                            producer_code: producerCodeValue
                        }
                    };
                })()'''
            },
            # Kliknij przycisk "Przypisz" tylko jeśli wszystkie pola są wypełnione
            {
                'type': 'evaluate',
                'expression': '''(() => {
                    const firstRow = document.querySelector('.mpd-form table tbody tr:first-child');
                    if (!firstRow) {
                        return { clicked: false, reason: 'no_row' };
                    }
                    
                    const mainColorSelect = firstRow.querySelector('.main-color-select');
                    const producerColorInput = firstRow.querySelector('.producer-color-input');
                    const producerCodeInput = firstRow.querySelector('.producer-code-input');
                    const assignBtn = firstRow.querySelector('.assign-mapping-btn');
                    
                    const mainColorValue = mainColorSelect?.value || '';
                    const producerColorValue = producerColorInput?.value?.trim() || '';
                    const producerCodeValue = producerCodeInput?.value?.trim() || '';
                    
                    const allFieldsFilled = mainColorValue && producerColorValue && producerCodeValue;
                    
                    if (!allFieldsFilled) {
                        return {
                            clicked: false,
                            reason: 'fields_not_filled',
                            missing_fields: {
                                main_color: !mainColorValue,
                                producer_color: !producerColorValue,
                                producer_code: !producerCodeValue
                            }
                        };
                    }
                    
                    if (!assignBtn) {
                        return { clicked: false, reason: 'button_not_found' };
                    }
                    
                    // Przewiń do przycisku
                    assignBtn.scrollIntoView({ behavior: 'instant', block: 'center' });
                    
                    // Kliknij przycisk używając dispatchEvent (omija problem z Debug Toolbar)
                    const clickEvent = new MouseEvent('click', {
                        bubbles: true,
                        cancelable: true,
                        view: window
                    });
                    assignBtn.dispatchEvent(clickEvent);
                    
                    return {
                        clicked: true,
                        mpd_id: assignBtn.getAttribute('data-mpd-id'),
                        button_text: assignBtn.textContent.trim()
                    };
                })()'''
            },
            # Poczekaj chwilę na wykonanie kliknięcia
            {
                'type': 'wait',
                'seconds': 1
            },
            # Poczekaj chwilę na odpowiedź z serwera
            {
                'type': 'wait',
                'seconds': 2
            },
            # Sprawdź czy pojawił się komunikat statusu
            {
                'type': 'evaluate',
                'expression': '''(() => {
                    const statusMsg = document.getElementById('status-message');
                    if (statusMsg) {
                        return {
                            has_message: true,
                            message: statusMsg.textContent.trim(),
                            is_visible: statusMsg.style.display !== 'none',
                            has_class: statusMsg.className.includes('success') || statusMsg.className.includes('error')
                        };
                    }
                    return { has_message: false };
                })()'''
            },
            # Sprawdź czy produkt został zmapowany (po przypisaniu) lub czy trzeba utworzyć nowy
            # UWAGA: NIE KLIKAMY przycisku "Utwórz produkt" przed wypełnieniem wszystkich pól formularza!
            {
                'type': 'evaluate',
                'expression': '''(() => {
                    const data = window.__productData || {};
                    const isMapped = document.querySelector('input[name="is_mapped"]')?.checked || false;
                    const createBtn = document.getElementById('create-mpd-product-btn');
                    
                    // Sprawdź coverage z pierwszego suggested product
                    const firstSuggestion = data.suggested_products?.[0];
                    const coverage = firstSuggestion?.coverage || 0;
                    const action = data.action || (coverage === 100 ? 'assign' : 'create_new');
                    
                    // UWAGA: Przycisk "Utwórz produkt" (createBtn) NIE POWINIEN być klikany tutaj!
                    // Najpierw musimy wypełnić wszystkie pola formularza (mpd_name, mpd_description, itp.)
                    // Dopiero po wypełnieniu wszystkich pól możemy kliknąć przycisk tworzenia produktu.
                    
                    // Zapisz aktualny stan do użycia w następnych krokach
                    window.__productStatus = {
                        is_mapped: isMapped,
                        needs_creation: action === 'create_new',
                        has_create_button: !!createBtn,
                        action: action,
                        coverage: coverage,
                        all_fields_filled: false  // Flaga: czy wszystkie pola są wypełnione
                    };
                    
                    return {
                        is_mapped: isMapped,
                        needs_creation: action === 'create_new',
                        has_create_button: !!createBtn,
                        action: action,
                        coverage: coverage,
                        note: 'Przycisk "Utwórz produkt" NIE będzie klikany przed wypełnieniem wszystkich pól'
                    };
                })()'''
            },
            # Jeśli coverage != 100%, przygotuj się do wypełniania pól formularza i sformatuj nazwę produktu
            {
                'type': 'evaluate',
                'expression': '''(() => {
                    const status = window.__productStatus || {};
                    const data = window.__productData || {};
                    
                    // Jeśli produkt nie istnieje (coverage != 100%), przygotuj dane do wypełnienia pól
                    if (status.needs_creation) {
                        // Pobierz dostępne pola formularza
                        const formFields = {
                            mpd_name: document.getElementById('mpd_name'),
                            mpd_description: document.getElementById('mpd_description'),
                            mpd_short_description: document.getElementById('mpd_short_description'),
                            mpd_brand: document.getElementById('mpd_brand'),
                            mpd_size_category: document.getElementById('mpd_size_category'),
                            main_color_id: document.getElementById('main_color_id'),
                            producer_color_name: document.getElementById('producer_color_name'),
                            producer_code: document.getElementById('producer_code'),
                            series_name: document.getElementById('series_name'),
                            unit_id: document.getElementById('unit_id')
                        };
                        
                        // Sformatuj nazwę produktu dla MPD (dla Marko: "Kostium kąpielowy {MODEL_NAME}")
                        let formattedName = '';
                        const originalName = (data.product_name || '').trim();
                        const brandName = data.brand_name || '';
                        
                        if (brandName.toLowerCase().includes('marko')) {
                            // Format: "Kostium dwuczęściowy Kostium kąpielowy Model {MODEL_NAME} M-XXX (X) {COLOR} - Marko"
                            // Wyjście: "Kostium kąpielowy {MODEL_NAME}"
                            // Przykład: "Kostium dwuczęściowy Kostium kąpielowy Model Rose M-818 (5) Yellow/Pink - Marko"
                            // -> "Kostium kąpielowy Rose"
                            
                            // Wzorzec: "Model {MODEL_NAME}" gdzie MODEL_NAME może być wielowyrazowy (np. "Rose", "Red Ferrari")
                            // Szukamy wszystkiego między "Model " a " M-" (kod producenta)
                            const modelMatch = originalName.match(/Model\\s+([A-Za-z]+(?:\\s+[A-Za-z]+)*?)(?:\\s+M-\\d+)/);
                            if (modelMatch) {
                                const modelName = modelMatch[1].trim();
                                formattedName = 'Kostium kąpielowy ' + modelName;
                                console.log(`Sformatowano nazwę: "${originalName}" -> "${formattedName}"`);
                            } else {
                                // Alternatywny wzorzec: szukaj po "Kostium kąpielowy" lub "Kostium dwuczęściowy Kostium kąpielowy"
                                const altMatch = originalName.match(/Kostium\\s+(?:dwuczęściowy\\s+)?kąpielowy\\s+([A-Za-z]+(?:\\s+[A-Za-z]+)*?)(?:\\s+M-\\d+|\\s+Model)/);
                                if (altMatch) {
                                    formattedName = 'Kostium kąpielowy ' + altMatch[1].trim();
                                    console.log(`Sformatowano nazwę (alt): "${originalName}" -> "${formattedName}"`);
                                } else {
                                    // Fallback: spróbuj wyciągnąć pierwsze słowo po "Model "
                                    const simpleMatch = originalName.match(/Model\\s+([A-Za-z]+)/);
                                    if (simpleMatch) {
                                        formattedName = 'Kostium kąpielowy ' + simpleMatch[1];
                                        console.log(`Sformatowano nazwę (simple): "${originalName}" -> "${formattedName}"`);
                                    } else {
                                        formattedName = originalName; // Fallback - zostaw oryginalną nazwę
                                        console.warn(`Nie udało się sformatować nazwy: "${originalName}"`);
                                    }
                                }
                            }
                        } else {
                            formattedName = originalName; // Dla innych marek zostaw oryginalną nazwę
                        }
                        
                        // Zapisz informacje o polach do wypełnienia
                        window.__formFields = formFields;
                        // Zachowaj needs_creation z poprzedniego statusu
                        if (!window.__productStatus) {
                            window.__productStatus = {};
                        }
                        window.__productStatus.action = 'ready_to_fill_form';
                        window.__productStatus.needs_creation = true; // Upewnij się, że needs_creation jest ustawione
                        window.__formattedName = formattedName;
                        
                        return {
                            ready_to_fill: true,
                            action: 'ready_to_fill_form',
                            product_name: originalName,
                            formatted_name: formattedName,
                            product_color: data.product_color || '',
                            producer_color_from_name: data.producer_color_from_name || '',
                            producer_code_from_name: data.producer_code_from_name || '',
                            fields_available: Object.keys(formFields).filter(key => formFields[key] !== null)
                        };
                    }
                    
                    return {
                        ready_to_fill: false,
                        reason: 'product_exists_or_assigned'
                    };
                })()'''
            },
            # Wypełnij pole nazwa (mpd_name) sformatowaną nazwą produktu
            {
                'type': 'evaluate',
                'expression': '''(() => {
                    const status = window.__productStatus || {};
                    const formattedName = window.__formattedName || '';
                    const nameField = document.getElementById('mpd_name');
                    
                    if (status.needs_creation && nameField) {
                        // Jeśli nie ma sformatowanej nazwy, spróbuj sformatować teraz
                        if (!formattedName) {
                            const originalName = window.__productData?.product_name || '';
                            const brandName = window.__productData?.brand_name || '';
                            
                            if (brandName.toLowerCase().includes('marko')) {
                                // Formatuj nazwę tutaj jeśli nie została sformatowana wcześniej
                                const modelMatch = originalName.match(/Model\\s+([A-Za-z]+(?:\\s+[A-Za-z]+)*?)(?:\\s+M-\\d+)/);
                                if (modelMatch) {
                                    formattedName = 'Kostium kąpielowy ' + modelMatch[1].trim();
                                } else {
                                    const simpleMatch = originalName.match(/Model\\s+([A-Za-z]+)/);
                                    if (simpleMatch) {
                                        formattedName = 'Kostium kąpielowy ' + simpleMatch[1];
                                    } else {
                                        formattedName = originalName; // Fallback
                                    }
                                }
                                console.log(`Sformatowano nazwę w akcji wypełniania: "${originalName}" -> "${formattedName}"`);
                            } else {
                                formattedName = originalName;
                            }
                        }
                        
                        if (formattedName) {
                            // Wyczyść pole i wypełnij sformatowaną nazwą
                            nameField.value = formattedName;
                            nameField.dispatchEvent(new Event('input', { bubbles: true }));
                            nameField.dispatchEvent(new Event('change', { bubbles: true }));
                            
                            // Zapisz sformatowaną nazwę do window dla dalszego użycia
                            window.__formattedName = formattedName;
                            
                            console.log(`Wypełniono pole nazwy: "${formattedName}"`);
                            
                            return {
                                name_filled: true,
                                formatted_name: formattedName,
                                original_name: window.__productData?.product_name || ''
                            };
                        }
                    }
                    
                    return {
                        name_filled: false,
                        reason: status.needs_creation ? (nameField ? 'no_formatted_name' : 'field_not_found') : 'not_needed',
                        has_name_field: !!nameField,
                        has_formatted_name: !!formattedName,
                        needs_creation: status.needs_creation
                    };
                })()'''
            },
            # UWAGA: NIE KLIKAMY przycisku "Zapisz" obok pola mpd_name!
            # Funkcja updateField() w change_form.html automatycznie tworzy produkt w MPD,
            # jeśli produkt nie jest zmapowany. Musimy najpierw wypełnić wszystkie pola!
            # Zamiast tego tylko zapisujemy wartość w polu, ale NIE klikamy przycisku "Zapisz"
            {
                'type': 'evaluate',
                'expression': '''(() => {
                    const status = window.__productStatus || {};
                    const nameField = document.getElementById('mpd_name');
                    
                    // Upewnij się, że needs_creation jest ustawione
                    const needsCreation = status.needs_creation !== undefined ? status.needs_creation : (status.action === 'create_new' || status.action === 'ready_to_fill_form');
                    
                    if (!nameField) {
                        return { save_clicked: false, reason: 'field_not_found' };
                    }
                    
                    // Jeśli produkt potrzebuje tworzenia, NIE klikamy przycisku "Zapisz"!
                    // Tylko wypełniamy pole - przycisk zostanie kliknięty dopiero po wypełnieniu wszystkich pól
                    if (needsCreation) {
                        return {
                            save_clicked: false,
                            reason: 'skipped_to_prevent_auto_create',
                            field: 'mpd_name',
                            note: 'Pole wypełnione, ale przycisk "Zapisz" NIE został kliknięty - zapobieganie automatycznemu tworzeniu produktu przed wypełnieniem wszystkich pól'
                        };
                    }
                    
                    // Jeśli produkt jest już zmapowany, możemy kliknąć przycisk "Zapisz"
                    const nameRow = nameField.closest('.form-row');
                    if (!nameRow) {
                        return { save_clicked: false, reason: 'row_not_found' };
                    }
                    
                    const buttons = nameRow.querySelectorAll('button');
                    for (const btn of buttons) {
                        const onclickAttr = btn.getAttribute('onclick') || '';
                        if (onclickAttr.includes('updateField') && onclickAttr.includes('mpd_name')) {
                            btn.click();
                            return {
                                save_clicked: true,
                                field: 'mpd_name',
                                button_text: btn.textContent.trim()
                            };
                        }
                    }
                    
                    return {
                        save_clicked: false,
                        reason: 'button_not_found',
                        buttons_found: buttons.length
                    };
                })()'''
            },
            # Poczekaj chwilę na zapisanie nazwy
            {
                'type': 'wait',
                'seconds': 1
            },
            # Pobierz oryginalny opis produktu i przygotuj do edycji przez AI
            {
                'type': 'evaluate',
                'expression': '''(() => {
                    const status = window.__productStatus || {};
                    const data = window.__productData || {};
                    
                    if (status.needs_creation) {
                        // Pobierz oryginalny opis produktu z pola description na stronie Django Admin
                        const originalDescriptionField = document.querySelector('textarea[name="description"]');
                        const originalDescription = originalDescriptionField?.value || '';
                        
                        // Zapisz oryginalny opis do użycia w edycji przez AI
                        window.__originalDescription = originalDescription;
                        window.__productStatus.description_ready = true;
                        
                        return {
                            description_found: !!originalDescriptionField,
                            original_description: originalDescription,
                            description_length: originalDescription.length,
                            ready_for_ai_edit: true
                        };
                    }
                    
                    return {
                        description_found: false,
                        reason: 'not_needed'
                    };
                })()'''
            },
            # Wywołaj funkcję Python do edycji opisu przez AI i wypełnij pola
            # UWAGA: Ta akcja wymaga integracji z AI - na razie używamy funkcji Python do edycji
            {
                'type': 'evaluate',
                'expression': '''(() => {
                    const status = window.__productStatus || {};
                    const originalDescription = window.__originalDescription || '';
                    
                    if (status.needs_creation && originalDescription) {
                        // Przygotuj żądanie edycji przez AI
                        // Funkcja Python będzie wywołana po wykonaniu tej akcji
                        window.__aiEditRequest = {
                            field: 'description',
                            original_text: originalDescription,
                            product_name: window.__formattedName || '',
                            brand_name: window.__productData?.brand_name || '',
                            action: 'edit_description',
                            ready: true
                        };
                        
                        return {
                            ai_request_prepared: true,
                            field: 'description',
                            original_length: originalDescription.length,
                            original_text: originalDescription,
                            product_name: window.__formattedName || '',
                            brand_name: window.__productData?.brand_name || '',
                            note: 'Żądanie edycji przez AI przygotowane - wymaga wywołania funkcji Python'
                        };
                    }
                    
                    return {
                        ai_request_prepared: false,
                        reason: 'no_description_or_not_needed'
                    };
                })()'''
            },
            # Wypełnij pole mpd_description zedytowanym opisem (po edycji przez AI)
            # UWAGA: Ta akcja będzie wypełniać pole po otrzymaniu zedytowanego opisu z funkcji Python
            {
                'type': 'evaluate',
                'expression': '''(() => {
                    const status = window.__productStatus || {};
                    // Sprawdź najpierw window.__editedDescription (ustawione przez funkcję Python), potem fallback do oryginalnego
                    const editedDescription = window.__editedDescription || window.__originalDescription || '';
                    
                    // Debug: sprawdź czy wartości są dostępne
                    const hasEdited = !!window.__editedDescription;
                    const hasOriginal = !!window.__originalDescription;
                    
                    // Upewnij się, że needs_creation jest ustawione (może być utracone między akcjami)
                    const needsCreation = status.needs_creation !== undefined ? status.needs_creation : (status.action === 'create_new' || status.action === 'ready_to_fill_form');
                    
                    if (needsCreation && editedDescription) {
                        const descriptionField = document.getElementById('mpd_description');
                        
                        if (descriptionField) {
                            // Wypełnij pole zedytowanym opisem
                            descriptionField.value = editedDescription;
                            descriptionField.dispatchEvent(new Event('input', { bubbles: true }));
                            descriptionField.dispatchEvent(new Event('change', { bubbles: true }));
                            
                            return {
                                description_filled: true,
                                edited_description: editedDescription,
                                description_length: editedDescription.length,
                                has_edited: hasEdited,
                                has_original: hasOriginal
                            };
                        }
                        
                        return {
                            description_filled: false,
                            reason: 'field_not_found',
                            has_edited: hasEdited,
                            has_original: hasOriginal,
                            edited_description_length: window.__editedDescription?.length || 0
                        };
                    }
                    
                    return {
                        description_filled: false,
                        reason: 'not_needed',
                        needs_creation: needsCreation,
                        status_needs_creation: status.needs_creation,
                        status_action: status.action,
                        has_edited: hasEdited,
                        has_original: hasOriginal,
                        edited_description_length: window.__editedDescription?.length || 0,
                        edited_description_available: !!window.__editedDescription
                    };
                })()'''
            },
            # UWAGA: NIE KLIKAMY przycisku "Zapisz" obok pola mpd_description!
            # Funkcja updateField() w change_form.html automatycznie tworzy produkt w MPD,
            # jeśli produkt nie jest zmapowany. Musimy najpierw wypełnić wszystkie pola!
            # Zamiast tego tylko zapisujemy wartość w polu, ale NIE klikamy przycisku "Zapisz"
            {
                'type': 'evaluate',
                'expression': '''(() => {
                    const status = window.__productStatus || {};
                    const descriptionField = document.getElementById('mpd_description');
                    
                    // Upewnij się, że needs_creation jest ustawione
                    const needsCreation = status.needs_creation !== undefined ? status.needs_creation : (status.action === 'create_new' || status.action === 'ready_to_fill_form');
                    
                    if (!descriptionField) {
                        return { save_clicked: false, reason: 'field_not_found' };
                    }
                    
                    // Jeśli produkt potrzebuje tworzenia, NIE klikamy przycisku "Zapisz"!
                    // Tylko wypełniamy pole - przycisk zostanie kliknięty dopiero po wypełnieniu wszystkich pól
                    if (needsCreation) {
                        return {
                            save_clicked: false,
                            reason: 'skipped_to_prevent_auto_create',
                            field: 'mpd_description',
                            note: 'Pole wypełnione, ale przycisk "Zapisz" NIE został kliknięty - zapobieganie automatycznemu tworzeniu produktu przed wypełnieniem wszystkich pól'
                        };
                    }
                    
                    // Jeśli produkt jest już zmapowany, możemy kliknąć przycisk "Zapisz"
                    const descriptionRow = descriptionField.closest('.form-row');
                    if (!descriptionRow) {
                        return { save_clicked: false, reason: 'row_not_found' };
                    }
                    
                    const buttons = descriptionRow.querySelectorAll('button');
                    for (const btn of buttons) {
                        const onclickAttr = btn.getAttribute('onclick') || '';
                        if (onclickAttr.includes('updateField') && onclickAttr.includes('mpd_description')) {
                            btn.click();
                            return {
                                save_clicked: true,
                                field: 'mpd_description',
                                button_text: btn.textContent.trim()
                            };
                        }
                    }
                    
                    return {
                        save_clicked: false,
                        reason: 'button_not_found',
                        buttons_found: buttons.length
                    };
                })()'''
            },
            # Poczekaj chwilę na zapisanie opisu
            {
                'type': 'wait',
                'seconds': 1
            },
            # Wygeneruj krótki opis jako streszczenie z długiego opisu
            {
                'type': 'evaluate',
                'expression': '''(() => {
                    const status = window.__productStatus || {};
                    // Użyj window.__shortDescription jeśli jest dostępne (ustawione przez funkcję Python), w przeciwnym razie wygeneruj z opisu
                    const shortDescriptionFromAI = window.__shortDescription || '';
                    const editedDescription = window.__editedDescription || window.__originalDescription || '';
                    
                    // Upewnij się, że needs_creation jest ustawione (może być utracone między akcjami)
                    const needsCreation = status.needs_creation !== undefined ? status.needs_creation : (status.action === 'create_new' || status.action === 'ready_to_fill_form');
                    
                    // Jeśli AI już wygenerowało krótki opis, użyj go
                    if (needsCreation && shortDescriptionFromAI) {
                        return {
                            short_description_generated: true,
                            short_description: shortDescriptionFromAI,
                            short_description_length: shortDescriptionFromAI.length,
                            source: 'ai_generated'
                        };
                    }
                    
                    // Jeśli nie ma krótkiego opisu z AI, ale jest długi opis, wygeneruj prosty skrót
                    if (needsCreation && editedDescription) {
                        // Generuj krótki opis jako streszczenie (max 200 znaków)
                        // TODO: Użyć AI do generowania streszczenia (już zaimplementowane w funkcji Python)
                        // Na razie używamy prostego skrócenia jako fallback
                        let shortDescription = editedDescription.trim();
                        const maxLength = 200;
                        
                        if (shortDescription.length > maxLength) {
                            // Znajdź ostatnią pełną frazę przed maxLength
                            const truncated = shortDescription.substring(0, maxLength);
                            const lastPeriod = truncated.lastIndexOf('.');
                            const lastSpace = truncated.lastIndexOf(' ');
                            
                            if (lastPeriod > maxLength * 0.7) {
                                shortDescription = truncated.substring(0, lastPeriod + 1);
                            } else if (lastSpace > maxLength * 0.7) {
                                shortDescription = truncated.substring(0, lastSpace) + '...';
                            } else {
                                shortDescription = truncated + '...';
                            }
                        }
                        
                        // Zapisz krótki opis
                        window.__shortDescription = shortDescription;
                        
                        return {
                            short_description_generated: true,
                            short_description: shortDescription,
                            short_description_length: shortDescription.length
                        };
                    }
                    
                    return {
                        short_description_generated: false,
                        reason: 'not_needed'
                    };
                })()'''
            },
            # Wypełnij pole mpd_short_description krótkim opisem
            {
                'type': 'evaluate',
                'expression': '''(() => {
                    const status = window.__productStatus || {};
                    const shortDescription = window.__shortDescription || '';
                    
                    // Upewnij się, że needs_creation jest ustawione (może być utracone między akcjami)
                    const needsCreation = status.needs_creation !== undefined ? status.needs_creation : (status.action === 'create_new' || status.action === 'ready_to_fill_form');
                    
                    if (needsCreation && shortDescription) {
                        const shortDescriptionField = document.getElementById('mpd_short_description');
                        
                        if (shortDescriptionField) {
                            // Wypełnij pole krótkim opisem
                            shortDescriptionField.value = shortDescription;
                            shortDescriptionField.dispatchEvent(new Event('input', { bubbles: true }));
                            shortDescriptionField.dispatchEvent(new Event('change', { bubbles: true }));
                            
                            return {
                                short_description_filled: true,
                                short_description: shortDescription,
                                short_description_length: shortDescription.length
                            };
                        }
                        
                        return {
                            short_description_filled: false,
                            reason: 'field_not_found'
                        };
                    }
                    
                    return {
                        short_description_filled: false,
                        reason: 'not_needed'
                    };
                })()'''
            },
            # UWAGA: NIE KLIKAMY przycisku "Zapisz" obok pola mpd_short_description!
            # Funkcja updateField() w change_form.html automatycznie tworzy produkt w MPD,
            # jeśli produkt nie jest zmapowany. Musimy najpierw wypełnić wszystkie pola!
            # Zamiast tego tylko zapisujemy wartość w polu, ale NIE klikamy przycisku "Zapisz"
            {
                'type': 'evaluate',
                'expression': '''(() => {
                    const status = window.__productStatus || {};
                    const shortDescriptionField = document.getElementById('mpd_short_description');
                    
                    // Upewnij się, że needs_creation jest ustawione
                    const needsCreation = status.needs_creation !== undefined ? status.needs_creation : (status.action === 'create_new' || status.action === 'ready_to_fill_form');
                    
                    if (!shortDescriptionField) {
                        return { save_clicked: false, reason: 'field_not_found' };
                    }
                    
                    // Jeśli produkt potrzebuje tworzenia, NIE klikamy przycisku "Zapisz"!
                    // Tylko wypełniamy pole - przycisk zostanie kliknięty dopiero po wypełnieniu wszystkich pól
                    if (needsCreation) {
                        return {
                            save_clicked: false,
                            reason: 'skipped_to_prevent_auto_create',
                            field: 'mpd_short_description',
                            note: 'Pole wypełnione, ale przycisk "Zapisz" NIE został kliknięty - zapobieganie automatycznemu tworzeniu produktu przed wypełnieniem wszystkich pól'
                        };
                    }
                    
                    // Jeśli produkt jest już zmapowany, możemy kliknąć przycisk "Zapisz"
                    const shortDescriptionRow = shortDescriptionField.closest('.form-row');
                    if (!shortDescriptionRow) {
                        return { save_clicked: false, reason: 'row_not_found' };
                    }
                    
                    const buttons = shortDescriptionRow.querySelectorAll('button');
                    for (const btn of buttons) {
                        const onclickAttr = btn.getAttribute('onclick') || '';
                        if (onclickAttr.includes('updateField') && onclickAttr.includes('mpd_short_description')) {
                            btn.click();
                            return {
                                save_clicked: true,
                                field: 'mpd_short_description',
                                button_text: btn.textContent.trim()
                            };
                        }
                    }
                    
                    return {
                        save_clicked: false,
                        reason: 'button_not_found',
                        buttons_found: buttons.length
                    };
                })()'''
            },
            # Poczekaj chwilę na zapisanie krótkiego opisu
            {
                'type': 'wait',
                'seconds': 1
            },
            # Pobierz listę dostępnych atrybutów i przygotuj do wyciągnięcia przez AI
            {
                'type': 'evaluate',
                'expression': '''(() => {
                    const status = window.__productStatus || {};
                    const attributesSelect = document.getElementById('mpd_attributes');
                    
                    // Upewnij się, że needs_creation jest ustawione
                    const needsCreation = status.needs_creation !== undefined ? status.needs_creation : (status.action === 'create_new' || status.action === 'ready_to_fill_form');
                    
                    if (!attributesSelect || !needsCreation) {
                        return {
                            attributes_prepared: false,
                            reason: !attributesSelect ? 'field_not_found' : 'not_needed'
                        };
                    }
                    
                    // Pobierz wszystkie dostępne atrybuty
                    const availableAttributes = Array.from(attributesSelect.options).map(option => ({
                        id: parseInt(option.value),
                        name: option.textContent.trim()
                    }));
                    
                    // Zapisz do użycia w następnym kroku
                    window.__availableAttributes = availableAttributes;
                    window.__productStatus.attributes_ready = true;
                    
                    return {
                        attributes_prepared: true,
                        available_count: availableAttributes.length,
                        attributes: availableAttributes.slice(0, 10), // Pokaż pierwsze 10 dla debugowania
                        note: 'Lista atrybutów przygotowana do wyciągnięcia przez AI'
                    };
                })()'''
            },
            # Wyciągnij atrybuty z opisu przez AI
            {
                'type': 'evaluate',
                'expression': '''(() => {
                    const status = window.__productStatus || {};
                    const availableAttributes = window.__availableAttributes || [];
                    const editedDescription = window.__editedDescription || window.__originalDescription || '';
                    
                    // Upewnij się, że needs_creation jest ustawione
                    const needsCreation = status.needs_creation !== undefined ? status.needs_creation : (status.action === 'create_new' || status.action === 'ready_to_fill_form');
                    
                    if (!needsCreation || !editedDescription || !availableAttributes.length) {
                        return {
                            ai_extraction_prepared: false,
                            reason: !needsCreation ? 'not_needed' : (!editedDescription ? 'no_description' : 'no_attributes')
                        };
                    }
                    
                    // Przygotuj żądanie wyciągnięcia atrybutów przez AI
                    window.__aiExtractAttributesRequest = {
                        description: editedDescription,
                        available_attributes: availableAttributes,
                        product_name: window.__formattedName || '',
                        brand_name: window.__productData?.brand_name || '',
                        action: 'extract_attributes',
                        ready: true
                    };
                    
                    // Zwróć dane bezpośrednio w wyniku, aby funkcja Python mogła je użyć
                    return {
                        ai_extraction_prepared: true,
                        description: editedDescription,  // Przekaż opis bezpośrednio
                        available_attributes: availableAttributes,  // Przekaż atrybuty bezpośrednio
                        product_name: window.__formattedName || '',
                        brand_name: window.__productData?.brand_name || '',
                        description_length: editedDescription.length,
                        available_attributes_count: availableAttributes.length,
                        note: 'Żądanie wyciągnięcia atrybutów przez AI przygotowane - wymaga wywołania funkcji Python'
                    };
                })()'''
            },
            # Zaznacz wybrane atrybuty w select multiple
            {
                'type': 'evaluate',
                'expression': '''(() => {
                    const status = window.__productStatus || {};
                    const attributesSelect = document.getElementById('mpd_attributes');
                    const selectedAttributeIds = window.__selectedAttributeIds || [];
                    
                    // Upewnij się, że needs_creation jest ustawione
                    const needsCreation = status.needs_creation !== undefined ? status.needs_creation : (status.action === 'create_new' || status.action === 'ready_to_fill_form');
                    
                    if (!attributesSelect || !needsCreation) {
                        return {
                            attributes_selected: false,
                            reason: !attributesSelect ? 'field_not_found' : 'not_needed'
                        };
                    }
                    
                    if (!selectedAttributeIds || selectedAttributeIds.length === 0) {
                        return {
                            attributes_selected: false,
                            reason: 'no_attributes_selected',
                            note: 'AI nie wybrało żadnych atrybutów lub jeszcze nie zostały wybrane'
                        };
                    }
                    
                    // Zaznacz pasujące atrybuty
                    let selectedCount = 0;
                    Array.from(attributesSelect.options).forEach(option => {
                        const optionId = parseInt(option.value);
                        if (selectedAttributeIds.includes(optionId)) {
                            option.selected = true;
                            selectedCount++;
                        }
                    });
                    
                    // Wywołaj funkcję saveAttributeSelection() jeśli istnieje
                    if (typeof saveAttributeSelection === 'function') {
                        saveAttributeSelection();
                    }
                    
                    return {
                        attributes_selected: true,
                        selected_count: selectedCount,
                        selected_ids: selectedAttributeIds,
                        note: 'Atrybuty zaznaczone w formularzu (przycisk "Zapisz atrybuty" NIE został kliknięty - zapobieganie automatycznemu tworzeniu produktu)'
                    };
                })()'''
            },
            # Wypełnij grupę rozmiarową - zawsze "bielizna"
            {
                'type': 'evaluate',
                'expression': '''(() => {
                    const status = window.__productStatus || {};
                    const sizeCategorySelect = document.getElementById('mpd_size_category');
                    
                    // Upewnij się, że needs_creation jest ustawione
                    const needsCreation = status.needs_creation !== undefined ? status.needs_creation : (status.action === 'create_new' || status.action === 'ready_to_fill_form');
                    
                    if (!sizeCategorySelect || !needsCreation) {
                        return {
                            size_category_filled: false,
                            reason: !sizeCategorySelect ? 'field_not_found' : 'not_needed'
                        };
                    }
                    
                    // Znajdź opcję "bielizna"
                    const options = Array.from(sizeCategorySelect.options);
                    let found = false;
                    for (const option of options) {
                        if (option.textContent.trim().toLowerCase() === 'bielizna') {
                            sizeCategorySelect.value = option.value;
                            sizeCategorySelect.dispatchEvent(new Event('change', { bubbles: true }));
                            found = true;
                            break;
                        }
                    }
                    
                    return {
                        size_category_filled: found,
                        value: found ? 'bielizna' : null,
                        note: found ? 'Grupa rozmiarowa ustawiona na "bielizna" (przycisk "Zapisz" NIE został kliknięty)' : 'Nie znaleziono opcji "bielizna"'
                    };
                })()'''
            },
            # Wypełnij kolor producenta (już mamy z nazwy produktu)
            {
                'type': 'evaluate',
                'expression': '''(() => {
                    const status = window.__productStatus || {};
                    const data = window.__productData || {};
                    const producerColorField = document.getElementById('producer_color_name');
                    
                    // Upewnij się, że needs_creation jest ustawione
                    const needsCreation = status.needs_creation !== undefined ? status.needs_creation : (status.action === 'create_new' || status.action === 'ready_to_fill_form');
                    
                    if (!producerColorField || !needsCreation) {
                        return {
                            producer_color_filled: false,
                            reason: !producerColorField ? 'field_not_found' : 'not_needed'
                        };
                    }
                    
                    const producerColor = data.producer_color_from_name || '';
                    if (producerColor) {
                        producerColorField.value = producerColor;
                        producerColorField.dispatchEvent(new Event('input', { bubbles: true }));
                        producerColorField.dispatchEvent(new Event('change', { bubbles: true }));
                        
                        return {
                            producer_color_filled: true,
                            value: producerColor,
                            note: 'Kolor producenta wypełniony (przycisk "Zapisz" NIE został kliknięty)'
                        };
                    }
                    
                    return {
                        producer_color_filled: false,
                        reason: 'no_color_from_name'
                    };
                })()'''
            },
            # Wypełnij kod producenta (już mamy z nazwy produktu)
            {
                'type': 'evaluate',
                'expression': '''(() => {
                    const status = window.__productStatus || {};
                    const data = window.__productData || {};
                    const producerCodeField = document.getElementById('producer_code');
                    
                    // Upewnij się, że needs_creation jest ustawione
                    const needsCreation = status.needs_creation !== undefined ? status.needs_creation : (status.action === 'create_new' || status.action === 'ready_to_fill_form');
                    
                    if (!producerCodeField || !needsCreation) {
                        return {
                            producer_code_filled: false,
                            reason: !producerCodeField ? 'field_not_found' : 'not_needed'
                        };
                    }
                    
                    const producerCode = data.producer_code_from_name || '';
                    if (producerCode) {
                        producerCodeField.value = producerCode;
                        producerCodeField.dispatchEvent(new Event('input', { bubbles: true }));
                        producerCodeField.dispatchEvent(new Event('change', { bubbles: true }));
                        
                        return {
                            producer_code_filled: true,
                            value: producerCode,
                            note: 'Kod producenta wypełniony (przycisk "Zapisz" NIE został kliknięty)'
                        };
                    }
                    
                    return {
                        producer_code_filled: false,
                        reason: 'no_code_from_name'
                    };
                })()'''
            },
            # Wypełnij nazwę serii - pusta
            {
                'type': 'evaluate',
                'expression': '''(() => {
                    const status = window.__productStatus || {};
                    const seriesNameField = document.getElementById('series_name');
                    
                    // Upewnij się, że needs_creation jest ustawione
                    const needsCreation = status.needs_creation !== undefined ? status.needs_creation : (status.action === 'create_new' || status.action === 'ready_to_fill_form');
                    
                    if (!seriesNameField || !needsCreation) {
                        return {
                            series_name_filled: false,
                            reason: !seriesNameField ? 'field_not_found' : 'not_needed'
                        };
                    }
                    
                    // Ustaw pustą wartość
                    seriesNameField.value = '';
                    seriesNameField.dispatchEvent(new Event('input', { bubbles: true }));
                    seriesNameField.dispatchEvent(new Event('change', { bubbles: true }));
                    
                    return {
                        series_name_filled: true,
                        value: '',
                        note: 'Nazwa serii ustawiona na pustą (przycisk "Zapisz" NIE został kliknięty)'
                    };
                })()'''
            },
            # Wybierz ścieżkę - jeśli w nazwie jest "kostium dwuczęściowy" to wybierz "Dwuczęściowe"
            {
                'type': 'evaluate',
                'expression': '''(() => {
                    const status = window.__productStatus || {};
                    const data = window.__productData || {};
                    const pathsSelect = document.getElementById('mpd_paths');
                    
                    // Upewnij się, że needs_creation jest ustawione
                    const needsCreation = status.needs_creation !== undefined ? status.needs_creation : (status.action === 'create_new' || status.action === 'ready_to_fill_form');
                    
                    if (!pathsSelect || !needsCreation) {
                        return {
                            path_selected: false,
                            reason: !pathsSelect ? 'field_not_found' : 'not_needed'
                        };
                    }
                    
                    const productName = (data.product_name || '').toLowerCase();
                    const shouldSelectPath = productName.includes('kostium dwuczęściowy') || productName.includes('kostium dwuczesciowy');
                    
                    if (shouldSelectPath) {
                        // Znajdź opcję "Dwuczęściowe" lub "Dwuczesciowe"
                        const options = Array.from(pathsSelect.options);
                        let selectedCount = 0;
                        for (const option of options) {
                            const optionText = option.textContent.trim().toLowerCase();
                            if (optionText.includes('dwuczęściowe') || optionText.includes('dwuczesciowe')) {
                                option.selected = true;
                                selectedCount++;
                            }
                        }
                        
                        // NIE wywołujemy addPaths() jeśli needs_creation jest true,
                        // bo to może spowodować automatyczne utworzenie produktu
                        // Zaznaczamy tylko opcje w select multiple
                        
                        return {
                            path_selected: selectedCount > 0,
                            selected_count: selectedCount,
                            path_name: 'Dwuczęściowe',
                            note: 'Ścieżka "Dwuczęściowe" zaznaczona w select multiple (przycisk "Dodaj ścieżki" NIE został kliknięty - zapobieganie automatycznemu tworzeniu produktu)'
                        };
                    }
                    
                    return {
                        path_selected: false,
                        reason: 'no_dwuczesciowy_in_name',
                        product_name: productName
                    };
                })()'''
            },
            # Wybierz jednostkę - "szt."
            {
                'type': 'evaluate',
                'expression': '''(() => {
                    const status = window.__productStatus || {};
                    const unitSelect = document.getElementById('unit_id');
                    
                    // Upewnij się, że needs_creation jest ustawione
                    const needsCreation = status.needs_creation !== undefined ? status.needs_creation : (status.action === 'create_new' || status.action === 'ready_to_fill_form');
                    
                    if (!unitSelect || !needsCreation) {
                        return {
                            unit_selected: false,
                            reason: !unitSelect ? 'field_not_found' : 'not_needed'
                        };
                    }
                    
                    // Znajdź opcję "szt." lub "szt"
                    const options = Array.from(unitSelect.options);
                    let found = false;
                    for (const option of options) {
                        const optionText = option.textContent.trim().toLowerCase();
                        if (optionText === 'szt.' || optionText === 'szt' || optionText.includes('sztuk')) {
                            unitSelect.value = option.value;
                            unitSelect.dispatchEvent(new Event('change', { bubbles: true }));
                            found = true;
                            break;
                        }
                    }
                    
                    return {
                        unit_selected: found,
                        value: found ? 'szt.' : null,
                        note: found ? 'Jednostka ustawiona na "szt." (przycisk "Zapisz" NIE został kliknięty)' : 'Nie znaleziono opcji "szt."'
                    };
                })()'''
            },
            # Pobierz dane materiałowe z size_table_txt i przygotuj do wypełnienia składu
            {
                'type': 'evaluate',
                'expression': '''(() => {
                    const status = window.__productStatus || {};
                    const data = window.__productData || {};
                    
                    // Upewnij się, że needs_creation jest ustawione
                    const needsCreation = status.needs_creation !== undefined ? status.needs_creation : (status.action === 'create_new' || status.action === 'ready_to_fill_form');
                    
                    if (!needsCreation) {
                        return {
                            composition_prepared: false,
                            reason: 'not_needed'
                        };
                    }
                    
                    // Pobierz product_id do użycia w Python
                    const productId = data.product_id || null;
                    
                    return {
                        composition_prepared: true,
                        needs_python_parsing: true,
                        product_id: productId,
                        note: 'Potrzebne dane z size_table_txt - wymaga wywołania funkcji Python do parsowania'
                    };
                })()'''
            },
            # Poczekaj chwilę na parsowanie materiałów
            {
                'type': 'wait',
                'seconds': 1
            },
            # Wypełnij skład materiałowy na podstawie sparsowanych danych
            {
                'type': 'evaluate',
                'expression': '''(() => {
                    const status = window.__productStatus || {};
                    const fabricList = document.getElementById('fabric-list');
                    const materials = window.__parsedMaterials || [];
                    
                    // Upewnij się, że needs_creation jest ustawione
                    const needsCreation = status.needs_creation !== undefined ? status.needs_creation : (status.action === 'create_new' || status.action === 'ready_to_fill_form');
                    
                    if (!fabricList || !needsCreation || !materials || materials.length === 0) {
                        return {
                            composition_filled: false,
                            reason: !fabricList ? 'field_not_found' : (!needsCreation ? 'not_needed' : 'no_materials')
                        };
                    }
                    
                    // Pobierz dostępne materiały z pierwszego selecta
                    const firstSelect = fabricList.querySelector('select[name="fabric_component[]"]');
                    if (!firstSelect) {
                        return {
                            composition_filled: false,
                            reason: 'no_fabric_select_found'
                        };
                    }
                    
                    const availableMaterials = Array.from(firstSelect.options).map(opt => ({
                        id: parseInt(opt.value),
                        name: opt.textContent.trim().toLowerCase()
                    }));
                    
                    let filledCount = 0;
                    
                    // Wypełnij materiały
                    for (let i = 0; i < materials.length; i++) {
                        const material = materials[i];
                        const materialName = material.name.toLowerCase();
                        
                        // Znajdź pasujący materiał w dostępnych opcjach
                        const matchedMaterial = availableMaterials.find(am => 
                            am.name.includes(materialName) || materialName.includes(am.name) ||
                            am.name === materialName
                        );
                        
                        if (!matchedMaterial) {
                            continue; // Pomiń jeśli nie znaleziono pasującego materiału
                        }
                        
                        // Jeśli potrzebujemy więcej wierszy, dodaj je
                        const fabricRows = fabricList.querySelectorAll('.fabric-row');
                        if (i >= fabricRows.length) {
                            // Wywołaj funkcję addFabricRow() jeśli istnieje
                            if (typeof addFabricRow === 'function') {
                                addFabricRow();
                            }
                        }
                        
                        // Pobierz aktualny wiersz (może być nowo dodany)
                        const currentRows = fabricList.querySelectorAll('.fabric-row');
                        if (i < currentRows.length) {
                            const row = currentRows[i];
                            const select = row.querySelector('select[name="fabric_component[]"]');
                            const input = row.querySelector('input[name="fabric_percentage[]"]');
                            
                            if (select && input) {
                                select.value = matchedMaterial.id;
                                input.value = material.percentage;
                                select.dispatchEvent(new Event('change', { bubbles: true }));
                                input.dispatchEvent(new Event('input', { bubbles: true }));
                                filledCount++;
                            }
                        }
                    }
                    
                    return {
                        composition_filled: filledCount > 0,
                        filled_count: filledCount,
                        total_materials: materials.length,
                        note: `Wypełniono ${filledCount} z ${materials.length} materiałów (przycisk "Zapisz" NIE został kliknięty)`
                    };
                })()'''
            },
            # Screenshot strony szczegółów produktu
            {
                'type': 'screenshot',
                'full_page': True,
                'path': None
            },
            # Powrót do listingu produktów (jeśli produkt został zmapowany)
            # Jeśli produkt potrzebuje tworzenia, zostajemy na stronie formularza do wypełnienia pól
            {
                'type': 'evaluate',
                'expression': '''(() => {
                    const status = window.__productStatus || {};
                    const isMapped = document.querySelector('input[name="is_mapped"]')?.checked || false;
                    
                    // Jeśli produkt został zmapowany, wróć do listingu
                    // Jeśli produkt potrzebuje tworzenia, zostajemy na stronie formularza (czekamy na wypełnienie pól)
                    if (isMapped) {
                        // Pobierz URL listingu z parametrami filtrowania
                        const changelistUrl = sessionStorage.getItem('changelist_url') || 
                                             document.referrer || 
                                             '/admin/matterhorn1/product/';
                        
                        window.__shouldReturn = {
                            should_return: true,
                            changelist_url: changelistUrl
                        };
                        
                        return {
                            should_return: true,
                            changelist_url: changelistUrl,
                            reason: 'product_mapped'
                        };
                    }
                    
                    // Jeśli produkt potrzebuje tworzenia, zostajemy na stronie
                    if (status.needs_creation) {
                        return {
                            should_return: false,
                            reason: 'product_needs_creation',
                            waiting_for_form_fill: true,
                            form_fields_ready: true
                        };
                    }
                    
                    return {
                        should_return: false,
                        reason: 'product_not_mapped'
                    };
                })()'''
            },
            # Nawiguj z powrotem do listingu (TYLKO jeśli produkt został zmapowany)
            # UWAGA: Jeśli produkt potrzebuje tworzenia (needs_creation), NIE nawigujemy dalej!
            {
                'type': 'evaluate',
                'expression': '''(() => {
                    const status = window.__productStatus || {};
                    const shouldReturn = window.__shouldReturn;
                    
                    // Jeśli produkt potrzebuje tworzenia, NIE nawigujemy dalej - zostajemy na formularzu
                    if (status.needs_creation) {
                        return {
                            navigating_back: false,
                            reason: 'product_needs_creation_stay_on_form',
                            note: 'Zostajemy na formularzu - czekamy na wypełnienie wszystkich pól'
                        };
                    }
                    
                    // Nawiguj tylko jeśli produkt został zmapowany
                    if (shouldReturn && shouldReturn.should_return) {
                        console.log('Produkt został zmapowany - zwracam URL do nawigacji przez Playwright:', shouldReturn.changelist_url);
                        return { 
                            navigating_back: true,
                            navigate_to_url: shouldReturn.changelist_url  // URL do nawigacji przez Playwright
                        };
                    }
                    return { navigating_back: false };
                })()'''
            },
            # Poczekaj na załadowanie listingu (TYLKO jeśli nawigowaliśmy z powrotem)
            {
                'type': 'evaluate',
                'expression': '''(() => {
                    const status = window.__productStatus || {};
                    
                    // Jeśli produkt potrzebuje tworzenia, pomiń czekanie na listing
                    if (status.needs_creation) {
                        return { skip_wait: true, reason: 'product_needs_creation' };
                    }
                    
                    // Sprawdź czy jesteśmy na liście produktów
                    const isChangelist = window.location.pathname.includes('/admin/matterhorn1/product/') && 
                                       !window.location.pathname.match(/\\/\\d+\\/change\\//);
                    
                    if (isChangelist) {
                        // Poczekaj na załadowanie listingu
                        return { skip_wait: false, waiting_for_listing: true };
                    }
                    
                    return { skip_wait: true, reason: 'not_on_changelist' };
                })()'''
            },
            {
                'type': 'wait_for',
                'selector': 'table.changelist tbody tr, table#result_list tbody tr, table tbody tr',
                'timeout': 10000,
                'optional': True
            },
            # Przejdź do następnego produktu z listy (TYLKO jeśli wróciliśmy do listingu i produkt został zmapowany)
            # UWAGA: Jeśli produkt potrzebuje tworzenia, NIE przechodzimy do następnego produktu!
            {
                'type': 'evaluate',
                'expression': '''(() => {
                    const status = window.__productStatus || {};
                    
                    // Jeśli produkt potrzebuje tworzenia, NIE przechodzimy do następnego produktu
                    if (status.needs_creation) {
                        return {
                            next_product_found: false,
                            reason: 'product_needs_creation_stay_on_form',
                            note: 'Zostajemy na formularzu - czekamy na wypełnienie wszystkich pól przed przejściem dalej'
                        };
                    }
                    
                    // Sprawdź czy jesteśmy na liście produktów
                    const isChangelist = window.location.pathname.includes('/admin/matterhorn1/product/') && 
                                       !window.location.pathname.match(/\\/\\d+\\/change\\//);
                    
                    if (!isChangelist) {
                        return { next_product_found: false, reason: 'not_on_changelist' };
                    }
                    
                    // Znajdź pierwszy produkt z listy, który nie jest jeszcze zmapowany
                    const rows = document.querySelectorAll('table#result_list tbody tr');
                    let nextProductLink = null;
                    
                    for (const row of rows) {
                        const link = row.querySelector('td.field-name a');
                        const isMappedCell = row.querySelector('td.field-is_mapped');
                        const isMapped = isMappedCell?.textContent?.trim() === 'True' || 
                                       isMappedCell?.querySelector('img[alt="True"]');
                        
                        if (link && !isMapped) {
                            nextProductLink = link.href;
                            break;
                        }
                    }
                    
                    if (nextProductLink) {
                        window.__nextProduct = {
                            next_product_found: true,
                            next_product_url: nextProductLink
                        };
                        console.log('Przechodzę do następnego produktu - zwracam URL do nawigacji przez Playwright:', nextProductLink);
                        return {
                            next_product_found: true,
                            next_product_url: nextProductLink,
                            navigate_to_url: nextProductLink,  // URL do nawigacji przez Playwright
                            navigating: true
                        };
                    }
                    
                    return {
                        next_product_found: false,
                        reason: 'no_more_products'
                    };
                })()'''
            },
            # Poczekaj na załadowanie następnego produktu (TYLKO jeśli przeszliśmy do następnego produktu)
            {
                'type': 'evaluate',
                'expression': '''(() => {
                    const status = window.__productStatus || {};
                    
                    // Jeśli produkt potrzebuje tworzenia, NIE czekamy na załadowanie następnego produktu
                    // Zostajemy na formularzu i kończymy automatyzację
                    if (status.needs_creation) {
                        return {
                            skip_wait: true,
                            reason: 'product_needs_creation_stay_on_form',
                            note: 'Automatyzacja zatrzymana - czekamy na wypełnienie wszystkich pól formularza'
                        };
                    }
                    
                    // Sprawdź czy jesteśmy na stronie szczegółów produktu
                    const isProductDetail = window.location.pathname.match(/\\/\\d+\\/change\\//);
                    if (isProductDetail) {
                        return { skip_wait: false, waiting_for_product_detail: true };
                    }
                    
                    return { skip_wait: true, reason: 'not_on_product_detail' };
                })()'''
            },
            {
                'type': 'wait_for',
                'selector': '.form-row, fieldset, input[name="name"]',
                'timeout': 15000,
                'optional': True
            },
            # Sprawdź czy wszystkie pola są wypełnione i utwórz produkt
            {
                'type': 'evaluate',
                'expression': '''(() => {
                    const status = window.__productStatus || {};
                    
                    // Jeśli produkt potrzebuje tworzenia, sprawdź czy wszystkie pola są wypełnione
                    if (status.needs_creation) {
                        // Sprawdź czy wszystkie wymagane pola są wypełnione
                        const nameField = document.getElementById('mpd_name');
                        const descField = document.getElementById('mpd_description');
                        const shortDescField = document.getElementById('mpd_short_description');
                        const sizeCategoryField = document.getElementById('mpd_size_category');
                        const producerColorField = document.getElementById('producer_color_name');
                        const producerCodeField = document.getElementById('producer_code');
                        const unitField = document.getElementById('unit_id');
                        
                        const fieldsFilled = {
                            name: nameField && nameField.value.trim() !== '',
                            description: descField && descField.value.trim() !== '',
                            short_description: shortDescField && shortDescField.value.trim() !== '',
                            size_category: sizeCategoryField && sizeCategoryField.value !== '',
                            producer_color: producerColorField && producerColorField.value.trim() !== '',
                            producer_code: producerCodeField && producerCodeField.value.trim() !== '',
                            unit: unitField && unitField.value !== ''
                        };
                        
                        const allFieldsFilled = Object.values(fieldsFilled).every(v => v === true);
                        
                        const result = {
                            ready_to_create: allFieldsFilled,
                            all_fields_filled: allFieldsFilled,
                            fields_status: fieldsFilled
                        };
                        
                        // Zapisz wynik do zmiennej globalnej
                        window.__readyToCreate = result;
                        
                        if (allFieldsFilled) {
                            return result;
                        } else {
                            result.message = 'Nie wszystkie pola są wypełnione';
                            return result;
                        }
                    }
                    
                    const result = {
                        ready_to_create: false,
                        reason: 'product_not_needs_creation'
                    };
                    window.__readyToCreate = result;
                    return result;
                })()'''
            },
            # Kliknij przycisk "Utwórz nowy produkt w MPD" jeśli wszystkie pola są wypełnione
            {
                'type': 'evaluate',
                'expression': '''(() => {
                    const status = window.__productStatus || {};
                    const readyToCreate = window.__readyToCreate || {};
                    
                    if (status.needs_creation && readyToCreate.ready_to_create) {
                        const createBtn = document.getElementById('create-mpd-product-btn');
                        if (createBtn) {
                            // Kliknij przycisk
                            createBtn.click();
                            return {
                                button_clicked: true,
                                button_found: true,
                                note: 'Przycisk "Utwórz nowy produkt w MPD" został kliknięty'
                            };
                        } else {
                            return {
                                button_clicked: false,
                                button_found: false,
                                error: 'Przycisk "Utwórz nowy produkt w MPD" nie został znaleziony'
                            };
                        }
                    }
                    
                    return {
                        button_clicked: false,
                        reason: !status.needs_creation ? 'product_not_needs_creation' : (!readyToCreate.ready_to_create ? 'fields_not_filled' : 'unknown')
                    };
                })()'''
            },
            # Poczekaj na utworzenie produktu (sprawdź status message lub reload strony)
            {
                'type': 'wait',
                'seconds': 5
            },
            # Sprawdź czy produkt został utworzony (sprawdź status message lub czy strona się przeładowała)
            {
                'type': 'evaluate',
                'expression': '''(() => {
                    // Poczekaj chwilę na przeładowanie strony
                    const statusMsg = document.getElementById('status-message');
                    const isMappedInput = document.querySelector('input[name="is_mapped"]');
                    const isMappedValue = isMappedInput?.value === 'True' || isMappedInput?.checked === true;
                    const isMappedDisplay = document.querySelector('.field-is_mapped')?.textContent?.trim() === 'True' ||
                                          document.querySelector('.field-is_mapped img[alt="True"]') !== null;
                    const isMapped = isMappedValue || isMappedDisplay;
                    
                    // Sprawdź czy jest komunikat sukcesu (różne warianty)
                    const statusText = statusMsg ? statusMsg.textContent.trim() : '';
                    const hasSuccessMessage = statusText && (
                        statusText.toLowerCase().includes('utworzony') || 
                        statusText.toLowerCase().includes('utworzono') ||
                        statusText.toLowerCase().includes('mpd') || 
                        statusText.toLowerCase().includes('tworzenie') ||
                        statusText.toLowerCase().includes('success') ||
                        statusText.toLowerCase().includes('sukces')
                    );
                    
                    // Sprawdź czy jesteśmy na stronie produktu (strona się przeładowała)
                    const isOnProductPage = window.location.pathname.includes('/admin/matterhorn1/product/') && 
                                           window.location.pathname.match(/\\/\\d+\\/change\\//);
                    
                    // Sprawdź czy jest mapped_product_uid (produkt został utworzony w MPD)
                    // 1. Sprawdź input field
                    const mappedProductUidInput = document.querySelector('input[name="mapped_product_uid"]');
                    const mappedProductUidFromInput = mappedProductUidInput?.value || '';
                    
                    // 2. Sprawdź sekcję "Mapowanie MPD" - znajdź fieldset i sprawdź wartość
                    let mappingFieldset = document.querySelector('#fieldset-0-3');
                    // Jeśli nie znaleziono po ID, szukaj po tekście nagłówka
                    if (!mappingFieldset) {
                        const fieldsets = document.querySelectorAll('fieldset');
                        for (const fs of fieldsets) {
                            const heading = fs.querySelector('h2.fieldset-heading, h2');
                            if (heading && heading.textContent.includes('Mapowanie MPD')) {
                                mappingFieldset = fs;
                                break;
                            }
                        }
                    }
                    let mappedProductUidFromFieldset = '';
                    if (mappingFieldset) {
                        // Szukaj wartości w sekcji - może być w input, div, lub jako tekst
                        const fieldsetInput = mappingFieldset.querySelector('input[name="mapped_product_uid"]');
                        const fieldsetDiv = mappingFieldset.querySelector('.field-mapped_product_uid');
                        const fieldsetText = mappingFieldset.textContent || '';
                        
                        if (fieldsetInput) {
                            mappedProductUidFromFieldset = fieldsetInput.value || '';
                        } else if (fieldsetDiv) {
                            mappedProductUidFromFieldset = fieldsetDiv.textContent.trim() || '';
                        } else {
                            // Spróbuj wyciągnąć wartość z tekstu sekcji (np. "Mapped product uid: 1234")
                            const uidMatch = fieldsetText.match(/mapped.*product.*uid[\\s:]*([0-9]+)/i);
                            if (uidMatch) {
                                mappedProductUidFromFieldset = uidMatch[1];
                            }
                        }
                    }
                    
                    // 3. Sprawdź czy wartość jest różna od "-" lub pustej
                    const hasMappedUid = (mappedProductUidFromInput && mappedProductUidFromInput.trim() !== '' && mappedProductUidFromInput.trim() !== '-') ||
                                       (mappedProductUidFromFieldset && mappedProductUidFromFieldset.trim() !== '' && mappedProductUidFromFieldset.trim() !== '-');
                    
                    let result = {
                        product_created: false,
                        waiting: true,
                        note: 'Czekam na potwierdzenie utworzenia produktu',
                        status_text: statusText,
                        is_mapped: isMapped,
                        has_mapped_uid: hasMappedUid,
                        is_on_product_page: isOnProductPage
                    };
                    
                    // Produkt został utworzony jeśli:
                    // 1. Jest komunikat sukcesu LUB
                    // 2. Produkt jest zmapowany LUB
                    // 3. Jest mapped_product_uid (produkt został utworzony w MPD)
                    if (hasSuccessMessage || isMapped || hasMappedUid) {
                        result = {
                            product_created: true,
                            success_message: statusText || 'Produkt został utworzony',
                            is_mapped: isMapped,
                            has_mapped_uid: hasMappedUid,
                            page_reloaded: isOnProductPage
                        };
                    }
                    
                    // Zapisz wynik do zmiennej globalnej
                    window.__productCreated = result;
                    
                    return result;
                })()'''
            },
            # WAŻNE: Poczekaj dłużej na pełne przeładowanie strony i aktualizację bazy danych
            # Po utworzeniu produktu, Django musi zaktualizować is_mapped w bazie
            # Jeśli wrócimy za szybko do listy, produkt może jeszcze nie być oznaczony jako zmapowany
            {
                'type': 'wait',
                'seconds': 8  # Zwiększone z 5 do 8 sekund - dajemy czas na aktualizację bazy
            },
            # Sprawdź ponownie czy produkt został utworzony i czy is_mapped jest zaktualizowane
            {
                'type': 'evaluate',
                'expression': '''(() => {
                    console.log('=== SPRAWDZANIE PO OSTATECZNYM OCZEKIWANIU ===');
                    const isMappedInput = document.querySelector('input[name="is_mapped"]');
                    const isMappedValue = isMappedInput?.value === 'True' || isMappedInput?.checked === true;
                    const isMappedDisplay = document.querySelector('.field-is_mapped')?.textContent?.trim() === 'True' ||
                                          document.querySelector('.field-is_mapped img[alt="True"]') !== null;
                    const isMapped = isMappedValue || isMappedDisplay;
                    
                    const mappedProductUid = document.querySelector('input[name="mapped_product_uid"]')?.value || '';
                    const hasMappedUid = mappedProductUid && mappedProductUid.trim() !== '' && mappedProductUid.trim() !== '-';
                    
                    console.log('Po oczekiwaniu - is_mapped:', isMapped);
                    console.log('Po oczekiwaniu - mapped_product_uid:', mappedProductUid);
                    console.log('Po oczekiwaniu - hasMappedUid:', hasMappedUid);
                    
                    // Zaktualizuj window.__productCreated z najnowszymi danymi
                    if (window.__productCreated) {
                        window.__productCreated.is_mapped = isMapped;
                        window.__productCreated.has_mapped_uid = hasMappedUid;
                        window.__productCreated.mapped_product_uid = mappedProductUid;
                        if (isMapped || hasMappedUid) {
                            window.__productCreated.product_created = true;
                        }
                    }
                    
                    return {
                        final_check: true,
                        is_mapped: isMapped,
                        has_mapped_uid: hasMappedUid,
                        mapped_product_uid: mappedProductUid,
                        product_created: isMapped || hasMappedUid
                    };
                })()'''
            },
            # Sprawdź czy mapped_product_uid jest już dostępne (może wymagać przeładowania strony)
            {
                'type': 'evaluate',
                'expression': '''(() => {
                    const productCreatedResult = window.__productCreated || {};
                    const productCreated = productCreatedResult.product_created === true;
                    
                    if (!productCreated) {
                        return { mapped_uid_check: false, reason: 'product_not_created' };
                    }
                    
                    // Sprawdź mapped_product_uid - użyj tej samej logiki co w akcji sprawdzającej utworzenie
                    const mappedProductUidInput = document.querySelector('input[name="mapped_product_uid"]');
                    const mappedProductUidFromInput = mappedProductUidInput?.value || '';
                    
                    // Sprawdź również w fieldset "Mapowanie MPD"
                    let mappingFieldset = document.querySelector('#fieldset-0-3');
                    if (!mappingFieldset) {
                        const fieldsets = document.querySelectorAll('fieldset');
                        for (const fs of fieldsets) {
                            const heading = fs.querySelector('h2.fieldset-heading, h2');
                            if (heading && heading.textContent.includes('Mapowanie MPD')) {
                                mappingFieldset = fs;
                                break;
                            }
                        }
                    }
                    let mappedProductUidFromFieldset = '';
                    if (mappingFieldset) {
                        const fieldsetInput = mappingFieldset.querySelector('input[name="mapped_product_uid"]');
                        const fieldsetDiv = mappingFieldset.querySelector('.field-mapped_product_uid');
                        const fieldsetText = mappingFieldset.textContent || '';
                        
                        if (fieldsetInput) {
                            mappedProductUidFromFieldset = fieldsetInput.value || '';
                        } else if (fieldsetDiv) {
                            mappedProductUidFromFieldset = fieldsetDiv.textContent.trim() || '';
                        } else {
                            const uidMatch = fieldsetText.match(/mapped.*product.*uid[\\s:]*([0-9]+)/i);
                            if (uidMatch) {
                                mappedProductUidFromFieldset = uidMatch[1];
                            }
                        }
                    }
                    
                    const hasMappedUid = (mappedProductUidFromInput && mappedProductUidFromInput.trim() !== '' && mappedProductUidFromInput.trim() !== '-') ||
                                       (mappedProductUidFromFieldset && mappedProductUidFromFieldset.trim() !== '' && mappedProductUidFromFieldset.trim() !== '-');
                    
                    // Jeśli nie ma mapped_product_uid, przeładuj stronę aby odświeżyć dane
                    if (!hasMappedUid && productCreatedResult.has_mapped_uid) {
                        console.log('mapped_product_uid nie jest jeszcze widoczne, przeładowuję stronę...');
                        window.location.reload();
                        return { mapped_uid_check: false, reloading: true, reason: 'reloading_page_to_get_mapped_uid' };
                    }
                    
                    return {
                        mapped_uid_check: true,
                        has_mapped_uid: hasMappedUid,
                        mapped_uid_input: mappedProductUidFromInput,
                        mapped_uid_fieldset: mappedProductUidFromFieldset
                    };
                })()'''
            },
            # Poczekaj po przeładowaniu strony (jeśli było przeładowanie)
            {
                'type': 'wait',
                'seconds': 3
            },
            # Upload zdjęć do MinIO po utworzeniu produktu
            {
                'type': 'evaluate',
                'expression': '''(() => {
                    const productCreatedResult = window.__productCreated || {};
                    const productCreated = productCreatedResult.product_created === true;
                    const hasMappedUid = productCreatedResult.has_mapped_uid === true;
                    
                    if (!productCreated) {
                        return { upload_images_skipped: true, reason: 'product_not_created' };
                    }
                    
                    // Sprawdź czy produkt ma mapped_product_uid - użyj tej samej logiki co w akcji sprawdzającej utworzenie
                    const mappedProductUidInput = document.querySelector('input[name="mapped_product_uid"]');
                    const mappedProductUidFromInput = mappedProductUidInput?.value || '';
                    
                    // Sprawdź również w fieldset "Mapowanie MPD"
                    let mappingFieldset = document.querySelector('#fieldset-0-3');
                    if (!mappingFieldset) {
                        const fieldsets = document.querySelectorAll('fieldset');
                        for (const fs of fieldsets) {
                            const heading = fs.querySelector('h2.fieldset-heading, h2');
                            if (heading && heading.textContent.includes('Mapowanie MPD')) {
                                mappingFieldset = fs;
                                break;
                            }
                        }
                    }
                    let mappedProductUidFromFieldset = '';
                    if (mappingFieldset) {
                        const fieldsetInput = mappingFieldset.querySelector('input[name="mapped_product_uid"]');
                        const fieldsetDiv = mappingFieldset.querySelector('.field-mapped_product_uid');
                        const fieldsetText = mappingFieldset.textContent || '';
                        
                        if (fieldsetInput) {
                            mappedProductUidFromFieldset = fieldsetInput.value || '';
                        } else if (fieldsetDiv) {
                            mappedProductUidFromFieldset = fieldsetDiv.textContent.trim() || '';
                        } else {
                            const uidMatch = fieldsetText.match(/mapped.*product.*uid[\\s:]*([0-9]+)/i);
                            if (uidMatch) {
                                mappedProductUidFromFieldset = uidMatch[1];
                            }
                        }
                    }
                    
                    // Sprawdź czy wartość jest różna od "-" lub pustej
                    const mappedProductUid = (mappedProductUidFromInput && mappedProductUidFromInput.trim() !== '' && mappedProductUidFromInput.trim() !== '-') 
                                            ? mappedProductUidFromInput.trim()
                                            : (mappedProductUidFromFieldset && mappedProductUidFromFieldset.trim() !== '' && mappedProductUidFromFieldset.trim() !== '-')
                                                ? mappedProductUidFromFieldset.trim()
                                                : null;
                    
                    // Jeśli nie ma mapped_product_uid, ale has_mapped_uid jest true, poczekaj jeszcze chwilę
                    if (!mappedProductUid && hasMappedUid) {
                        // Spróbuj jeszcze raz po chwili - może strona się jeszcze przeładowuje
                        return { upload_images_skipped: true, reason: 'mapped_uid_not_loaded_yet', has_mapped_uid: hasMappedUid, note: 'Czekam na załadowanie mapped_product_uid' };
                    }
                    
                    if (!mappedProductUid) {
                        return { upload_images_skipped: true, reason: 'no_mapped_product_uid', has_mapped_uid: hasMappedUid };
                    }
                    
                    // Wywołaj upload zdjęć
                    const productId = window.location.pathname.match(/\\/(\\d+)\\/change\\//)?.[1];
                    if (!productId) {
                        return { upload_images_skipped: true, reason: 'no_product_id' };
                    }
                    
                    console.log(`Rozpoczynam upload zdjęć dla produktu ${productId}, mapped_product_uid: ${mappedProductUid}`);
                    
                    // Wywołaj funkcję uploadImages przez fetch SYNCHRONICZNIE (używamy async/await w Promise)
                    // Ustawiamy flagę że upload się rozpoczął
                    window.__imagesUploadStarted = true;
                    window.__imagesUploaded = null;
                    
                    // Wywołaj fetch i poczekaj na odpowiedź
                    fetch(`/admin/matterhorn1/product/upload-images/${productId}/`, {
                        method: 'POST',
                        headers: {
                            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || ''
                        }
                    })
                    .then(response => {
                        console.log('Response status:', response.status);
                        return response.json();
                    })
                    .then(data => {
                        window.__imagesUploaded = {
                            success: data.success,
                            message: data.message || data.error,
                            images_count: data.images?.length || 0,
                            errors: data.errors || []
                        };
                        console.log('Upload zdjęć zakończony:', data);
                        window.__imagesUploadStarted = false;
                    })
                    .catch(error => {
                        window.__imagesUploaded = {
                            success: false,
                            error: error.toString()
                        };
                        console.error('Błąd uploadu zdjęć:', error);
                        window.__imagesUploadStarted = false;
                    });
                    
                    return {
                        upload_images_started: true,
                        product_id: productId,
                        mapped_product_uid: mappedProductUid,
                        note: 'Fetch został wywołany, czekam na zakończenie...'
                    };
                })()'''
            },
            # Poczekaj na zakończenie uploadu zdjęć - sprawdzaj w pętli
            {
                'type': 'evaluate',
                'expression': '''(() => {
                    // Sprawdź czy upload się zakończył
                    const uploadResult = window.__imagesUploaded;
                    const uploadStarted = window.__imagesUploadStarted === true;
                    
                    if (uploadStarted && !uploadResult) {
                        // Upload się rozpoczął ale jeszcze nie zakończył - czekaj dłużej
                        console.log('Upload w trakcie, czekam...');
                        return { upload_in_progress: true, wait_seconds: 10 };
                    }
                    
                    if (uploadResult) {
                        console.log('Upload zakończony:', uploadResult);
                        return { upload_in_progress: false, upload_completed: true };
                    }
                    
                    // Upload się nie rozpoczął - może nie było mapped_product_uid?
                    return { upload_in_progress: false, upload_completed: false, reason: 'upload_not_started' };
                })()'''
            },
            {
                'type': 'wait',
                # Czekaj 10 sekund na upload (fetch może być wolny)
                'seconds': 10
            },
            # Sprawdź wynik uploadu zdjęć
            {
                'type': 'evaluate',
                'expression': '''(() => {
                    const uploadResult = window.__imagesUploaded || {};
                    return {
                        upload_images_completed: true,
                        upload_success: uploadResult.success || false,
                        upload_message: uploadResult.message || uploadResult.error || 'Brak informacji',
                        images_count: uploadResult.images_count || 0
                    };
                })()'''
            },
            # Wróć do listingu produktów (TYLKO jeśli produkt został utworzony) i zwiększ licznik
            {
                'type': 'evaluate',
                'expression': '''(() => {
                    console.log('=== SPRAWDZANIE CZY PRODUKT ZOSTAŁ UTWORZONY ===');
                    // Sprawdź czy produkt został utworzony - użyj wyniku z poprzedniej akcji
                    const productCreatedResult = window.__productCreated || {};
                    const productCreated = productCreatedResult.product_created === true;
                    console.log('Product created (z window.__productCreated):', productCreated);
                    
                    // Jeśli nie ma wyniku, sprawdź ręcznie
                    if (!productCreated) {
                        console.log('Sprawdzam ręcznie czy produkt został utworzony...');
                        const statusMsg = document.getElementById('status-message');
                        const isMappedInput = document.querySelector('input[name="is_mapped"]');
                        const isMappedValue = isMappedInput?.value === 'True' || isMappedInput?.checked === true;
                        const isMappedDisplay = document.querySelector('.field-is_mapped')?.textContent?.trim() === 'True' ||
                                              document.querySelector('.field-is_mapped img[alt="True"]') !== null;
                        const isMapped = isMappedValue || isMappedDisplay;
                        const mappedProductUid = document.querySelector('input[name="mapped_product_uid"]')?.value || '';
                        const hasMappedUid = mappedProductUid && mappedProductUid.trim() !== '';
                        const statusText = statusMsg ? statusMsg.textContent.trim() : '';
                        const hasSuccessMessage = statusText && (
                            statusText.toLowerCase().includes('utworzony') || 
                            statusText.toLowerCase().includes('utworzono') ||
                            statusText.toLowerCase().includes('mpd') || 
                            statusText.toLowerCase().includes('tworzenie') ||
                            statusText.toLowerCase().includes('success') ||
                            statusText.toLowerCase().includes('sukces')
                        );
                        
                        console.log('Status message:', statusText);
                        console.log('is_mapped:', isMapped);
                        console.log('has_mapped_uid:', hasMappedUid);
                        console.log('has_success_message:', hasSuccessMessage);
                        
                        const productCreatedManual = hasSuccessMessage || isMapped || hasMappedUid;
                        console.log('Product created (ręcznie):', productCreatedManual);
                        
                        if (!productCreatedManual) {
                            console.log('Produkt NIE został jeszcze utworzony - czekam...');
                            return {
                                navigating_back: false,
                                reason: 'product_not_created_yet',
                                note: 'Czekam na utworzenie produktu przed powrotem do listingu',
                                status_message: statusText || 'brak',
                                is_mapped: isMapped,
                                has_mapped_uid: hasMappedUid
                            };
                        }
                    }
                    
                    console.log('✅ Produkt został utworzony - przechodzę do listy produktów');
                    
                    // Zwiększ licznik przetworzonych produktów
                    const productsProcessed = parseInt(sessionStorage.getItem('products_processed') || '0') + 1;
                    sessionStorage.setItem('products_processed', productsProcessed.toString());
                    console.log('Licznik przetworzonych produktów:', productsProcessed);
                    
                    // Sprawdź czy już jesteśmy na liście produktów (strona się przeładowała i wróciła do produktu)
                    const isChangelist = window.location.pathname.includes('/admin/matterhorn1/product/') && 
                                       !window.location.pathname.match(/\\/\\d+\\/change\\//);
                    console.log('Czy jesteśmy na liście produktów:', isChangelist);
                    console.log('Obecny URL:', window.location.href);
                    
                    if (isChangelist) {
                        // Już jesteśmy na liście, nie trzeba nawigować
                        console.log('Już jesteśmy na liście produktów - nie trzeba nawigować');
                        return {
                            navigating_back: false,
                            already_on_changelist: true,
                            url: window.location.href,
                            products_processed: productsProcessed
                        };
                    }
                    
                    const changelistUrl = sessionStorage.getItem('changelist_url');
                    console.log('Zapisany changelist_url:', changelistUrl);
                    
                    if (changelistUrl) {
                        // WAŻNE: Zwróć URL do nawigacji przez Playwright zamiast window.location.href
                        // To zapobiega problemom z zamkniętą przeglądarką
                        console.log('🔄 Wracam do listy produktów - zwracam URL do nawigacji przez Playwright:', changelistUrl);
                        return {
                            navigating_back: true,
                            navigate_to_url: changelistUrl,  // URL do nawigacji przez Playwright
                            products_processed: productsProcessed,
                            note: 'Odświeżam listę produktów aby zaktualizować status is_mapped'
                        };
                    }
                    
                    // Jeśli nie ma zapisanego URL, skonstruuj go z obecnego URL
                    const currentUrl = window.location.href;
                    console.log('Brak zapisanego URL, konstruuję z obecnego URL:', currentUrl);
                    const changelistMatch = currentUrl.match(/admin\\/matterhorn1\\/product\\/(\\d+)\\/change\\//);
                    if (changelistMatch) {
                        // Wyciągnij parametry z URL
                        const urlParams = new URLSearchParams(currentUrl.split('?')[1] || '');
                        const brandId = urlParams.get('brand__id__exact') || '';
                        const active = urlParams.get('active__exact') || '';
                        const isMapped = urlParams.get('is_mapped__exact') || '';
                        
                        const baseUrl = currentUrl.split('/admin/')[0];
                        const changelistUrl = `${baseUrl}/admin/matterhorn1/product/?brand__id__exact=${brandId}&active__exact=${active}&is_mapped__exact=${isMapped}`;
                        console.log('Skonstruowany URL:', changelistUrl);
                        return {
                            navigating_back: true,
                            navigate_to_url: changelistUrl,  // URL do nawigacji przez Playwright
                            constructed: true
                        };
                    }
                    
                    console.error('❌ Nie można skonstruować URL do listingu');
                    return {
                        navigating_back: false,
                        error: 'Nie można skonstruować URL do listingu',
                        current_url: currentUrl
                    };
                })()'''
            },
            # Poczekaj na przeładowanie strony po nawigacji (nawigacja przez Playwright czeka automatycznie, ale dajemy dodatkowy czas)
            {
                'type': 'wait',
                'seconds': 2
            },
            # Poczekaj na załadowanie listingu - sprawdź czy jesteśmy na właściwej stronie
            {
                'type': 'evaluate',
                'expression': '''(() => {
                    console.log('=== SPRAWDZANIE CZY JESTEŚMY NA LIŚCIE PRODUKTÓW ===');
                    const currentPath = window.location.pathname;
                    const isChangelist = currentPath.includes('/admin/matterhorn1/product/') && 
                                       !currentPath.match(/\\/\\d+\\/change\\//);
                    console.log('Obecna ścieżka:', currentPath);
                    console.log('Czy jesteśmy na liście produktów:', isChangelist);
                    
                    if (!isChangelist) {
                        console.log('⚠️ NIE jesteśmy na liście produktów - czekam dalej...');
                        return { skip_wait: false, waiting_for_changelist: true, current_path: currentPath };
                    }
                    
                    console.log('✅ Jesteśmy na liście produktów');
                    return { skip_wait: false, on_changelist: true, current_path: currentPath };
                })()'''
            },
            # Poczekaj na załadowanie listingu
            {
                'type': 'wait_for',
                'selector': 'table.changelist tbody tr, table#result_list tbody tr, table tbody tr',
                'timeout': 20000  # Zwiększony timeout
            },
            # Dodatkowe sprawdzenie czy tabela jest załadowana
            {
                'type': 'evaluate',
                'expression': '''(() => {
                    console.log('=== SPRAWDZANIE CZY TABELA JEST ZAŁADOWANA ===');
                    const table = document.querySelector('table#result_list tbody');
                    const rows = table ? table.querySelectorAll('tr') : [];
                    console.log('Liczba wierszy w tabeli:', rows.length);
                    console.log('Tabela istnieje:', !!table);
                    
                    if (rows.length === 0) {
                        console.log('⚠️ Tabela jest pusta lub nie załadowana');
                        return { table_loaded: false, rows_count: 0 };
                    }
                    
                    console.log('✅ Tabela jest załadowana, liczba wierszy:', rows.length);
                    return { table_loaded: true, rows_count: rows.length };
                })()'''
            },
            # Przejdź do następnego niezmapowanego produktu z listy (z limitem max_products)
            {
                'type': 'evaluate',
                'expression': f'''(() => {{
                    // Sprawdź limit przetworzonych produktów
                    const productsProcessed = parseInt(sessionStorage.getItem('products_processed') || '0');
                    const maxProducts = {max_products};
                    
                    if (productsProcessed >= maxProducts) {{
                        return {{
                            next_product_found: false,
                            reason: 'max_products_reached',
                            products_processed: productsProcessed,
                            max_products: maxProducts,
                            message: `Osiągnięto limit {max_products} produktów`
                        }};
                    }}
                    
                    // Znajdź pierwszy produkt z listy, który nie jest jeszcze zmapowany
                    // Użyj różnych selektorów dla kompatybilności
                    let rows = document.querySelectorAll('table#result_list tbody tr');
                    if (rows.length === 0) {{
                        rows = document.querySelectorAll('table.changelist tbody tr');
                    }}
                    if (rows.length === 0) {{
                        rows = document.querySelectorAll('table tbody tr');
                    }}
                    let nextProductLink = null;
                    
                    console.log('=== SZUKANIE NASTĘPNEGO NIEZMAPOWANEGO PRODUKTU ===');
                    console.log('Liczba wierszy w tabeli:', rows.length);
                    
                    for (let idx = 0; idx < rows.length; idx++) {{
                        const row = rows[idx];
                        const link = row.querySelector('td.field-name a');
                        const isMappedCell = row.querySelector('td.field-is_mapped');
                        
                        // Sprawdź is_mapped na kilka sposobów
                        const isMappedText = isMappedCell?.textContent?.trim() || '';
                        const isMappedImg = isMappedCell?.querySelector('img[alt="True"]') !== null;
                        const isMapped = isMappedText === 'True' || isMappedImg;
                        
                        const productName = link?.textContent?.trim() || '';
                        const productId = link?.href?.match(/\\/(\\d+)\\/change\\//)?.[1] || 'unknown';
                        
                        console.log('Wiersz ' + (idx + 1) + ': ID=' + productId + ', Nazwa="' + productName.substring(0, 50) + '...", is_mapped=' + isMapped);
                        
                        if (link && !isMapped) {{
                            nextProductLink = link.href;
                            console.log('Znaleziono niezmapowany produkt: ' + nextProductLink);
                            break;
                        }} else if (link && isMapped) {{
                            console.log('Produkt ' + productId + ' jest już zmapowany - pomijam');
                        }}
                    }}
                    
                    if (!nextProductLink) {{
                        console.log('❌ Nie znaleziono żadnego niezmapowanego produktu');
                    }}
                    
                    if (nextProductLink) {{
                        console.log('Przechodzę do następnego produktu po utworzeniu - zwracam URL do nawigacji przez Playwright:', nextProductLink);
                        return {{
                            next_product_found: true,
                            next_product_url: nextProductLink,
                            navigate_to_url: nextProductLink,  // URL do nawigacji przez Playwright
                            products_processed: productsProcessed,
                            max_products: maxProducts
                        }};
                    }}
                    
                    return {{
                        next_product_found: false,
                        reason: 'no_unmapped_products',
                        total_rows: rows.length,
                        products_processed: productsProcessed
                    }};
                }})()'''
            },
            # Poczekaj na przeładowanie strony po nawigacji
            {
                'type': 'wait',
                'seconds': 3
            },
            # Poczekaj na załadowanie strony następnego produktu
            {
                'type': 'wait_for',
                'selector': '.form-row, fieldset, input[name="name"]',
                'timeout': 15000
            },
            # Końcowe sprawdzenie - jeśli nie ma więcej produktów lub osiągnięto limit, zatrzymaj automatyzację
            {
                'type': 'evaluate',
                'expression': f'''(() => {{
                    // Sprawdź limit przetworzonych produktów
                    const productsProcessed = parseInt(sessionStorage.getItem('products_processed') || '0');
                    const maxProducts = {max_products};
                    
                    if (productsProcessed >= maxProducts) {{
                        return {{
                            automation_completed: true,
                            reason: 'max_products_reached',
                            products_processed: productsProcessed,
                            max_products: maxProducts,
                            message: `Osiągnięto limit {max_products} produktów`
                        }};
                    }}
                    
                    // Sprawdź czy jesteśmy na stronie produktu czy na liście
                    const isProductPage = window.location.pathname.match(/\\/\\d+\\/change\\//);
                    const isChangelist = window.location.pathname.includes('/admin/matterhorn1/product/') && !isProductPage;
                    
                    if (isChangelist) {{
                        // Sprawdź czy są jeszcze niezmapowane produkty
                        // Użyj różnych selektorów dla kompatybilności
                        let rows = document.querySelectorAll('table#result_list tbody tr');
                        if (rows.length === 0) {{
                            rows = document.querySelectorAll('table.changelist tbody tr');
                        }}
                        if (rows.length === 0) {{
                            rows = document.querySelectorAll('table tbody tr');
                        }}
                        let hasUnmapped = false;
                        
                        for (const row of rows) {{
                            const isMappedCell = row.querySelector('td.field-is_mapped');
                            const isMapped = isMappedCell?.textContent?.trim() === 'True' || 
                                            isMappedCell?.querySelector('img[alt="True"]') !== null;
                            if (!isMapped) {{
                                hasUnmapped = true;
                                break;
                            }}
                        }}
                        
                        if (!hasUnmapped) {{
                            return {{
                                automation_completed: true,
                                reason: 'no_more_unmapped_products',
                                message: 'Wszystkie produkty zostały zmapowane',
                                products_processed: productsProcessed
                            }};
                        }}
                    }}
                    
                    return {{
                        automation_completed: false,
                        can_continue: true,
                        products_processed: productsProcessed,
                        max_products: maxProducts
                    }};
                }})()'''
            }
        ]
    }

    return config


def create_brand_automation_task_config(
    brand_id: int,
    brand_name: str,
    category_id: int = None,
    category_name: str = None,
    active: bool = True,
    is_mapped: bool = False,
    base_url: str = 'http://localhost:8080',
    username: str = None,
    password: str = None,
    env_file: str = '.env.dev',
    max_products: int = 10
) -> Dict[str, Any]:
    """
    Tworzy pełną konfigurację zadania automatyzacji dla marki z opcjonalnymi filtrami

    Args:
        brand_id: ID marki
        brand_name: Nazwa marki
        category_id: ID kategorii (opcjonalne)
        category_name: Nazwa kategorii (opcjonalne)
        active: Filtrowanie po statusie aktywności (True/False, opcjonalne)
        base_url: URL aplikacji
        username: Nazwa użytkownika (opcjonalne)
        password: Hasło (opcjonalne)
        env_file: Ścieżka do pliku .env

    Returns:
        Słownik z konfiguracją zadania dla WebAgentTask
    """
    config = get_brand_filter_config(
        brand_id=brand_id,
        brand_name=brand_name,
        category_id=category_id,
        category_name=category_name,
        active=active,
        is_mapped=is_mapped,
        base_url=base_url,
        username=username,
        password=password,
        env_file=env_file,
        max_products=max_products
    )

    # Utwórz nazwę zadania z informacją o filtrach
    name_parts = [f'Django Admin - Produkty marki: {brand_name}']
    if category_name:
        name_parts.append(f'Kategoria: {category_name}')
    if active is not None:
        name_parts.append(f'Aktywne: {"Tak" if active else "Nie"}')
    if is_mapped is not None:
        name_parts.append(f'Zmapowane: {"Tak" if is_mapped else "Nie"}')

    return {
        'name': ' | '.join(name_parts),
        'task_type': 'automation',
        'url': base_url,
        'config': config,
        'brand_id': brand_id,
        'brand_name': brand_name,
        'priority': 0  # Domyślny priorytet, można zmienić później
    }


def create_automation_tasks_for_all_brands(
    base_url: str = 'http://localhost:8080',
    username: str = None,
    password: str = None,
    env_file: str = '.env.dev',
    using: str = 'matterhorn1',
    category_id: int = None,
    category_name: str = None,
    active: bool = True,
    is_mapped: bool = False
) -> List[Dict[str, Any]]:
    """
    Tworzy konfiguracje zadań automatyzacji dla wszystkich marek

    Args:
        base_url: URL aplikacji Django
        username: Nazwa użytkownika (opcjonalne)
        password: Hasło (opcjonalne)
        env_file: Ścieżka do pliku .env
        using: Nazwa bazy danych
        category_id: ID kategorii (opcjonalne)
        category_name: Nazwa kategorii (opcjonalne)
        active: Filtrowanie po statusie aktywności (domyślnie: True)
        is_mapped: Filtrowanie po statusie mapowania (domyślnie: False - tylko niezmapowane)

    Returns:
        Lista słowników z konfiguracjami zadań
    """
    brands = get_all_brands(using=using)
    tasks = []

    for brand in brands:
        task_config = create_brand_automation_task_config(
            brand_id=brand['id'],
            brand_name=brand['name'],
            category_id=category_id,
            category_name=category_name,
            active=active,
            is_mapped=is_mapped,
            base_url=base_url,
            username=username,
            password=password,
            env_file=env_file
        )
        tasks.append(task_config)

    return tasks
