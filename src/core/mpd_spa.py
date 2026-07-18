"""Serwowanie zbudowanego React SPA MPD pod /mpd-app/."""

from __future__ import annotations

import mimetypes
from pathlib import Path

from django.conf import settings
from django.core.exceptions import SuspiciousFileOperation
from django.http import FileResponse, Http404, HttpResponse
from django.utils._os import safe_join


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
        try:
            # safe_join blokuje path traversal (.., absolutne ścieżki)
            filepath = Path(safe_join(str(root_resolved), relative))
        except SuspiciousFileOperation as exc:
            raise Http404 from exc
        if filepath.is_file():
            content_type, _ = mimetypes.guess_type(str(filepath))
            return FileResponse(
                filepath.open('rb'),
                content_type=content_type or 'application/octet-stream',
            )

    index = root_resolved / 'index.html'
    if not index.is_file():
        raise Http404('Brak index.html w buildzie MPD SPA.')

    return HttpResponse(
        index.read_text(encoding='utf-8'),
        content_type='text/html; charset=utf-8',
    )
