# WYMAGANE w core.settings.prod (i .test) — bez tego aplikacja nie wystartuje.
# Wygeneruj osobny, losowy klucz dla KAŻDEGO środowiska (dev/test/prod), nigdy nie
# współdziel z tym w repo/kodzie: .venv/Scripts/python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
DJANGO_SECRET_KEY=zmien-na-losowy-klucz

# Bazy danych – dla lokalnego uruchomienia (manage.py na hoście) ustaw HOST=localhost, PORT=5434
# Docker override w docker-compose.dev.yml ustawia postgres-ssh-tunnel dla kontenerów
DEFAULT_DB_HOST=localhost
DEFAULT_DB_PORT=5434
DEFAULT_DB_NAME=
DEFAULT_DB_USER=
DEFAULT_DB_PASSWORD=
DJANGO_SETTINGS_MODULE=
DOCKERHUB_USERNAME=


MATTERHORN1_DB_HOST=localhost
MATTERHORN1_DB_PORT=5434
MATTERHORN1_DB_NAME=
MATTERHORN1_DB_USER=
MATTERHORN1_DB_PASSWORD=

MPD_DB_HOST=localhost
MPD_DB_PORT=5434
MPD_DB_NAME=
MPD_DB_USER=
MPD_DB_PASSWORD=

WEB_AGENT_DB_HOST=localhost
WEB_AGENT_DB_PORT=5434
WEB_AGENT_DB_NAME=
WEB_AGENT_DB_USER=
WEB_AGENT_DB_PASSWORD=

# Tabu – baza i API (szczegóły: docs/LOCAL_DEV_DATABASE.md)
TABU_DB_HOST=localhost
TABU_DB_PORT=5434
TABU_DB_NAME=zzz_tabu
TABU_DB_USER=
TABU_DB_PASSWORD=

TABU_API_BASE_URL=
TABU_API_KEY=

api_key = "" # API key pawlo884

# headersMatterhorn = {
#     "Content-Type": "application/json",
#     "Authorization": api_key}


# Flower (monitoring Celery). W blue-green domyślnie admin/flower jeśli nie ustawione.
FLOWER_USER=
FLOWER_PASSWORD=
FLOWER_UNAUTHENTICATED_API=

DO_SPACES_KEY=
DO_SPACES_SECRET=
DO_SPACES_REGION=
DO_SPACES_BUCKET=
DO_SPACES_ACCESS_KEY_ID=

# MinIO / S3 Storage
MINIO_ENDPOINT=https://minio-api.sowa.ch
MINIO_BUCKET_NAME=nc-media
MINIO_ACCESS_KEY=
MINIO_SECRET_KEY=
MINIO_REGION=us-east-1
MINIO_PUBLIC_URL=https://minio-api.sowa.ch/nc-media
MINIO_VERIFY_SSL=false
AWS_DEFAULT_ACL=
AWS_QUERYSTRING_AUTH=false


# Redis Configuration
# Redis pełni TYLKO rolę brokera Celery. Cache Django (DatabaseCache) oraz result
# backend Celery (django-celery-results) korzystają z PostgreSQL - bez dodatkowych zmiennych.
REDIS_HOST=
REDIS_PORT=
REDIS_PASSWORD=
REDIS_DB=

# Celery Configuration
# Result backend jest ustawiony na stałe na 'django-db' w core/settings - NIE ustawiaj
# CELERY_RESULT_BACKEND w env (pusta wartość jest OK).
CELERY_BROKER_URL=redis://:${REDIS_PASSWORD}@${REDIS_HOST}:${REDIS_PORT}/${REDIS_DB}
CELERY_RESULT_BACKEND=

# AI (web_agent - wzbogacanie nazwy/opisu produktu przy automatyzacji)
# USE_LANGCHAIN_AI=1 przelacza get_ai_processor() (ai_processor.py) na
# LangChainAIProcessor: OpenRouter, primary moonshotai/kimi-k2-thinking ->
# fallback openai/gpt-4o-mini przez LangChain .with_fallbacks(). Wymaga
# OPENROUTER_API_KEY (NIE OPENAI_API_KEY - inny klucz, inny provider).
# Bez USE_LANGCHAIN_AI=1 uzywany jest legacy AIProcessor (OPENAI_API_KEY
# albo HF_TOKEN - patrz ai_processor.py).
USE_LANGCHAIN_AI=
OPENROUTER_API_KEY=
OPENAI_API_KEY=
HF_TOKEN=

# LangSmith - tracing LangChain (ambient, samo ustawienie tych zmiennych
# instrumentuje kazde ChatOpenAI.invoke() bez zmian w kodzie). Klucz z
# smith.langchain.com. Dziala tylko razem z USE_LANGCHAIN_AI=1.
LANGSMITH_TRACING=
LANGSMITH_API_KEY=
LANGSMITH_PROJECT=nc