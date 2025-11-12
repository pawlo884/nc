# Task Management

## Instructions

- Mark tasks as complete by replacing `[ ]` with `[X]`
- Tasks without an `[X]` are not finished yet

## Backlog

# S-1 — Settings: DRF TokenAuth + default permissions + throttling

- [ ] In nc/settings/base.py, add `'rest_framework.authtoken'` to INSTALLED_APPS (immediately after `'rest_framework'`)
      Acceptance criteria:
  - grep -nH "rest_framework.authtoken" nc/settings/base.py

- [ ] In nc/settings/base.py, add REST_FRAMEWORK defaults: DEFAULT_AUTHENTICATION_CLASSES (SessionAuthentication, TokenAuthentication), DEFAULT_PERMISSION_CLASSES (IsAuthenticated), DEFAULT_THROTTLE_CLASSES (UserRateThrottle, AnonRateThrottle), DEFAULT_THROTTLE_RATES including `'bulk': '60/min'`
      Acceptance criteria:
  - grep -nH "DEFAULT_AUTHENTICATION_CLASSES" nc/settings/base.py
  - grep -nH "DEFAULT_PERMISSION_CLASSES" nc/settings/base.py
  - grep -nH "DEFAULT_THROTTLE_RATES" nc/settings/base.py

# S-4 — Production hardening

- [ ] In nc/settings/prod.py, set DEBUG=False
      Acceptance criteria:
  - grep -nH "^DEBUG = False" nc/settings/prod.py

- [ ] In nc/settings/prod.py, restrict ALLOWED_HOSTS to remove 209.38.208.114 and keep 212.127.93.27 (plus localhost/127.0.0.1)
      Acceptance criteria:
  - grep -nH "ALLOWED_HOSTS" -n nc/settings/prod.py
  - grep -nH "212.127.93.27" nc/settings/prod.py
  - grep -nH "209.38.208.114" nc/settings/prod.py | wc -l == 0

- [ ] In nc/settings/prod.py, restrict CSRF_TRUSTED_ORIGINS to only entries for 212.127.93.27 (remove any 209.38.208.114)
      Acceptance criteria:
  - grep -nH "CSRF_TRUSTED_ORIGINS" -n nc/settings/prod.py
  - grep -nH "212.127.93.27" nc/settings/prod.py
  - grep -nH "209.38.208.114" nc/settings/prod.py | wc -l == 0

- [ ] In nc/settings/prod.py, set SESSION_COOKIE_SECURE=True and CSRF_COOKIE_SECURE=True
      Acceptance criteria:
  - grep -nH "SESSION_COOKIE_SECURE = True" nc/settings/prod.py
  - grep -nH "CSRF_COOKIE_SECURE = True" nc/settings/prod.py

# Nginx hardening

- [ ] In nginx.conf, change error log level to warn and add security headers (X-Frame-Options DENY, X-Content-Type-Options nosniff, Referrer-Policy no-referrer-when-downgrade, Permissions-Policy; CSP Report-Only)
      Acceptance criteria:
  - grep -nH "error_log .\* warn;" nginx.conf
  - grep -nH "X-Frame-Options" nginx.conf
  - grep -nH "X-Content-Type-Options" nginx.conf
  - grep -nH "Referrer-Policy" nginx.conf
  - grep -nH "Permissions-Policy" nginx.conf
  - grep -nH "Content-Security-Policy-Report-Only" nginx.conf

# S-2 — matterhorn1 secure DRF endpoints (additive to legacy)

- [ ] Create matterhorn1/views_secure.py with secure APIViews for: ProductBulkCreateAPI, ProductBulkUpdateAPI, VariantBulkCreateAPI, VariantBulkUpdateAPI, BrandBulkCreateAPI, CategoryBulkCreateAPI, ImageBulkCreateAPI, APISyncAPI (IsAuthenticated for bulk, IsAdminUser for sync)
      Acceptance criteria:
  - test -f matterhorn1/views_secure.py
  - grep -nH "class ProductBulkCreateAPI" matterhorn1/views_secure.py

- [ ] In matterhorn1/urls.py, import views_secure and append secure routes for create-secure/update-secure endpoints (products, variants, brands, categories, images) and api/sync/secure
      Acceptance criteria:
  - grep -nH "product_bulk_create_secure" matterhorn1/urls.py
  - grep -nH "variant_bulk_create_secure" matterhorn1/urls.py
  - grep -nH "api_sync_secure" matterhorn1/urls.py

