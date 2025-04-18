#!/bin/bash

# Tworzenie katalogów dla Celery
mkdir -p /var/lib/celery
chmod 777 /var/lib/celery

# Uruchomienie właściwej komendy
exec "$@" 