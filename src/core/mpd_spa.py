"""Serwowanie zbudowanego React SPA MPD pod /mpd-app/."""

from __future__ import annotations

import mimetypes
from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404, HttpResponse


def mpd_spa(request, path: str = ''):
    """
    Serwuje pliki z MPD_SPA_ROOT; nieznane ścieżki → index.html (React Router).
    """
    root = Path(getattr(settings, 'MPD_SPA_ROOT', ''))
    if not root.is_dir():
        raise Http404('MPD React SPA nie jest zbudowane (brak MPD_SPA_ROOT).')

    root_resolved = root.resolve()
    relative = (path or '').lstrip('/')

    if relative:
        candidate = (root / relative).resolve()
        try:
            candidate.relative_to(root_resolved)
        except ValueError as exc:
            raise Http404 from exc
        if candidate.is_file():
            content_type, _ = mimetypes.guess_type(str(candidate))
            return FileResponse(
                candidate.open('rb'),
                content_type=content_type or 'application/octet-stream',
            )

    index = root_resolved / 'index.html'
    if not index.is_file():
        raise Http404('Brak index.html w buildzie MPD SPA.')

    return HttpResponse(
        index.read_text(encoding='utf-8'),
        content_type='text/html; charset=utf-8',
    )