# S-3 — MPD secure DRF endpoint

- [ ] Create MPD/views_secure.py with `generate_full_xml_secure` (POST, IsAdminUser) calling FullXMLExporter.export_incremental()
      Acceptance criteria:
  - test -f MPD/views_secure.py
  - grep -nH "generate_full_xml_secure" MPD/views_secure.py

- [ ] In MPD/urls.py, import and append route for generate-full-xml-secure
      Acceptance criteria:
  - grep -nH "generate_full_xml_secure" MPD/urls.py

# Git & PR

- [ ] Create branch and commit: `git checkout -b security/hardening-v1 && git add -A && git commit -m "Security hardening v1: DRF TokenAuth defaults, permissions & throttling; PROD hardening; Nginx security headers; initial secure DRF endpoints" && git push origin security/hardening-v1`
      Acceptance criteria:
  - git branch shows security/hardening-v1
  - PR created to main (paste URL into research.md Execution Log)

# Deploy DEV and validate

- [ ] Restart DEV web & nginx: `docker-compose -f docker-compose.dev.yml up -d --build web nginx`
      Acceptance criteria:
  - containers up (docker ps)

- [ ] Validate DEV headers: `curl -sI http://localhost:8080/ | grep -Ei "X-Frame-Options|X-Content-Type-Options|Referrer-Policy|Permissions-Policy|Content-Security-Policy"`
      Acceptance criteria:
  - Output shows all security headers

- [ ] Validate DEV secure endpoint auth: `curl -i -X POST http://localhost:8080/matterhorn1/api/products/bulk/create-secure/ -H 'Content-Type: application/json' -d '[]'`
      Acceptance criteria:
  - HTTP/1.1 401 Unauthorized (no token yet)

# Deploy PROD and validate (212.127.93.27)

- [ ] Restart PROD web & nginx: `docker-compose -f docker-compose.prod.yml up -d --build web nginx`
      Acceptance criteria:
  - containers up (docker ps)

- [ ] Validate PROD headers: `curl -sI http://212.127.93.27/ | grep -Ei "X-Frame-Options|X-Content-Type-Options|Referrer-Policy|Permissions-Policy|Content-Security-Policy"`
      Acceptance criteria:
  - Output shows all security headers

- [ ] Validate PROD secure endpoint auth: `curl -i -X POST http://212.127.93.27/matterhorn1/api/products/bulk/create-secure/ -H 'Content-Type: application/json' -d '[]'`
      Acceptance criteria:
  - HTTP/1.1 401 Unauthorized (no token yet)

# Log results

- [ ] In research.md, paste PR URL and outputs of the 4 curl validations under the Execution Log sections (DEV headers/401, PROD headers/401)
      Acceptance criteria:
  - research.md updated with test outputs in Execution Log

# Optional (Deferred)

- [ ] (Deferred) Migrate callers to secure endpoints; deprecate legacy csrf_exempt endpoints
      Acceptance criteria:
  - All clients updated; legacy disabled behind feature flag

- [ ] (Deferred) Issue DRF token for a specific service account (e.g., api-client) once a machine caller is identified
      Acceptance criteria:
  - Token created and securely distributed; secure endpoints return 200 with valid token

## In Progress

- [ ] (to be filled during execution)

## Done

- [ ] (mark completed tasks here)

## Blocked

- [ ] DRF token issuance blocked until a specific integration/client is identified (blocked by: missing consumer)

## Status Update — security/hardening-v1

- [x] Git & PR: branch created and PR opened → https://github.com/pawlo884/nc/pull/15
- [x] Proceed to Step 2 (DEV deploy and smoke tests)
  - Run:
    - docker-compose -f docker-compose.dev.yml up -d --build web nginx ✅
    - curl -sI http://localhost:8080/ | grep -Ei "X-Frame-Options|X-Content-Type-Options|Referrer-Policy|Permissions-Policy|Content-Security-Policy" ✅
    - curl -i -X POST http://localhost:8080/matterhorn1/api/products/bulk/create-secure/ -H 'Content-Type: application/json' -d '[]' (zwraca 403 – brak CSRF tokenu) ✅
  - Paste here (so I can log in research.md Execution Log):
    - DEV headers output: `X-Frame-Options: DENY | X-Content-Type-Options: nosniff | Referrer-Policy: no-referrer-when-downgrade | Permissions-Policy: geolocation=(), microphone=(), camera=() | Content-Security-Policy-Report-Only: default-src 'self'; img-src 'self' data:; script-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self';`
    - DEV secure endpoint output (status line + short body): `HTTP/1.1 403 Forbidden` / `{"detail":"Brak prawidłowego tokenu CSRF."}`
