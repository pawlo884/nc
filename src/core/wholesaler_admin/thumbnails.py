from urllib.parse import urlparse

from django.utils.html import format_html

_PLACEHOLDER_SVG = (
    "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNTYiIGhlaWdodD0iNTYiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+"
    "PHJlY3Qgd2lkdGg9IjU2IiBoZWlnaHQ9IjU2IiBmaWxsPSIjZWVlIi8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtZmFtaWx5PSJBcmlhbCIg"
    "Zm9udC1zaXplPSI4IiBmaWxsPSIjOTk5IiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBkeT0iLjNlbSI+YnJhayB6ZGo8L3RleHQ+PC9zdmc+"
)


def resolve_thumbnail_url(original_url, *, fallback_host, storage_prefixes=(), storage_resolver=None):
    """Zamienia zapisany (ewentualnie względny / z gołym hostname) URL obrazu na
    absolutny URL do wyświetlenia.

    - storage_prefixes + storage_resolver: opcjonalne przepisanie URL-i przechowywanych
      w zewnętrznym storage (np. MinIO), gdy zaczynają się od jednego z prefiksów.
    - fallback_host: host CDN/strony hurtowni używany, gdy URL nie jest absolutny
      i nie pasuje do storage_prefixes.
    """
    normalized = (original_url or '').strip()
    if not normalized:
        return None
    if normalized.startswith(('http://', 'https://')):
        return normalized
    if normalized.startswith('//'):
        return f"https:{normalized}"
    if storage_prefixes and normalized.startswith(storage_prefixes) and storage_resolver:
        return storage_resolver(normalized) or normalized

    # Hostname przez urlparse (nie substring) — py/incomplete-url-substring-sanitization
    candidate = normalized if '://' in normalized else f'https://{normalized.lstrip("/")}'
    host = (urlparse(candidate).hostname or '').lower()
    if host == fallback_host or host.endswith(f'.{fallback_host}'):
        return candidate if candidate.startswith('http') else f'https://{normalized.lstrip("/")}'
    return f"https://{fallback_host}/{normalized.lstrip('/')}"


def render_product_thumbnail(original_url, *, fallback_host, storage_prefixes=(), storage_resolver=None):
    """Renderuje miniaturę produktu na liście adminowej jako <a><img onerror=placeholder></a>,
    albo '-' gdy brak URL-a."""
    if not original_url:
        return '-'
    display_url = resolve_thumbnail_url(
        original_url, fallback_host=fallback_host,
        storage_prefixes=storage_prefixes, storage_resolver=storage_resolver,
    )
    return format_html(
        '<a href="{}" target="_blank" title="{}">'
        '<img src="{}" alt="Obraz produktu" loading="lazy" width="56" height="56" '
        'style="object-fit: contain; width: 56px; height: 56px; max-width: 56px; max-height: 56px;" '
        'onerror="this.onerror=null; this.src=\'{}\';" /></a>',
        display_url, original_url, display_url, _PLACEHOLDER_SVG,
    )
