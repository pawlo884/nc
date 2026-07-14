# Wzor .env.test — skopiuj do .env.test w katalogu glownym repo (nie commituj)

DJANGO_SETTINGS_MODULE=core.settings.test
DJANGO_SECRET_KEY=zmien-na-losowy-klucz-test
DJANGO_DEBUG=0
DJANGO_ALLOWED_HOSTS=nc-test.sowa.ch,localhost,127.0.0.1
DJANGO_ENV=test

API_BASE_URL=https://nc-test.sowa.ch
MPD_API_URL=https://nc-test.sowa.ch/mpd

# PostgreSQL — OSOBNE bazy test (nigdy prod!)
# Host: IP postgresa na VPS lub nazwa serwisu w sieci Docker (np. postgres)
DEFAULT_DB_HOST=postgres
DEFAULT_DB_PORT=5432
DEFAULT_DB_NAME=test_default
DEFAULT_DB_USER=
DEFAULT_DB_PASSWORD=

MATTERHORN1_DB_HOST=postgres
MATTERHORN1_DB_PORT=5432
MATTERHORN1_DB_NAME=test_matterhorn1
MATTERHORN1_DB_USER=
MATTERHORN1_DB_PASSWORD=

MPD_DB_HOST=postgres
MPD_DB_PORT=5432
MPD_DB_NAME=test_MPD
MPD_DB_USER=
MPD_DB_PASSWORD=

WEB_AGENT_DB_HOST=postgres
WEB_AGENT_DB_PORT=5432
WEB_AGENT_DB_NAME=test_web_agent
WEB_AGENT_DB_USER=
WEB_AGENT_DB_PASSWORD=

TABU_DB_HOST=postgres
TABU_DB_PORT=5432
TABU_DB_NAME=test_tabu
TABU_DB_USER=
TABU_DB_PASSWORD=

# Redis w klastrze k3s (Service: redis)
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=zmien-haslo-test
REDIS_DB=0
CELERY_BROKER_URL=redis://:zmien-haslo-test@redis:6379/0
CELERY_RESULT_BACKEND=redis://:zmien-haslo-test@redis:6379/0

# MinIO / S3 (opcjonalnie osobny bucket test)
MINIO_ENDPOINT=
MINIO_BUCKET_NAME=
MINIO_ACCESS_KEY=
MINIO_SECRET_KEY=

FLOWER_USER=admin
FLOWER_PASSWORD=
