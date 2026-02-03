"""
Middleware do dynamicznego kontrolowania DEBUG na podstawie IP klienta
oraz blokowania botów i crawlerów.
"""
import threading
import re
from django.http import HttpResponseForbidden

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


class BotBlockerMiddleware:
    """
    Middleware do blokowania znanych botów i crawlerów.
    Można skonfigurować przez zmienne środowiskowe:
    - BOT_BLOCKER_ENABLED=True/False (domyślnie True)
    - BOT_BLOCKER_ALLOWED_BOTS=Googlebot,Bingbot (oddzielone przecinkami)
    """
    
    # Lista znanych botów/crawlerów do blokowania
    BLOCKED_USER_AGENTS = [
        r'bot', r'crawler', r'spider', r'scraper',
        r'curl', r'wget', r'python-requests', r'python-urllib',
        r'http', r'libwww', r'fetch', r'getright',
        r'go-http-client', r'java', r'perl', r'ruby',
        r'scrapy', r'mechanize', r'phantomjs', r'selenium',
        r'headless', r'postman', r'insomnia', r'httpie',
    ]
    
    # Dozwolone boty (np. Googlebot, Bingbot dla SEO)
    ALLOWED_BOTS = [
        'googlebot', 'bingbot', 'slurp', 'duckduckbot',
        'baiduspider', 'yandexbot', 'facebookexternalhit',
    ]
    
    def __init__(self, get_response):
        self.get_response = get_response
        import os
        # Sprawdź czy blokowanie jest włączone
        self.enabled = os.getenv('BOT_BLOCKER_ENABLED', 'True').lower() in ('true', '1', 'yes', 'on')
        
        # Pobierz dozwolone boty z zmiennej środowiskowej
        allowed_bots_env = os.getenv('BOT_BLOCKER_ALLOWED_BOTS', '')
        if allowed_bots_env:
            self.allowed_bots = [bot.strip().lower() for bot in allowed_bots_env.split(',')]
        else:
            self.allowed_bots = [bot.lower() for bot in self.ALLOWED_BOTS]
        
        # Kompiluj regex dla lepszej wydajności
        self.blocked_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.BLOCKED_USER_AGENTS]
    
    def __call__(self, request):
        if not self.enabled:
            return self.get_response(request)
        
        # Pomijaj health check endpoint - musi być dostępny dla Docker health checks
        if request.path == '/health/' or request.path == '/health':
            return self.get_response(request)
        
        # Requesty z zaufanego proxy (nc-nginx-router, NPM itd.) – nie blokuj po User-Agent,
        # bo łańcuch proxy mógł go zmienić (np. Wget/curl), a prawdziwy klient to przeglądarka
        remote_addr = request.META.get('REMOTE_ADDR', '')
        if remote_addr:
            if remote_addr == '127.0.0.1' or remote_addr == '::1':
                return self.get_response(request)
            if remote_addr.startswith('10.') or remote_addr.startswith('172.') or remote_addr.startswith('192.168.'):
                return self.get_response(request)
        
        # Sprawdź User-Agent
        user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
        
        if not user_agent:
            # Brak User-Agent - podejrzane, ale nie blokujemy (może być normalny klient)
            return self.get_response(request)
        
        # Sprawdź czy to dozwolony bot
        for allowed_bot in self.allowed_bots:
            if allowed_bot in user_agent:
                return self.get_response(request)
        
        # Sprawdź czy User-Agent pasuje do zablokowanych wzorców
        for pattern in self.blocked_patterns:
            if pattern.search(user_agent):
                # Zablokuj request
                return HttpResponseForbidden(
                    '<h1>403 Forbidden</h1>'
                    '<p>Access denied. Automated crawling is not allowed.</p>',
                    content_type='text/html'
                )
        
        return self.get_response(request)
