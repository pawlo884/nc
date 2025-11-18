"""
Wzorce i konfiguracja dla każdej marki - używane przez automatyzację i AI
"""
from typing import Dict, List, Optional, Any
import re


# Konfiguracja wzorców dla każdej marki
BRAND_PATTERNS: Dict[str, Dict[str, Any]] = {
    'marko': {
        'name': 'Marko',
        'brand_id': 28,

        # Wzorce do formatowania nazwy produktu dla MPD
        'name_formatting': {
            'pattern': r'Model\s+([A-Za-z]+(?:\s+[A-Za-z]+)*?)(?:\s+M-\d+)',
            'alt_pattern': r'Kostium\s+(?:dwuczęściowy\s+)?kąpielowy\s+([A-Za-z]+(?:\s+[A-Za-z]+)*?)(?:\s+M-\d+|\s+Model)',
            'simple_pattern': r'Model\s+([A-Za-z]+)',
            'output_template': 'Kostium kąpielowy {model_name}',
            'description': 'Format: "Kostium dwuczęściowy Kostium kąpielowy Model {MODEL_NAME} M-XXX (X) {COLOR} - Marko" -> "Kostium kąpielowy {MODEL_NAME}"'
        },

        # Wzorce do wyciągania koloru producenta z nazwy
        'producer_color': {
            'pattern': r'\([^)]+\)\s+([^-]+?)\s*-\s*Marko',
            'alt_pattern': r'\([^)]+\)\s+([A-Za-z/]+(?:\s+[A-Za-z]+)*)',
            'description': 'Wyciąga pełną nazwę koloru (np. "Red Ferrari", "Yellow/Pink") z nazwy produktu'
        },

        # Wzorce do wyciągania kodu producenta
        'producer_code': {
            'pattern': r'M-(\d{3})',
            'output_template': 'M-{code}',
            'description': 'Wyciąga kod producenta w formacie M-XXX'
        },

        # Mapowanie kolorów (nazwa z API -> nazwa standardowa)
        'color_mapping': {
            'żółty': 'Yellow',
            'yellow': 'Yellow',
            'czerwony': 'Red',
            'red': 'Red',
            'niebieski': 'Blue',
            'blue': 'Blue',
            'zielony': 'Green',
            'green': 'Green',
            'czarny': 'Black',
            'black': 'Black',
            'biały': 'White',
            'white': 'White',
            'różowy': 'Pink',
            'pink': 'Pink',
            'pomarańczowy': 'Orange',
            'orange': 'Orange',
            'fioletowy': 'Violet',
            'violet': 'Violet',
            'purple': 'Violet',
            'szary': 'Grey',
            'grey': 'Grey',
            'gray': 'Grey',
            'beżowy': 'Beige',
            'beige': 'Beige',
            'brązowy': 'Brown',
            'brown': 'Brown',
            'mocca': 'Mocca',
            'mokka': 'Mocca',
        },

        # Wzorce do wyciągania informacji o produkcie z opisu (dla AI)
        'description_patterns': {
            'materials': [
                r'(\d+)\s*%\s*([A-Za-z]+)',
                r'([A-Za-z]+)\s+(\d+)\s*%',
            ],
            'sizes': [
                r'rozmiar[:\s]+([A-Z0-9,/\s]+)',
                r'size[:\s]+([A-Z0-9,/\s]+)',
            ],
            'attributes': {
                'fiszbinach': 'na fiszbinach',
                'usztywnianych miseczkach': 'usztywniane miseczki',
                'niski krój': 'niski stan',
                'wiązanie na szyi': 'wiązane na szyi',
                'regulowane': 'regulowane',
                'gładkie': 'gładkie',
            }
        },

        # Domyślne wartości dla produktów tej marki
        'defaults': {
            'size_category': 'bielizna',
            'unit': 'szt.',
            'paths': {
                'kostium dwuczęściowy': 'Dwuczęściowe',
                'kostium jednoczęściowy': 'Jednoczęściowe',
            }
        }
    },

    # Można dodać więcej marek tutaj
    # 'gatta': {
    #     'name': 'Gatta',
    #     'brand_id': 29,
    #     ...
    # },
}


def get_brand_patterns(brand_name: str) -> Optional[Dict[str, Any]]:
    """
    Pobiera wzorce dla danej marki

    Args:
        brand_name: Nazwa marki (case-insensitive)

    Returns:
        Słownik z wzorcami dla marki lub None jeśli marka nie istnieje
    """
    brand_key = brand_name.lower().strip()
    return BRAND_PATTERNS.get(brand_key)


