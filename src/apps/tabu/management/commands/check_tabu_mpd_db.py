"""
Sprawdza połączenie z bazami Tabu i MPD.
Użycie (z katalogu src):
  python manage.py check_tabu_mpd_db --settings=core.settings.dev

Dla lokalnego uruchomienia (tunel Docker na localhost:5434):
  W .env.dev ustaw: TABU_DB_HOST=localhost, MPD_DB_HOST=localhost, TABU_DB_PORT=5434, MPD_DB_PORT=5434
"""
from django.core.management.base import BaseCommand
from django.db import connections


class Command(BaseCommand):
    help = 'Sprawdza połączenie z bazami Tabu (zzz_tabu) i MPD (zzz_MPD)'

    def handle(self, *args, **options):
        dbs = [
            ('zzz_tabu', 'Tabu'),
            ('zzz_MPD', 'MPD'),
        ]

        for db_alias, label in dbs:
            if db_alias not in connections.databases:
                self.stdout.write(
                    self.style.WARNING(f'{label} ({db_alias}): Nie skonfigurowana')
                )
                continue

            cfg = connections.databases[db_alias]
            host = cfg.get('HOST', '?')
            port = cfg.get('PORT', '?')

            self.stdout.write(f'\n{label} ({db_alias}):')
            self.stdout.write(f'  Host: {host}, Port: {port}')

            try:
                conn = connections[db_alias]
                conn.ensure_connection()
                with conn.cursor() as cur:
                    cur.execute('SELECT 1')
                    cur.fetchone()
                self.stdout.write(self.style.SUCCESS(f'  ✓ Połączenie OK'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ✗ Błąd: {e}'))

        self.stdout.write('')
