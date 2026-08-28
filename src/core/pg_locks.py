"""
Rozproszone blokady oparte o PostgreSQL advisory locks.

Zastępują wcześniejszy wzorzec `cache.add(key, id, ttl)` na Redisie dla krótkich
blokad tasków Celery (tabu, mada). Zalety względem blokady z TTL w cache:

* brak "martwych" blokad - advisory lock zwalnia się automatycznie, gdy proces
  trzymający połączenie padnie (nie trzeba watchdogów czyszczących lock),
* brak ryzyka, że blokada wygaśnie w trakcie długiego importu (żaden TTL),
* jedno mniej zastosowanie Redisa.

Blokada jest trzymana na DEDYKOWANYM połączeniu do bazy (nie na połączeniu ORM),
żeby recykling połączeń Django w trakcie taska jej nie zerwał. Połączenie jest
zamykane w bloku `finally`, co również zwalnia lock.

Użycie:

    from core.pg_locks import advisory_lock

    with advisory_lock('tabu:sync_tabu_stock') as acquired:
        if not acquired:
            return {'status': 'skipped', 'reason': 'already_running'}
        ...  # sekcja krytyczna
"""
from __future__ import annotations

import contextlib
import hashlib
import logging
from typing import Iterator

from django.db import connections

logger = logging.getLogger(__name__)

# Pierwszy klucz 2-argumentowego advisory locka - stała "przestrzeń nazw" projektu
# ('nc' w ASCII), żeby nie kolidować z ewentualnymi lockami bibliotek trzecich.
_LOCK_NAMESPACE = 0x6E63  # 28259


def _lock_keys(name: str) -> tuple[int, int]:
    """Zamienia nazwę blokady na parę int4 dla pg_*advisory_lock(key1, key2)."""
    digest = hashlib.blake2b(name.encode('utf-8'), digest_size=4).digest()
    key2 = int.from_bytes(digest, 'big', signed=True)  # int4 (signed)
    return _LOCK_NAMESPACE, key2


@contextlib.contextmanager
def advisory_lock(name: str, *, using: str = 'default', blocking: bool = False) -> Iterator[bool]:
    """
    Context manager zwracający informację, czy blokada `name` została zdobyta.

    blocking=False (domyślnie): próbuje raz (pg_try_advisory_lock); yield True/False.
    blocking=True: czeka aż lock będzie wolny (pg_advisory_lock); zawsze yield True.

    Blokada jest zwalniana przy wyjściu z bloku (pg_advisory_unlock + zamknięcie
    dedykowanego połączenia).
    """
    key1, key2 = _lock_keys(name)
    conn = connections.create_connection(using)
    acquired = False
    try:
        with conn.cursor() as cursor:
            if blocking:
                cursor.execute('SELECT pg_advisory_lock(%s, %s)', [key1, key2])
                acquired = True
            else:
                cursor.execute('SELECT pg_try_advisory_lock(%s, %s)', [key1, key2])
                acquired = bool(cursor.fetchone()[0])
        if acquired:
            logger.debug('advisory_lock: zdobyto blokadę %r', name)
        else:
            logger.debug('advisory_lock: blokada %r zajęta', name)
        yield acquired
    finally:
        try:
            if acquired:
                with conn.cursor() as cursor:
                    cursor.execute('SELECT pg_advisory_unlock(%s, %s)', [key1, key2])
        except Exception:  # pragma: no cover - zwalnia się i tak przy close()
            logger.warning('advisory_lock: nie udało się jawnie zwolnić %r', name, exc_info=True)
        finally:
            conn.close()
