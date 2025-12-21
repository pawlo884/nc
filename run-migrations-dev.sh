#!/bin/bash

################################################################################
# Skrypt do uruchamiania migracji w środowisku DEVELOPMENT
################################################################################

set -e  # Exit on error

# Kolory do outputu
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_info "🔄 Uruchamianie migracji dla wszystkich baz danych..."

# Migracje dla bazy default (auth, admin, etc.)
log_warning "📦 Migracje dla zzz_default (auth, admin, etc.)..."
python manage.py migrate --database=zzz_default --settings=nc.settings.dev

# Migracje dla aplikacji admin_interface
log_warning "📦 Migracje dla admin_interface..."
python manage.py migrate admin_interface --database=zzz_default --settings=nc.settings.dev

# Migracje dla matterhorn1
log_warning "📦 Migracje dla matterhorn1..."
python manage.py migrate matterhorn1 --database=zzz_matterhorn1 --settings=nc.settings.dev

# Migracje dla MPD
log_warning "📦 Migracje dla MPD..."
python manage.py migrate MPD --database=zzz_MPD --settings=nc.settings.dev

# Migracje dla web_agent
log_warning "📦 Migracje dla web_agent..."
python manage.py migrate web_agent --database=zzz_web_agent --settings=nc.settings.dev

# Migracje dla django_celery_beat
log_warning "📦 Migracje dla django_celery_beat..."
python manage.py migrate django_celery_beat --database=zzz_default --settings=nc.settings.dev

# Migracje dla django_celery_results
log_warning "📦 Migracje dla django_celery_results..."
python manage.py migrate django_celery_results --database=zzz_default --settings=nc.settings.dev

log_success "✅ Wszystkie migracje zakończone pomyślnie!"
echo ""
log_info "Możesz teraz uruchomić testy:"
echo "  python manage.py test --settings=nc.settings.dev"

