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


# Redis/Celery Configuration
REDIS_HOST=
REDIS_PORT=
REDIS_PASSWORD=
REDIS_DB=

# Celery Configuration
CELERY_BROKER_URL=redis://:${REDIS_PASSWORD}@${REDIS_HOST}:${REDIS_PORT}/${REDIS_DB}
CELERY_RESULT_BACKEND=redis://:${REDIS_PASSWORD}@${REDIS_HOST}:${REDIS_PORT}/${REDIS_DB}