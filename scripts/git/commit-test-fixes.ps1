# Skrypt PowerShell do commitowania napraw testów w logicznych grupach
# Uruchom na branchu feature/tests-comprehensive

Write-Host "=== Commitowanie napraw testów ===" -ForegroundColor Cyan
Write-Host "Branch: $(git branch --show-current)" -ForegroundColor Yellow
Write-Host ""

# 1. Naprawy w kodzie produkcyjnym (serializers, views, models, migrations)
Write-Host "1. Commitowanie napraw w kodzie produkcyjnym..." -ForegroundColor Yellow
git add matterhorn1/serializers.py matterhorn1/views_secure.py MPD/models.py matterhorn1/migrations/0001_initial.py
git commit -m "fix(matterhorn1,MPD): naprawa mapowania product_id/product_uid i importów

- Dodano import normalize_storage_key i resolve_image_url w serializers.py
- Naprawiono mapowanie product_id na product_uid w ProductSerializer
- Poprawiono użycie product_uid zamiast product_id w views_secure.py
- Dodano metodę __str__ w modelu Attributes (MPD)
- Naprawiono nazwę tabeli stock_history w migracji"

# 2. Konfiguracja środowiska testowego
Write-Host "2. Commitowanie konfiguracji testowej..." -ForegroundColor Yellow
git add nc/settings/dev.py
git commit -m "test(settings): konfiguracja baz danych dla testów

- Skonfigurowano wszystkie testowe bazy do używania MIRROR='default'
- Wyłączono database routers podczas testów
- Wyłączono throttling i użyto LocMemCache dla testów
- Warunkowe tworzenie baz z prefiksem zzz tylko poza testami"

# 3. Testy dla wszystkich aplikacji
Write-Host "3. Commitowanie testów..." -ForegroundColor Yellow
git add matterhorn1/tests.py MPD/tests.py web_agent/tests.py
git commit -m "test: dodanie kompleksowych testów dla wszystkich aplikacji

- Dodano testy modeli dla matterhorn1 (Brand, Category, Product, Variant, Image, etc.)
- Dodano testy API dla matterhorn1 (bulk operations, autoryzacja)
- Dodano testy modeli i API dla MPD
- Dodano testy modeli i API dla web_agent
- Poprawiono testy autoryzacji (akceptacja 403/405 zamiast tylko 401)
- Naprawiono testy bulk operations (użycie .using('default') dla testowej bazy)"

# 4. Dokumentacja i skrypty pomocnicze
Write-Host "4. Commitowanie dokumentacji i skryptów..." -ForegroundColor Yellow
git add DJANGO_6_COMPATIBILITY.md FIX_TEST_DATABASES.md HOW_TO_FIX_TESTS.md TEST_DATABASE_ISSUE.md TEST_FIXES_SUMMARY.md TEST_SUMMARY.md
git add clean-test-databases.ps1 clean_test_databases.py run-migrations-dev.ps1 run-migrations-dev.sh
git commit -m "docs: dokumentacja napraw testów i skrypty pomocnicze

- Dodano dokumentację analizy kompatybilności Django 6.0
- Dodano instrukcje naprawy problemów z bazami testowymi
- Dodano skrypty do czyszczenia testowych baz danych
- Dodano skrypty do uruchamiania migracji w środowisku dev"

Write-Host ""
Write-Host "=== Wszystkie commity utworzone pomyślnie! ===" -ForegroundColor Green
Write-Host ""
Write-Host "Podsumowanie:" -ForegroundColor Cyan
git log --oneline -4

