# Skrypt do uruchamiania migracji w środowisku DEVELOPMENT
# PowerShell script

Write-Host "🔄 Uruchamianie migracji dla wszystkich baz danych..." -ForegroundColor Blue

# Migracje dla bazy default (auth, admin, etc.)
Write-Host "`n📦 Migracje dla zzz_default (auth, admin, etc.)..." -ForegroundColor Yellow
python manage.py migrate --database=zzz_default --settings=core.settings.dev

# Migracje dla aplikacji admin_interface
Write-Host "`n📦 Migracje dla admin_interface..." -ForegroundColor Yellow
python manage.py migrate admin_interface --database=zzz_default --settings=core.settings.dev

# Migracje dla matterhorn1
Write-Host "`n📦 Migracje dla matterhorn1..." -ForegroundColor Yellow
python manage.py migrate matterhorn1 --database=zzz_matterhorn1 --settings=core.settings.dev

# Migracje dla MPD
Write-Host "`n📦 Migracje dla MPD..." -ForegroundColor Yellow
python manage.py migrate MPD --database=zzz_MPD --settings=core.settings.dev

# Migracje dla web_agent
Write-Host "`n📦 Migracje dla web_agent..." -ForegroundColor Yellow
python manage.py migrate web_agent --database=zzz_web_agent --settings=core.settings.dev

# Migracje dla django_celery_beat
Write-Host "`n📦 Migracje dla django_celery_beat..." -ForegroundColor Yellow
python manage.py migrate django_celery_beat --database=zzz_default --settings=core.settings.dev

# Migracje dla django_celery_results
Write-Host "`n📦 Migracje dla django_celery_results..." -ForegroundColor Yellow
python manage.py migrate django_celery_results --database=zzz_default --settings=core.settings.dev

Write-Host "`n✅ Wszystkie migracje zakończone pomyślnie!" -ForegroundColor Green
Write-Host "`nMożesz teraz uruchomić testy:" -ForegroundColor Cyan
Write-Host "  python manage.py test --settings=core.settings.dev" -ForegroundColor White

