#!/usr/bin/env python3
"""
Nginx Security Monitor
Monitoruje logi nginx pod kątem podejrzanych żądań i ataków
"""

import re
import time
import subprocess
import logging
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from typing import Dict, List, Tuple

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/nginx_security.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class NginxSecurityMonitor:
    def __init__(self, log_file_path: str = "/var/log/nginx/access.log"):
        self.log_file_path = log_file_path
        self.suspicious_patterns = [
            r'CONNECT\s+\w+:\d+',  # CONNECT requests
            r'TRACE\s+',           # TRACE requests
            r'OPTIONS\s+',         # OPTIONS requests
            r'\.\./',              # Path traversal
            r'\.\.\\',             # Path traversal (Windows)
            r'\.\.%2f',            # URL encoded path traversal
            r'\.\.%5c',            # URL encoded path traversal (Windows)
            r'<script',            # XSS attempts
            r'union\s+select',     # SQL injection
            r'drop\s+table',       # SQL injection
            r'exec\s*\(',          # Command injection
            r'eval\s*\(',          # Code injection
        ]

        self.rate_limits = {
            'suspicious_requests': 10,  # per minute
            'failed_requests': 20,      # per minute
            'total_requests': 100,      # per minute
        }

        self.blocked_ips = set()
        self.request_counts = defaultdict(lambda: defaultdict(int))

    def parse_log_line(self, line: str) -> Dict:
        """Parsuje linię logu nginx"""
        # Standardowy format nginx access log
        pattern = r'(\d+\.\d+\.\d+\.\d+)\s+-\s+-\s+\[(.*?)\]\s+"([^"]*)"\s+(\d+)\s+(\d+)\s+"([^"]*)"\s+"([^"]*)"'
        match = re.match(pattern, line)

        if not match:
            return None

        return {
            'ip': match.group(1),
            'timestamp': match.group(2),
            'request': match.group(3),
            'status': int(match.group(4)),
            'size': int(match.group(5)),
            'referer': match.group(6),
            'user_agent': match.group(7)
        }

    def is_suspicious_request(self, log_entry: Dict) -> Tuple[bool, str]:
        """Sprawdza czy żądanie jest podejrzane"""
        if not log_entry:
            return False, ""

        request = log_entry['request']

        for pattern in self.suspicious_patterns:
            if re.search(pattern, request, re.IGNORECASE):
                return True, pattern

        # Sprawdź status kody błędów
        if log_entry['status'] in [400, 401, 403, 404, 405, 500, 502, 503]:
            return True, f"HTTP_{log_entry['status']}"

        return False, ""

    def check_rate_limits(self, ip: str, current_time: datetime) -> bool:
        """Sprawdza czy IP przekroczył limity"""
        minute_key = current_time.strftime("%Y-%m-%d %H:%M")

        # Resetuj stare dane (starsze niż 1 godzina)
        cutoff_time = current_time - timedelta(hours=1)
        for key in list(self.request_counts[ip].keys()):
            if key < cutoff_time.strftime("%Y-%m-%d %H:%M"):
                del self.request_counts[ip][key]

        # Sprawdź limity
        for limit_type, limit in self.rate_limits.items():
            if self.request_counts[ip][f"{minute_key}_{limit_type}"] > limit:
                return True

        return False

    def update_request_count(self, ip: str, current_time: datetime, is_suspicious: bool, status: int):
        """Aktualizuje liczniki żądań"""
        minute_key = current_time.strftime("%Y-%m-%d %H:%M")

        self.request_counts[ip][f"{minute_key}_total_requests"] += 1

        if is_suspicious:
            self.request_counts[ip][f"{minute_key}_suspicious_requests"] += 1

        if status >= 400:
            self.request_counts[ip][f"{minute_key}_failed_requests"] += 1

    def block_ip(self, ip: str, reason: str):
        """Blokuje IP w nginx"""
        if ip in self.blocked_ips:
            return

        try:
            # Dodaj regułę do nginx (wymaga restartu nginx)
            logger.warning(f"BLOCKING IP: {ip} - Reason: {reason}")
            self.blocked_ips.add(ip)

            # Tutaj można dodać automatyczne blokowanie przez iptables
            # subprocess.run(['iptables', '-A', 'INPUT', '-s', ip, '-j', 'DROP'])

        except Exception as e:
            logger.error(f"Failed to block IP {ip}: {e}")

    def analyze_logs(self, lines: List[str]):
        """Analizuje logi nginx"""
        current_time = datetime.now()
        ip_stats = defaultdict(lambda: {
            'total_requests': 0,
            'suspicious_requests': 0,
            'failed_requests': 0,
            'last_seen': current_time
        })

        for line in lines:
            log_entry = self.parse_log_line(line.strip())
            if not log_entry:
                continue

            ip = log_entry['ip']
            is_suspicious, reason = self.is_suspicious_request(log_entry)

            # Aktualizuj statystyki
            ip_stats[ip]['total_requests'] += 1
            ip_stats[ip]['last_seen'] = current_time

            if is_suspicious:
                ip_stats[ip]['suspicious_requests'] += 1
                logger.warning(
                    f"Suspicious request from {ip}: {log_entry['request']} - Pattern: {reason}")

            if log_entry['status'] >= 400:
                ip_stats[ip]['failed_requests'] += 1

            # Sprawdź limity
            if self.check_rate_limits(ip, current_time):
                self.block_ip(ip, f"Rate limit exceeded - {ip_stats[ip]}")

        # Raport statystyk
        self.generate_report(ip_stats)

    def generate_report(self, ip_stats: Dict):
        """Generuje raport bezpieczeństwa"""
        if not ip_stats:
            return

        logger.info("=== NGINX SECURITY REPORT ===")

        # Top 10 IP z największą liczbą żądań
        top_ips = sorted(
            ip_stats.items(), key=lambda x: x[1]['total_requests'], reverse=True)[:10]
        logger.info("Top 10 IPs by request count:")
        for ip, stats in top_ips:
            logger.info(
                f"  {ip}: {stats['total_requests']} total, {stats['suspicious_requests']} suspicious, {stats['failed_requests']} failed")

        # IP z podejrzanymi żądaniami
        suspicious_ips = [(ip, stats) for ip, stats in ip_stats.items(
        ) if stats['suspicious_requests'] > 0]
        if suspicious_ips:
            logger.warning("IPs with suspicious requests:")
            for ip, stats in sorted(suspicious_ips, key=lambda x: x[1]['suspicious_requests'], reverse=True):
                logger.warning(
                    f"  {ip}: {stats['suspicious_requests']} suspicious requests")

        # IP z wysokim wskaźnikiem błędów
        error_ips = [(ip, stats) for ip, stats in ip_stats.items()
                     if stats['total_requests'] > 10 and
                     (stats['failed_requests'] / stats['total_requests']) > 0.5]
        if error_ips:
            logger.warning("IPs with high error rate:")
            for ip, stats in error_ips:
                error_rate = (stats['failed_requests'] /
                              stats['total_requests']) * 100
                logger.warning(
                    f"  {ip}: {error_rate:.1f}% error rate ({stats['failed_requests']}/{stats['total_requests']})")

    def monitor_realtime(self):
        """Monitoruje logi w czasie rzeczywistym"""
        logger.info("Starting real-time nginx monitoring...")

        try:
            # Użyj tail -f do śledzenia nowych linii
            process = subprocess.Popen(['tail', '-f', self.log_file_path],
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE,
                                       universal_newlines=True)

            buffer = []
            while True:
                line = process.stdout.readline()
                if line:
                    buffer.append(line)

                    # Analizuj co 10 linii lub co 30 sekund
                    if len(buffer) >= 10:
                        self.analyze_logs(buffer)
                        buffer = []

                time.sleep(0.1)

        except KeyboardInterrupt:
            logger.info("Monitoring stopped by user")
        except Exception as e:
            logger.error(f"Error in real-time monitoring: {e}")
        finally:
            if 'process' in locals():
                process.terminate()


def main():
    """Główna funkcja"""
    import argparse

    parser = argparse.ArgumentParser(description='Nginx Security Monitor')
    parser.add_argument('--log-file', default='/var/log/nginx/access.log',
                        help='Path to nginx access log file')
    parser.add_argument('--realtime', action='store_true',
                        help='Monitor logs in real-time')
    parser.add_argument('--lines', type=int, default=1000,
                        help='Number of recent lines to analyze (default: 1000)')

    args = parser.parse_args()

    monitor = NginxSecurityMonitor(args.log_file)

    if args.realtime:
        monitor.monitor_realtime()
    else:
        # Analizuj ostatnie N linii
        try:
            with open(args.log_file, 'r') as f:
                lines = f.readlines()[-args.lines:]
                monitor.analyze_logs(lines)
        except FileNotFoundError:
            logger.error(f"Log file not found: {args.log_file}")
        except Exception as e:
            logger.error(f"Error reading log file: {e}")


if __name__ == "__main__":
    main()
