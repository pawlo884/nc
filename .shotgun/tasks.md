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
  - grep -nH "error_log .* warn;" nginx.conf
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
- [X] Git & PR: branch created and PR opened → https://github.com/pawlo884/nc/pull/15
- [ ] Proceed to Step 2 (DEV deploy and smoke tests)
  - Run:
    - docker-compose -f docker-compose.dev.yml up -d --build web nginx
    - curl -sI http://localhost:8080/ | grep -Ei "X-Frame-Options|X-Content-Type-Options|Referrer-Policy|Permissions-Policy|Content-Security-Policy"
    - curl -i -X POST http://localhost:8080/matterhorn1/api/products/bulk/create-secure/ -H 'Content-Type: application/json' -d '[]'
  - Paste here (so I can log in research.md Execution Log):
    - DEV headers output:
    - DEV secure endpoint output (status line + short body):
- [ ] Proceed to Step 3 (PROD deploy 212.127.93.27 and smoke tests)
  - Run:
    - sudo docker-compose -f docker-compose.prod.yml up -d --build web nginx
    - curl -sI http://212.127.93.27/ | grep -Ei "X-Frame-Options|X-Content-Type-Options|Referrer-Policy|Permissions-Policy|Content-Security-Policy"
    - curl -i -X POST http://212.127.93.27/matterhorn1/api/products/bulk/create-secure/ -H 'Content-Type: application/json' -d '[]'
  - Paste here:
    - PROD headers output:
    - PROD secure endpoint output (status line + short body):

Footer: Created with Shotgun (https://shotgun.sh)

## In Progress — Guided Rollout
- [X] PR opened to main: https://github.com/pawlo884/nc/pull/15 (Step 1 complete)
- [ ] Step 2 (DEV): build & restart services
  - [ ] docker-compose -f docker-compose.dev.yml up -d --build web nginx
  - [ ] curl -sI http://localhost:8080/ | grep -Ei "X-Frame-Options|X-Content-Type-Options|Referrer-Policy|Permissions-Policy|Content-Security-Policy"
  - [ ] curl -i -X POST http://localhost:8080/matterhorn1/api/products/bulk/create-secure/ -H 'Content-Type: application/json' -d '[]'
  - Paste outputs here (I will log them into research.md after):
    - DEV headers output: …
    - DEV secure endpoint (HTTP status + short body): …
- [ ] Step 3 (PROD 212.127.93.27): build & restart services
  - [ ] sudo docker-compose -f docker-compose.prod.yml up -d --build web nginx
  - [ ] curl -sI http://212.127.93.27/ | grep -Ei "X-Frame-Options|X-Content-Type-Options|Referrer-Policy|Permissions-Policy|Content-Security-Policy"
  - [ ] curl -i -X POST http://212.127.93.27/matterhorn1/api/products/bulk/create-secure/ -H 'Content-Type: application/json' -d '[]'
  - Paste outputs here:
    - PROD headers output: …
    - PROD secure endpoint (HTTP status + short body): …

Footer: Created with Shotgun (https://shotgun.sh)

## Done (updates)
- [X] Git & PR: branch security/hardening-v1 created and PR opened to main → https://github.com/pawlo884/nc/pull/15

## Next Actions (Step 2 → DEV, Step 3 → PROD)
- Run DEV:
  - docker-compose -f docker-compose.dev.yml up -d --build web nginx
  - curl -sI http://localhost:8080/ | grep -Ei "X-Frame-Options|X-Content-Type-Options|Referrer-Policy|Permissions-Policy|Content-Security-Policy"
  - curl -i -X POST http://localhost:8080/matterhorn1/api/products/bulk/create-secure/ -H 'Content-Type: application/json' -d '[]'
- Run PROD (212.127.93.27):
  - sudo docker-compose -f docker-compose.prod.yml up -d --build web nginx
  - curl -sI http://212.127.93.27/ | grep -Ei "X-Frame-Options|X-Content-Type-Options|Referrer-Policy|Permissions-Policy|Content-Security-Policy"
  - curl -i -X POST http://212.127.93.27/matterhorn1/api/products/bulk/create-secure/ -H 'Content-Type: application/json' -d '[]'
- Paste here 4 outputs (in this order):
  1) DEV headers output
  2) DEV secure endpoint output (HTTP status + short body)
  3) PROD headers output
  4) PROD secure endpoint output (HTTP status + short body)

Footer: Created with Shotgun (https://shotgun.sh)

## PR Confirmation (Step 1)
- [X] PR opened: https://github.com/pawlo884/nc/pull/15 (target: main)

## Awaiting Step 2 — DEV deploy and tests (paste outputs below)
Run:
- docker-compose -f docker-compose.dev.yml up -d --build web nginx
- curl -sI http://localhost:8080/ | grep -Ei "X-Frame-Options|X-Content-Type-Options|Referrer-Policy|Permissions-Policy|Content-Security-Policy"
- curl -i -X POST http://localhost:8080/matterhorn1/api/products/bulk/create-secure/ -H 'Content-Type: application/json' -d '[]'

Paste outputs here:
- DEV headers output:
- DEV secure endpoint output (status line + short body):

## Next Step 3 — PROD deploy (212.127.93.27) and tests (paste outputs below)
Run:
- sudo docker-compose -f docker-compose.prod.yml up -d --build web nginx
- curl -sI http://212.127.93.27/ | grep -Ei "X-Frame-Options|X-Content-Type-Options|Referrer-Policy|Permissions-Policy|Content-Security-Policy"
- curl -i -X POST http://212.127.93.27/matterhorn1/api/products/bulk/create-secure/ -H 'Content-Type: application/json' -d '[]'

Paste outputs here:
- PROD headers output:
- PROD secure endpoint output (status line + short body):

Footer: Created with Shotgun (https://shotgun.sh)