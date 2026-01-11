"""
Custom PostgreSQL database backend z retry logic dla połączeń.
Obsługuje automatyczne ponawianie połączeń w przypadku timeoutów i błędów sieciowych.

Ten moduł rozszerza standardowy Django PostgreSQL backend o automatyczne ponawianie
połączeń w przypadku błędów sieciowych i timeoutów.
"""
import time
import logging
from django.db.backends.postgresql.base import DatabaseWrapper as PostgreSQLDatabaseWrapper
from django.db.backends.postgresql.base import Database as PostgreSQLDatabase
from django.db import OperationalError, InterfaceError
from django.db.utils import DatabaseError
from psycopg2 import OperationalError as Psycopg2OperationalError

# Nie importujemy tutaj - Django załaduje je osobno gdy będzie potrzebował

# Eksportujemy Database dla kompatybilności
Database = PostgreSQLDatabase

logger = logging.getLogger(__name__)

# Typy błędów, które powinny być ponawiane
RETRYABLE_ERRORS = (
    OperationalError,
    InterfaceError,
    Psycopg2OperationalError,
)

# Słowa kluczowe w komunikacie błędu, które wskazują na problemy sieciowe/timeout
RETRYABLE_ERROR_KEYWORDS = (
    'timeout',
    'timed out',
    'connection',
    'network',
    'refused',
    'unreachable',
    'broken pipe',
    'closed',
    'lost connection',
    'server closed',
)


def is_retryable_error(error):
    """
    Sprawdza czy błąd jest typu, który powinien być ponawiany.
    
    Args:
        error: Wyjątek do sprawdzenia
        
    Returns:
        bool: True jeśli błąd powinien być ponawiany
    """
    # Sprawdź typ błędu
    if isinstance(error, RETRYABLE_ERRORS):
        # Sprawdź komunikat błędu
        error_str = str(error).lower()
        return any(keyword in error_str for keyword in RETRYABLE_ERROR_KEYWORDS)
    return False


class DatabaseWrapper(PostgreSQLDatabaseWrapper):
    """
    Custom database wrapper z retry logic.
    Rozszerza standardowy PostgreSQL backend o automatyczne ponawianie połączeń.
    """
    # Django wymaga, aby te klasy były zdefiniowane jako atrybuty klasy
    # Używamy standardowych klas z PostgreSQL (będą ustawione poniżej)
    vendor = 'postgresql'
    display_name = 'PostgreSQL z retry logic'
    
    def __init__(self, *args, **kwargs):
        """Inicjalizacja z ustawieniami retry."""
        super().__init__(*args, **kwargs)
        
        # Pobierz ustawienia retry z konfiguracji
        from django.conf import settings
        retry_config = getattr(settings, 'DATABASE_RETRY_CONFIG', {})
        
        # Ustawienia retry per database lub globalne
        self.max_retries = retry_config.get('max_retries', 3)
        self.retry_delay = retry_config.get('retry_delay', 2)  # Sekundy
        self.retry_backoff = retry_config.get('retry_backoff', True)  # Exponential backoff
        self.retry_max_delay = retry_config.get('retry_max_delay', 30)  # Maksymalne opóźnienie
    
    def get_new_connection(self, conn_params):
        """
        Tworzy nowe połączenie z retry logic.
        
        Args:
            conn_params: Parametry połączenia
            
        Returns:
            Connection: Nowe połączenie z bazą danych
            
        Raises:
            OperationalError: Jeśli wszystkie próby połączenia zakończyły się niepowodzeniem
        """
        last_error = None
        
        for attempt in range(self.max_retries + 1):
            try:
                logger.debug(
                    f"[DB Retry] Próba połączenia {attempt + 1}/{self.max_retries + 1} "
                    f"do bazy {self.alias} (host: {conn_params.get('host', 'unknown')})"
                )
                
                # Próba połączenia
                connection = super().get_new_connection(conn_params)
                
                if attempt > 0:
                    logger.info(
                        f"[DB Retry] ✓ Połączenie z bazą {self.alias} udane po {attempt + 1} próbach"
                    )
                
                return connection
                
            except RETRYABLE_ERRORS as e:
                last_error = e
                
                if not is_retryable_error(e):
                    # Błąd nie jest retryable - rzuć go natychmiast
                    logger.error(
                        f"[DB Retry] ✗ Błąd nie-retryable podczas połączenia z bazą {self.alias}: {e}"
                    )
                    raise
                
                # Jeśli to ostatnia próba, rzuć błąd
                if attempt >= self.max_retries:
                    logger.error(
                        f"[DB Retry] ✗ Wyczerpano wszystkie próby połączenia z bazą {self.alias} "
                        f"({self.max_retries + 1} prób). Ostatni błąd: {e}"
                    )
                    raise
                
                # Oblicz opóźnienie przed następną próbą
                if self.retry_backoff:
                    # Exponential backoff: delay * 2^attempt, z maksymalnym limitem
                    delay = min(
                        self.retry_delay * (2 ** attempt),
                        self.retry_max_delay
                    )
                else:
                    delay = self.retry_delay
                
                logger.warning(
                    f"[DB Retry] ⏳ Błąd połączenia z bazą {self.alias} (próba {attempt + 1}/{self.max_retries + 1}): {e}. "
                    f"Ponowienie za {delay:.1f}s..."
                )
                
                time.sleep(delay)
            
            except Exception as e:
                # Nieoczekiwany błąd - rzuć go natychmiast bez retry
                logger.error(
                    f"[DB Retry] ✗ Nieoczekiwany błąd podczas połączenia z bazą {self.alias}: {type(e).__name__}: {e}"
                )
                raise
        
        # Jeśli dotarliśmy tutaj (nie powinno się zdarzyć), rzuć ostatni błąd
        if last_error:
            raise last_error
        raise OperationalError("Nie udało się nawiązać połączenia z bazą danych")
    
    def ensure_connection(self):
        """
        Zapewnia aktywne połączenie z bazą danych.
        Retry logic dla nowych połączeń jest w get_new_connection().
        Tutaj używamy super() aby uniknąć rekurencji.
        """
        # Używamy super() aby uniknąć rekurencji
        # super().ensure_connection() wywoła get_new_connection(), gdzie mamy retry logic
        super().ensure_connection()
        
        # Jeśli connection istnieje ale jest zamknięte, spróbuj ponownie z retry
        if self.connection is not None:
            try:
                # Sprawdź bezpośrednio czy połączenie jest zamknięte (bez wywoływania cursor)
                if hasattr(self.connection, 'closed') and self.connection.closed:
                    logger.warning(
                        f"[DB Retry] Połączenie z bazą {self.alias} jest zamknięte. Próba ponownego połączenia..."
                    )
                    # Zamknij i połącz ponownie
                    self.connection = None
                    # Wywołaj ponownie, co spowoduje wywołanie get_new_connection() z retry
                    super().ensure_connection()
            except Exception:
                # Jeśli sprawdzanie połączenia nie działa, po prostu kontynuuj
                pass


# Używamy bezpośrednio klas z PostgreSQL (zgodnie z dokumentacją Django)
# Django automatycznie użyje tych klas, jeśli nie są zdefiniowane jako atrybuty klasy
# DatabaseWrapper dziedziczy wszystkie potrzebne klasy z PostgreSQLDatabaseWrapper

# Django wymaga, aby DatabaseWrapper był dostępny bezpośrednio
__all__ = ['Database', 'DatabaseWrapper']
