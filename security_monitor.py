#!/usr/bin/env python3
"""
Skrypt monitorowania bezpieczeństwa dla aplikacji NC
Sprawdza logi pod kątem podejrzanych aktywności
"""

import os
import re
import time
from datetime import datetime, timedelta
from collections import defaultdict, Counter


class SecurityMonitor:
    def __init__(self, log_dir="/app/logs"):
        self.log_dir = log_dir
        self.security_log = os.path.join(log_dir, "security.log")
        self.nginx_log = "/var/log/nginx/access.log"
        self.django_log = os.path.join(log_dir, "django.log")

    def analyze_disallowed_hosts(self, hours=24):
        """Analizuje próby ataków z nieprawidłowymi nagłówkami Host"""
        print(f"\n🔍 Analiza prób ataków DisallowedHost (ostatnie {hours}h)")
        print("=" * 60)

        if not os.path.exists(self.security_log):
            print("❌ Brak pliku security.log")
            return

        cutoff_time = datetime.now() - timedelta(hours=hours)
        suspicious_ips = defaultdict(int)
        suspicious_hosts = defaultdict(int)

        try:
            with open(self.security_log, 'r') as f:
                for line in f:
                    if 'DisallowedHost' in line:
                        # Parsuj timestamp i IP
                        timestamp_match = re.search(
                            r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
                        if timestamp_match:
                            timestamp = datetime.strptime(
                                timestamp_match.group(1), '%Y-%m-%d %H:%M:%S')
                            if timestamp >= cutoff_time:
                                # Wyciągnij IP
                                ip_match = re.search(
                                    r'(\d+\.\d+\.\d+\.\d+)', line)
                                if ip_match:
                                    ip = ip_match.group(1)
                                    suspicious_ips[ip] += 1

                                # Wyciągnij host
                                host_match = re.search(
                                    r"Invalid HTTP_HOST header: '([^']+)'", line)
                                if host_match:
                                    host = host_match.group(1)
                                    suspicious_hosts[host] += 1

            if suspicious_ips:
                print(f"🚨 Wykryto {sum(suspicious_ips.values())} prób ataków")
                print("\n📊 Top 10 podejrzanych IP:")
                for ip, count in Counter(suspicious_ips).most_common(10):
                    print(f"  {ip}: {count} prób")

                print("\n🎯 Podejrzane nagłówki Host:")
                for host, count in Counter(suspicious_hosts).most_common(10):
                    print(f"  '{host}': {count} prób")
            else:
                print("✅ Brak podejrzanych aktywności")

        except Exception as e:
            print(f"❌ Błąd podczas analizy: {e}")

    def analyze_nginx_attacks(self, hours=24):
        """Analizuje ataki wykryte przez Nginx"""
        print(f"\n🔍 Analiza ataków Nginx (ostatnie {hours}h)")
        print("=" * 60)

        if not os.path.exists(self.nginx_log):
            print("❌ Brak pliku nginx access.log")
            return

        cutoff_time = datetime.now() - timedelta(hours=hours)
        blocked_requests = defaultdict(int)
        suspicious_paths = defaultdict(int)

        try:
            with open(self.nginx_log, 'r') as f:
                for line in f:
                    # Sprawdź czy to żądanie z kodem 444 (zablokowane)
                    if ' 444 ' in line:
                        # Wyciągnij IP i ścieżkę
                        parts = line.split()
                        if len(parts) >= 7:
                            ip = parts[0]
                            path = parts[6]
                            blocked_requests[ip] += 1
                            suspicious_paths[path] += 1

            if blocked_requests:
                print(f"🚨 Zablokowano {sum(blocked_requests.values())} żądań")
                print("\n📊 Top 10 zablokowanych IP:")
                for ip, count in Counter(blocked_requests).most_common(10):
                    print(f"  {ip}: {count} zablokowanych żądań")

                print("\n🎯 Podejrzane ścieżki:")
                for path, count in Counter(suspicious_paths).most_common(10):
                    print(f"  {path}: {count} prób")
            else:
                print("✅ Brak zablokowanych żądań")

        except Exception as e:
            print(f"❌ Błąd podczas analizy: {e}")

    def check_static_files(self):
        """Sprawdza czy pliki statyczne admin_interface są dostępne"""
        print(f"\n🔍 Sprawdzanie plików statycznych admin_interface")
        print("=" * 60)

        static_dir = "/app/staticfiles"
        admin_files = [
            "admin_interface/css/themes/",
            "admin_interface/js/",
            "admin_interface/css/base.css"
        ]

        missing_files = []
        for file_path in admin_files:
            full_path = os.path.join(static_dir, file_path)
            if os.path.exists(full_path):
                print(f"✅ {file_path}")
            else:
                print(f"❌ {file_path} - BRAK")
                missing_files.append(file_path)

        if missing_files:
            print(f"\n⚠️  Brakuje {len(missing_files)} plików admin_interface")
            print("💡 Rozwiązanie: Uruchom 'python manage.py collectstatic --clear'")
        else:
            print("\n✅ Wszystkie pliki admin_interface są dostępne")

    def generate_security_report(self):
        """Generuje raport bezpieczeństwa"""
        print("\n" + "="*80)
        print("🛡️  RAPORT BEZPIECZEŃSTWA APLIKACJI NC")
        print("="*80)
        print(f"📅 Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        self.analyze_disallowed_hosts()
        self.analyze_nginx_attacks()
        self.check_static_files()

        print("\n" + "="*80)
        print("📋 REKOMENDACJE BEZPIECZEŃSTWA:")
        print("="*80)
        print("1. 🔒 Regularnie monitoruj logi bezpieczeństwa")
        print("2. 🚫 Rozważ dodanie fail2ban dla automatycznego blokowania IP")
        print("3. 🔐 Włącz HTTPS w przyszłości")
        print("4. 📊 Skonfiguruj alerty dla podejrzanych aktywności")
        print("5. 🛡️  Regularnie aktualizuj zależności")


if __name__ == "__main__":
    monitor = SecurityMonitor()
    monitor.generate_security_report()