def format_product_name(product_name: str, brand_name: str) -> str:
    """
    Formatuje nazwę produktu zgodnie z wzorcami marki

    Args:
        product_name: Oryginalna nazwa produktu
        brand_name: Nazwa marki

    Returns:
        Sformatowana nazwa produktu
    """
    patterns = get_brand_patterns(brand_name)
    if not patterns or 'name_formatting' not in patterns:
        return product_name.strip()

    name_config = patterns['name_formatting']

    # Spróbuj głównego wzorca
    match = re.search(name_config['pattern'], product_name)
    if match:
        model_name = match.group(1).strip()
        return name_config['output_template'].format(model_name=model_name)

    # Spróbuj alternatywnego wzorca
    if 'alt_pattern' in name_config:
        alt_match = re.search(name_config['alt_pattern'], product_name)
        if alt_match:
            model_name = alt_match.group(1).strip()
            return name_config['output_template'].format(model_name=model_name)

    # Spróbuj prostego wzorca
    if 'simple_pattern' in name_config:
        simple_match = re.search(name_config['simple_pattern'], product_name)
        if simple_match:
            model_name = simple_match.group(1).strip()
            return name_config['output_template'].format(model_name=model_name)

    # Fallback - zwróć oryginalną nazwę
    return product_name.strip()


def extract_producer_color(product_name: str, brand_name: str) -> Optional[str]:
    """
    Wyciąga kolor producenta z nazwy produktu

    Args:
        product_name: Nazwa produktu
        brand_name: Nazwa marki

    Returns:
        Kolor producenta lub None
    """
    patterns = get_brand_patterns(brand_name)
    if not patterns or 'producer_color' not in patterns:
        return None

    color_config = patterns['producer_color']

    # Spróbuj głównego wzorca
    match = re.search(color_config['pattern'], product_name, re.IGNORECASE)
    if match:
        color = match.group(1).strip()
        # Sprawdź czy to nie jest kod (M-XXX)
        if not re.match(r'^M-\d+', color):
            return color

    # Spróbuj alternatywnego wzorca
    if 'alt_pattern' in color_config:
        alt_match = re.search(color_config['alt_pattern'], product_name)
        if alt_match:
            color = alt_match.group(1).strip()
            if not re.match(r'^M-\d+', color):
                return color

    return None


def extract_producer_code(product_name: str, brand_name: str) -> Optional[str]:
    """
    Wyciąga kod producenta z nazwy produktu

    Args:
        product_name: Nazwa produktu
        brand_name: Nazwa marki

    Returns:
        Kod producenta lub None
    """
    patterns = get_brand_patterns(brand_name)
    if not patterns or 'producer_code' not in patterns:
        return None

    code_config = patterns['producer_code']

    match = re.search(code_config['pattern'], product_name)
    if match:
        code = match.group(1)
        if 'output_template' in code_config:
            return code_config['output_template'].format(code=code)
        return f"M-{code}"

    return None


def map_color(color_name: str, brand_name: str) -> str:
    """
    Mapuje kolor z API na standardową nazwę koloru

    Args:
        color_name: Nazwa koloru z API
        brand_name: Nazwa marki

    Returns:
        Zmapowana nazwa koloru lub oryginalna jeśli brak mapowania
    """
    patterns = get_brand_patterns(brand_name)
    if not patterns or 'color_mapping' not in patterns:
        return color_name

    color_mapping = patterns['color_mapping']
    color_lower = color_name.lower().strip()

    return color_mapping.get(color_lower, color_name)


def get_default_value(brand_name: str, field: str) -> Optional[Any]:
    """
    Pobiera domyślną wartość dla pola produktu danej marki

    Args:
        brand_name: Nazwa marki
        field: Nazwa pola (np. 'size_category', 'unit')

    Returns:
        Domyślna wartość lub None
    """
    patterns = get_brand_patterns(brand_name)
    if not patterns or 'defaults' not in patterns:
        return None

    defaults = patterns['defaults']
    return defaults.get(field)


def get_path_for_product(product_name: str, brand_name: str) -> Optional[str]:
    """
    Określa ścieżkę produktu na podstawie nazwy

    Args:
        product_name: Nazwa produktu
        brand_name: Nazwa marki

    Returns:
        Nazwa ścieżki lub None
    """
    patterns = get_brand_patterns(brand_name)
    if not patterns or 'defaults' not in patterns:
        return None

    defaults = patterns['defaults']
    if 'paths' not in defaults:
        return None

    paths = defaults['paths']
    product_lower = product_name.lower()

    for key, path_value in paths.items():
        if key in product_lower:
            return path_value

    return None


def get_description_patterns(brand_name: str) -> Optional[Dict[str, Any]]:
    """
    Pobiera wzorce do analizy opisu produktu (dla AI)

    Args:
        brand_name: Nazwa marki

    Returns:
        Słownik z wzorcami lub None
    """
    patterns = get_brand_patterns(brand_name)
    if not patterns:
        return None

    return patterns.get('description_patterns')


def get_all_brand_names() -> List[str]:
    """
    Zwraca listę wszystkich dostępnych nazw marek

    Returns:
        Lista nazw marek
    """
    return [patterns['name'] for patterns in BRAND_PATTERNS.values()]


def get_brand_id(brand_name: str) -> Optional[int]:
    """
    Pobiera ID marki na podstawie nazwy

    Args:
        brand_name: Nazwa marki

    Returns:
        ID marki lub None
    """
    patterns = get_brand_patterns(brand_name)
    if not patterns:
        return None

    return patterns.get('brand_id')