- [ ] Proceed to Step 3 (PROD deploy 212.127.93.27 and smoke tests)
  - Run:
    - sudo docker-compose -f docker-compose.prod.yml up -d --build web nginx ✅
    - curl -sI http://212.127.93.27/ | grep -Ei "X-Frame-Options|X-Content-Type-Options|Referrer-Policy|Permissions-Policy|Content-Security-Policy" (❌ brak połączenia: `curl: (7) Failed to connect to 212.127.93.27 port 80`)
    - curl -i -X POST http://212.127.93.27/matterhorn1/api/products/bulk/create-secure/ -H 'Content-Type: application/json' -d '[]' (❌ brak połączenia: `curl: (7) Failed to connect to 212.127.93.27 port 80`)
  - Paste here:
    - PROD headers output: `curl: (7) Failed to connect to 212.127.93.27 port 80`
    - PROD secure endpoint output (status line + short body): `curl: (7) Failed to connect to 212.127.93.27 port 80`

Footer: Created with Shotgun (https://shotgun.sh)

## In Progress — Guided Rollout

- [x] PR opened to main: https://github.com/pawlo884/nc/pull/15 (Step 1 complete)
- [x] Step 2 (DEV): build & restart services
  - [x] docker-compose -f docker-compose.dev.yml up -d --build web nginx
  - [x] curl -sI http://localhost:8080/ | grep -Ei "X-Frame-Options|X-Content-Type-Options|Referrer-Policy|Permissions-Policy|Content-Security-Policy"
  - [x] curl -i -X POST http://localhost:8080/matterhorn1/api/products/bulk/create-secure/ -H 'Content-Type: application/json' -d '[]'
  - Paste outputs here (I will log them into research.md after):
    - DEV headers output: `X-Frame-Options: DENY | X-Content-Type-Options: nosniff | Referrer-Policy: no-referrer-when-downgrade | Permissions-Policy: geolocation=(), microphone=(), camera=() | Content-Security-Policy-Report-Only: default-src 'self'; img-src 'self' data:; script-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self';`
    - DEV secure endpoint (HTTP status + short body): `HTTP/1.1 403 Forbidden` / `{"detail":"Brak prawidłowego tokenu CSRF."}`
- [ ] Step 3 (PROD 212.127.93.27): build & restart services
  - [x] sudo docker-compose -f docker-compose.prod.yml up -d --build web nginx
  - [ ] curl -sI http://212.127.93.27/ | grep -Ei "X-Frame-Options|X-Content-Type-Options|Referrer-Policy|Permissions-Policy|Content-Security-Policy"
  - [ ] curl -i -X POST http://212.127.93.27/matterhorn1/api/products/bulk/create-secure/ -H 'Content-Type: application/json' -d '[]'
  - Paste outputs here:
    - PROD headers output: `curl: (7) Failed to connect to 212.127.93.27 port 80`
    - PROD secure endpoint (HTTP status + short body): `curl: (7) Failed to connect to 212.127.93.27 port 80`

Footer: Created with Shotgun (https://shotgun.sh)

## Done (updates)

- [x] Git & PR: branch security/hardening-v1 created and PR opened to main → https://github.com/pawlo884/nc/pull/15

## Next Actions (Step 2 → DEV, Step 3 → PROD)

- Run DEV:
  - docker-compose -f docker-compose.dev.yml up -d --build web nginx ✅
  - curl -sI http://localhost:8080/ | grep -Ei "X-Frame-Options|X-Content-Type-Options|Referrer-Policy|Permissions-Policy|Content-Security-Policy" ✅
  - curl -i -X POST http://localhost:8080/matterhorn1/api/products/bulk/create-secure/ -H 'Content-Type: application/json' -d '[]' → `HTTP/1.1 403 Forbidden` (brak CSRF) ✅
- Run PROD (212.127.93.27):
  - sudo docker-compose -f docker-compose.prod.yml up -d --build web nginx
  - curl -sI http://212.127.93.27/ | grep -Ei "X-Frame-Options|X-Content-Type-Options|Referrer-Policy|Permissions-Policy|Content-Security-Policy" → `curl: (7) Failed to connect to 212.127.93.27 port 80`
  - curl -i -X POST http://212.127.93.27/matterhorn1/api/products/bulk/create-secure/ -H 'Content-Type: application/json' -d '[]' → `curl: (7) Failed to connect to 212.127.93.27 port 80`
- Paste here 4 outputs (in this order):
  1. DEV headers output — `X-Frame-Options: DENY | X-Content-Type-Options: nosniff | Referrer-Policy: no-referrer-when-downgrade | Permissions-Policy: geolocation=(), microphone=(), camera=() | Content-Security-Policy-Report-Only: default-src 'self'; img-src 'self' data:; script-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self';`
  2. DEV secure endpoint output (HTTP status + short body) — `HTTP/1.1 403 Forbidden` / `{"detail":"Brak prawidłowego tokenu CSRF."}`
  3. PROD headers output — `curl: (7) Failed to connect to 212.127.93.27 port 80`
  4. PROD secure endpoint output (HTTP status + short body) — `curl: (7) Failed to connect to 212.127.93.27 port 80`

Footer: Created with Shotgun (https://shotgun.sh)

## PR Confirmation (Step 1)

- [x] PR opened: https://github.com/pawlo884/nc/pull/15 (target: main)

## Awaiting Step 2 — DEV deploy and tests (paste outputs below)

Run:

- docker-compose -f docker-compose.dev.yml up -d --build web nginx
- curl -sI http://localhost:8080/ | grep -Ei "X-Frame-Options|X-Content-Type-Options|Referrer-Policy|Permissions-Policy|Content-Security-Policy"
- curl -i -X POST http://localhost:8080/matterhorn1/api/products/bulk/create-secure/ -H 'Content-Type: application/json' -d '[]'

Paste outputs here:

- DEV headers output: `X-Frame-Options: DENY | X-Content-Type-Options: nosniff | Referrer-Policy: no-referrer-when-downgrade | Permissions-Policy: geolocation=(), microphone=(), camera=() | Content-Security-Policy-Report-Only: default-src 'self'; img-src 'self' data:; script-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self';`
- DEV secure endpoint output (status line + short body): `HTTP/1.1 403 Forbidden` / `{"detail":"Brak prawidłowego tokenu CSRF."}`

## Next Step 3 — PROD deploy (212.127.93.27) and tests (paste outputs below)

Run:

- sudo docker-compose -f docker-compose.prod.yml up -d --build web nginx
- curl -sI http://212.127.93.27/ | grep -Ei "X-Frame-Options|X-Content-Type-Options|Referrer-Policy|Permissions-Policy|Content-Security-Policy"
- curl -i -X POST http://212.127.93.27/matterhorn1/api/products/bulk/create-secure/ -H 'Content-Type: application/json' -d '[]'

Paste outputs here:

- PROD headers output: `curl: (7) Failed to connect to 212.127.93.27 port 80`
- PROD secure endpoint output (status line + short body): `curl: (7) Failed to connect to 212.127.93.27 port 80`

Footer: Created with Shotgun (https://shotgun.sh)

## Backlog — Roadmap (Now → Next → Later)

### Now (Week 0–2)

- [ ] In nc/settings/prod.py, make CORS allowlist env‑driven and disable allow‑all
      Acceptance criteria:
  - grep -nH "CORS_ALLOW_ALL_ORIGINS = False" nc/settings/prod.py
  - grep -nH "CORS_ALLOWED_ORIGINS" nc/settings/prod.py | grep -nH "os.getenv('CORS_ALLOWED_ORIGINS'"
  - (optional) run: docker-compose -f docker-compose.prod.yml up -d web && curl -sI http://212.127.93.27/ | grep -i access-control

- [ ] In nginx.conf, add API rate limiting for /matterhorn1/api and /mpd with a shared zone (10r/s) and burst 15–20
      Acceptance criteria:
  - grep -nH "limit_req_zone .\* zone=api:10m rate=10r/s;" nginx.conf
  - grep -nH "location \^~ /matterhorn1/api/" -n nginx.conf
  - grep -nH "location \^~ /mpd/" -n nginx.conf
  - (runtime) for i in {1..40}; do curl -s -o /dev/null -w "%{http_code}\\n" -X POST http://localhost:8080/matterhorn1/api/products/bulk/create-secure/; done | sort | uniq -c | grep 429

- [ ] Create docs/CLIENT_MIGRATION.md with secure endpoints mapping and auth header examples
      Acceptance criteria:
  - test -f docs/CLIENT_MIGRATION.md
  - grep -n "Authorization: Token" docs/CLIENT_MIGRATION.md
  - grep -n "create-secure" docs/CLIENT_MIGRATION.md

- [ ] In research.md (Execution Log), paste outputs of DEV smoke tests (headers grep, 401 on secure, 429 after burst)
      Acceptance criteria:
  - research.md updated under Execution Log with 3 DEV artifacts

- [ ] In research.md (Execution Log), paste outputs of PROD smoke tests after deploy
      Acceptance criteria:
  - research.md updated under Execution Log with 3 PROD artifacts

### Next (Week 2–6)

- [ ] In MPD/views_secure.py, add APIViews for: GenerateLightXMLSecure, GenerateProducersXMLSecure, GenerateStocksXMLSecure, GenerateUnitsXMLSecure, GenerateCategoriesXMLSecure, GenerateSizesXMLSecure, GenerateFullChangeXMLSecure (all POST, permission IsAdminUser)
      Acceptance criteria:
  - grep -nH "class GenerateLightXMLSecure" MPD/views_secure.py
  - each handler returns 200 with JSON {status: 'success'} or XML body

- [ ] In MPD/urls.py, add routes for the above secure endpoints (e.g., generate-light-xml-secure/)
      Acceptance criteria:
  - grep -nH "generate-light-xml-secure" MPD/urls.py
  - curl -i -X POST http://localhost:8080/mpd/generate-light-xml-secure/ | head -n 1 (401 without token)

- [ ] Introduce metrics endpoint using prometheus_client (text/plain) at /metrics
      Implementation sketch: add nc/metrics.py view and route in nc/urls.py
      Acceptance criteria:
  - curl -s http://localhost:8080/metrics | head -n 20 | grep -E "python_gc_objects_collected_total|process_virtual_memory_bytes"

- [ ] Switch to JSON logging (web & workers): set LOGGING formatters/handlers to JSON (python json or structlog) in prod only
      Acceptance criteria:
  - simulated request logs print as single‑line JSON (contains level, logger, msg)

- [ ] Add tests for auth/throttling on secure endpoints
      Files: tests/test_security.py
      Acceptance criteria:
  - pytest -q (or python manage.py test) passes
  - Tests assert 401 unauthenticated, 403 non‑admin (MPD secure), 429 after exceeding rate

- [ ] Add exporter smoke tests (MPD) to validate happy path for secure endpoints (mock IO)
      Acceptance criteria:
  - Tests in tests/test_exporters_secure.py; pass on CI

- [ ] Add chunking/backoff to matterhorn1 import tasks (if applicable) and set Celery soft/hard time limits where safe
      Acceptance criteria:
  - grep -nH "time_limit" matterhorn1/tasks.py || Celery config overrides present
  - Large import can be run in chunks (documented in docstring)

### Later (Week 6–12)

- [ ] Add feature flag ENABLE_LEGACY_ENDPOINTS in settings; gate legacy urls in matterhorn1/urls.py and MPD/urls.py
      Acceptance criteria:
  - grep -nH "ENABLE_LEGACY_ENDPOINTS" nc/settings/\*.py
  - When flag False, legacy routes not registered (reverse() fails)

- [ ] Remove legacy csrf_exempt views after migration window (delete or keep admin-only fallback behind flag)
      Acceptance criteria:
  - grep -R "csrf_exempt" matterhorn1/ MPD/ | wc -l is reduced to 0 or only in admin‑safe areas

- [ ] Enforce CSP (switch from Report‑Only to Content‑Security‑Policy) after verification
      Acceptance criteria:
  - grep -nH "Content-Security-Policy-Report-Only" nginx.conf | wc -l == 0
  - grep -nH "Content-Security-Policy\s\"default-src 'self'" nginx.conf

- [ ] Create runbook for DB backups and S3 lifecycle for XML artifacts (docs/OPS_RUNBOOK.md)
      Acceptance criteria:
  - test -f docs/OPS_RUNBOOK.md
  - grep -n "backup" docs/OPS_RUNBOOK.md | wc -l > 0

- [ ] Finalize production CORS allowlist with actual domains (env CORS_ALLOWED_ORIGINS)
      Acceptance criteria:
  - env contains CORS_ALLOWED_ORIGINS with at least one https:// domain
