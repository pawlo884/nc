from django.test import TestCase

# Create your tests here.
from defs_db import connect_to_postgresql
import os

# Wywołanie funkcji

os.environ["MATTERHORN_DB_NAME"] = "zzz_matterhorn"
os.environ["MATTERHORN_DB_USER"] = "doadmin"
os.environ["MATTERHORN_DB_PASSWORD"] = "AVNS_7h22feiJEsbaRFL7B3i"
os.environ["MATTERHORN_DB_HOST"] = "db-postgresql-fra1-18304-do-user-18661095-0.l.db.ondigitalocean.com"
os.environ["MATTERHORN_DB_PORT"] = "25060"

conn = connect_to_postgresql('matterhorn')


# Sprawdzenie czy połączenie działa
cur = conn.cursor()
cur.execute("SELECT version();")
print(cur.fetchone())

# Zamknięcie połączenia
cur.close()
conn.close()