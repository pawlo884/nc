"""
Middleware do dynamicznego kontrolowania DEBUG na podstawie IP klienta.
"""
import threading

# Thread-local storage dla DEBUG
_thread_locals = threading.local()


def get_debug():
    """Zwraca aktualną wartość DEBUG dla bieżącego wątku."""
    return getattr(_thread_locals, 'debug', False)


def set_debug(value):
    """Ustawia wartość DEBUG dla bieżącego wątku."""
    _thread_locals.debug = value


class DynamicDebugMiddleware:
    """
    Middleware które automatycznie ustawia DEBUG na False dla zewnętrznych IP
    i True dla localhost/127.0.0.1.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Sprawdź IP klienta - uwzględnij nginx reverse proxy
        remote_addr = request.META.get('REMOTE_ADDR', '')
        http_host = request.META.get('HTTP_HOST', '')
        
        # Sprawdź X-Forwarded-For (gdy za nginx)
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR', '')
        if x_forwarded_for:
            # X-Forwarded-For może zawierać wiele IP (klient, proxy)
            # Bierzemy pierwsze IP (prawdziwy klient)
            client_ip = x_forwarded_for.split(',')[0].strip()
        else:
            client_ip = remote_addr
        
        # Lista lokalnych adresów IP
        localhost_ips = ['127.0.0.1', 'localhost', '::1', '0.0.0.0']
        localhost_hosts = ['localhost', '127.0.0.1']
        
        # Sprawdź czy to localhost
        is_localhost = (
            client_ip in localhost_ips or
            remote_addr in localhost_ips or
            any(host in http_host for host in localhost_hosts)
        )
        
        # Ustaw DEBUG na podstawie IP
        # True dla localhost, False dla zewnętrznych IP
        set_debug(is_localhost)
        
        # Dodaj atrybut do request dla łatwego dostępu
        request.is_localhost = is_localhost
        
        response = self.get_response(request)
        return response
