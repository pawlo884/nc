"""
Bazowa klasa dla komend synchronizacji z API Tabu.
API Tabu: X-API-KEY, https://b2b.tabu.com.pl/api/v1
"""
import json
import logging
import time
from decimal import Decimal

import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from tabu.models import ApiSyncLog

logger = logging.getLogger(__name__)


class BaseTabuAPICommand(BaseCommand):
    """
    Bazowa klasa dla komend synchronizacji z API Tabu.
    """

    help = 'Bazowa komenda synchronizacji z API Tabu'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.api_base_url = None
        self.api_key = None
        self.sync_log = None

    def add_common_arguments(self, parser):
        """Dodaj wspólne argumenty dla wszystkich komend"""
        parser.add_argument(
            '--api-url',
            type=str,
            help='URL API Tabu (domyślnie: TABU_API_BASE_URL)',
            default=None,
        )
        parser.add_argument(
            '--api-key',
            type=str,
            help='Klucz API (domyślnie: TABU_API_KEY)',
            default=None,
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            help='Rozmiar batcha (domyślnie: 50)',
            default=50,
        )
        parser.add_argument(
            '--limit',
            type=int,
            help='Limit elementów na stronę API (max 1000 dla products)',
            default=1000,
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Tryb testowy - nie zapisuje danych do bazy',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Szczegółowe logowanie',
        )

    def setup_logging(self, verbose=False):
        """Konfiguruj logowanie"""
        level = logging.DEBUG if verbose else logging.INFO
        logging.getLogger(__name__).setLevel(level)

    def get_api_credentials(self, options):
        """Pobierz dane dostępowe do API"""
        self.api_base_url = (
            options.get('api_url')
            or getattr(settings, 'TABU_API_BASE_URL', '')
            or ''
        ).strip().rstrip('/')
        self.api_key = (
            options.get('api_key') or getattr(settings, 'TABU_API_KEY', '') or ''
        )

        if not self.api_base_url:
            raise CommandError(
                'Brak URL API. Ustaw TABU_API_BASE_URL w .env lub użyj --api-url'
            )
        if not self.api_key:
            raise CommandError(
                'Brak klucza API. Ustaw TABU_API_KEY w .env lub użyj --api-key'
            )

    def create_sync_log(self, sync_type, status='running'):
        """Utwórz log synchronizacji"""
        self.sync_log = ApiSyncLog.objects.create(
            sync_type=sync_type,
            status=status,
            started_at=timezone.now(),
        )
        return self.sync_log

    def update_sync_log(self, **kwargs):
        """Aktualizuj log synchronizacji"""
        if self.sync_log:
            for key, value in kwargs.items():
                if hasattr(self.sync_log, key):
                    setattr(self.sync_log, key, value)
            self.sync_log.save(update_fields=list(kwargs.keys()))

    def complete_sync_log(self, status='completed', error_message=None):
        """Zakończ log synchronizacji"""
        if self.sync_log:
            self.sync_log.status = status
            self.sync_log.completed_at = timezone.now()
            if error_message:
                self.sync_log.error_message = error_message
            self.sync_log.save()

    def make_api_request(self, path, params=None, timeout=30):
        """Wykonaj żądanie GET do API Tabu"""
        url = f"{self.api_base_url}/{path.strip('/')}" if path else self.api_base_url
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'X-API-KEY': self.api_key,
        }

        for attempt in range(3):
            try:
                resp = requests.get(
                    url, headers=headers, params=params or {}, timeout=timeout
                )
                if resp.status_code == 429:
                    wait_seconds = 120  # Blokada 2 min przy przekroczeniu limitu
                    logger.warning(
                        f'Limit API przekroczony (429). Oczekiwanie {wait_seconds}s...'
                    )
                    time.sleep(wait_seconds)
                    continue

                resp.raise_for_status()
                return resp.json()

            except requests.exceptions.RequestException as e:
                logger.error(f'Błąd żądania API Tabu: {e}')
                if attempt == 2:
                    raise CommandError(f'Błąd połączenia z API: {e}')
                time.sleep(2)

        raise CommandError('Przekroczono liczbę prób połączenia z API')

    def fetch_product_by_id(self, api_id, timeout=30):
        """
        GET products/{id}. Zwraca dict z danymi lub None przy 404 (brak produktu).
        """
        url = f"{self.api_base_url}/products/{api_id}"
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'X-API-KEY': self.api_key,
        }
        try:
            resp = requests.get(url, headers=headers, timeout=timeout)
            if resp.status_code == 404:
                return None
            if resp.status_code == 429:
                time.sleep(120)
                return self.fetch_product_by_id(api_id, timeout)
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, dict) and 'id' in data:
                return data
            return None
        except requests.exceptions.RequestException as e:
            logger.warning(f'API Tabu products/{api_id}: {e}')
            return None

    def fetch_paginated_products(
        self, path='products', limit=100, update_from=None, update_to=None, max_products=None
    ):
        """
        Pobierz produkty z paginacją.
        API zwraca: { code, count, limit, total, page, products: [...] }
        max_products: ogranicza liczbę produktów (do testów).
        """
        all_products = []
        page = 1

        while True:
            params = {'page': page, 'limit': limit}
            if update_from:
                params['update_from'] = update_from
            if update_to:
                params['update_to'] = update_to

            data = self.make_api_request(path, params=params)
            products = data.get('products', [])

            if not products:
                break

            all_products.extend(products)
            total = data.get('total', 0)

            if max_products and len(all_products) >= max_products:
                all_products = all_products[:max_products]
                break
            if len(all_products) >= total or len(products) < limit:
                break

            page += 1
            time.sleep(1)  # ~60 req/min - poniżej limitu 100/min API Tabu

        return all_products
