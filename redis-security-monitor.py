#!/usr/bin/env python3
"""
Redis Security Monitor
Monitoruje bezpieczeństwo Redis i wykrywa podejrzane aktywności
"""

import redis
import time
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any
import os

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/redis-security.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class RedisSecurityMonitor:
    def __init__(self, host='localhost', port=6379, password=None):
        """Inicjalizacja monitora bezpieczeństwa Redis"""
        self.redis_client = redis.Redis(
            host=host,
            port=port,
            password=password,
            decode_responses=True,
            socket_timeout=5,
            socket_connect_timeout=5
        )
        self.suspicious_activities = []
        self.failed_attempts = {}
        self.max_failed_attempts = 5
        self.block_duration = 300  # 5 minut

    def check_connection(self) -> bool:
        """Sprawdza połączenie z Redis"""
        try:
            self.redis_client.ping()
            return True
        except redis.ConnectionError as e:
            logger.error(f"Błąd połączenia z Redis: {e}")
            return False
        except redis.AuthenticationError as e:
            logger.error(f"Błąd autoryzacji Redis: {e}")
            return False

    def monitor_slow_queries(self) -> List[Dict]:
        """Monitoruje wolne zapytania"""
        try:
            slow_queries = self.redis_client.slowlog_get(10)
            suspicious_queries = []

            for query in slow_queries:
                if query['duration'] > 10000:  # > 10ms
                    suspicious_queries.append({
                        'timestamp': datetime.fromtimestamp(query['start_time']),
                        'duration': query['duration'],
                        'command': ' '.join(query['command']),
                        'client': query.get('client_addr', 'unknown')
                    })
                    logger.warning(
                        f"Wolne zapytanie: {query['duration']}ms - {query['command']}")

            return suspicious_queries
        except Exception as e:
            logger.error(f"Błąd monitorowania wolnych zapytań: {e}")
            return []

    def monitor_client_connections(self) -> Dict[str, Any]:
        """Monitoruje połączenia klientów"""
        try:
            client_list = self.redis_client.client_list()
            connections_info = {
                'total_connections': len(client_list),
                'suspicious_connections': [],
                'connection_details': []
            }

            for client in client_list:
                client_info = {
                    'addr': client.get('addr'),
                    'idle': int(client.get('idle', 0)),
                    'cmd': client.get('cmd'),
                    'user': client.get('user', 'default')
                }
                connections_info['connection_details'].append(client_info)

                # Wykrywanie podejrzanych połączeń
                if client_info['idle'] > 3600:  # > 1 godzina bezczynności
                    connections_info['suspicious_connections'].append(
                        client_info)
                    logger.warning(f"Podejrzane połączenie: {client_info}")

            return connections_info
        except Exception as e:
            logger.error(f"Błąd monitorowania połączeń: {e}")
            return {}

    def check_memory_usage(self) -> Dict[str, Any]:
        """Sprawdza użycie pamięci"""
        try:
            info = self.redis_client.info('memory')
            memory_info = {
                'used_memory': info.get('used_memory', 0),
                'used_memory_human': info.get('used_memory_human', '0B'),
                'maxmemory': info.get('maxmemory', 0),
                'maxmemory_human': info.get('maxmemory_human', '0B'),
                'memory_usage_percent': 0
            }

            if memory_info['maxmemory'] > 0:
                memory_info['memory_usage_percent'] = (
                    memory_info['used_memory'] / memory_info['maxmemory'] * 100
                )

                if memory_info['memory_usage_percent'] > 90:
                    logger.warning(
                        f"Wysokie użycie pamięci: {memory_info['memory_usage_percent']:.1f}%")

            return memory_info
        except Exception as e:
            logger.error(f"Błąd sprawdzania pamięci: {e}")
            return {}

    def detect_brute_force(self, client_addr: str) -> bool:
        """Wykrywa ataki brute force"""
        current_time = datetime.now()

        if client_addr not in self.failed_attempts:
            self.failed_attempts[client_addr] = []

        # Usuń stare próby
        self.failed_attempts[client_addr] = [
            attempt for attempt in self.failed_attempts[client_addr]
            if current_time - attempt < timedelta(seconds=self.block_duration)
        ]

        # Dodaj nową próbę
        self.failed_attempts[client_addr].append(current_time)

        # Sprawdź czy przekroczono limit
        if len(self.failed_attempts[client_addr]) >= self.max_failed_attempts:
            logger.critical(f"Wykryto atak brute force z {client_addr}")
            return True

        return False

    def generate_security_report(self) -> Dict[str, Any]:
        """Generuje raport bezpieczeństwa"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'connection_status': self.check_connection(),
            'slow_queries': self.monitor_slow_queries(),
            'client_connections': self.monitor_client_connections(),
            'memory_usage': self.check_memory_usage(),
            'failed_attempts': len(self.failed_attempts),
            'security_score': 100
        }

        # Oblicz wynik bezpieczeństwa
        if not report['connection_status']:
            report['security_score'] -= 20

        if report['slow_queries']:
            report['security_score'] -= len(report['slow_queries']) * 5

        if report['client_connections'].get('suspicious_connections'):
            report['security_score'] -= len(report['client_connections']
                                            ['suspicious_connections']) * 10

        if report['memory_usage'].get('memory_usage_percent', 0) > 90:
            report['security_score'] -= 15

        if report['failed_attempts'] > 0:
            report['security_score'] -= report['failed_attempts'] * 5

        report['security_score'] = max(0, report['security_score'])

        return report

    def run_monitoring(self, interval: int = 60):
        """Uruchamia monitoring w pętli"""
        logger.info("Uruchamianie monitora bezpieczeństwa Redis...")

        while True:
            try:
                report = self.generate_security_report()

                # Loguj raport
                logger.info(
                    f"Raport bezpieczeństwa: {json.dumps(report, indent=2, default=str)}")

                # Zapisz do pliku
                with open('logs/redis-security-report.json', 'w') as f:
                    json.dump(report, f, indent=2, default=str)

                # Sprawdź alerty
                if report['security_score'] < 70:
                    logger.critical(
                        f"Niski wynik bezpieczeństwa: {report['security_score']}")

                time.sleep(interval)

            except KeyboardInterrupt:
                logger.info("Zatrzymywanie monitora...")
                break
            except Exception as e:
                logger.error(f"Błąd monitorowania: {e}")
                time.sleep(interval)


def main():
    """Główna funkcja"""
    # Utwórz katalog na logi
    os.makedirs('logs', exist_ok=True)

    # Konfiguracja z zmiennych środowiskowych
    redis_host = os.getenv('REDIS_HOST', 'localhost')
    redis_port = int(os.getenv('REDIS_PORT', 6379))
    redis_password = os.getenv('REDIS_PASSWORD')

    monitor = RedisSecurityMonitor(
        host=redis_host,
        port=redis_port,
        password=redis_password
    )

    # Uruchom monitoring
    monitor.run_monitoring(interval=60)


if __name__ == "__main__":
    main()
