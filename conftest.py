"""
Wspólne fixture'y pytest dla całego projektu.

Migracja z `manage.py test` na pytest-django — istniejące klasy
`unittest.TestCase` / `APITestCase` działają bez zmian (pytest uruchamia je
natywnie). Nowe testy piszemy w stylu pytest z tych fixture'ów.

Tryb testów: `core.settings.dev` z `RUNNING_TESTS=True` (patrz dev.py) —
routery baz wyłączone, wszystko idzie do `default`, pozostałe aliasy to
`MIRROR: default`, `CELERY_TASK_ALWAYS_EAGER=True`, `DummyCache`.
"""
import pytest

# Bazy widoczne dla testów pytest-style (odpowiednik `databases = {...}`
# na klasach TestCase). Wszystkie i tak mirrorują `default` w trybie testów.
ALL_DATABASES = ["default", "MPD", "matterhorn1", "web_agent", "tabu", "mada"]


@pytest.fixture
def api_client():
    from rest_framework.test import APIClient
    return APIClient()


@pytest.fixture
def admin_user(db, django_user_model):
    return django_user_model.objects.create_superuser(
        username="admin_test",
        email="admin_test@example.com",
        password="pass-test-12345",
    )


@pytest.fixture
def auth_client(api_client, admin_user):
    """APIClient uwierzytelniony tokenem superusera."""
    from rest_framework.authtoken.models import Token
    token, _ = Token.objects.get_or_create(user=admin_user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return api_client


@pytest.fixture
def all_dbs(db):
    """Dla testów cross-DB (matterhorn1 <-> MPD) w stylu pytest — użyj razem z
    `@pytest.mark.django_db(databases=conftest.ALL_DATABASES)` na teście albo
    tego fixture'u, gdy potrzebny jest dostęp do wielu aliasów."""
    return ALL_DATABASES
