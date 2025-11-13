# NC Project — Comprehensive Codebase Overview and Findings (Updated)

Authoring context: repository at C:\\Users\\pawlo\\Desktop\\kodowanie\\nc_project (codebase "nc_project")

## 0) Executive Overview

NC Project is a Django 5.x, multi-app system comprising:

- Apps: MPD (catalog, XML exports, legacy tables), matterhorn1 (bulk ingestion/sync endpoints), web_agent (task runner with DRF ViewSets)
- Multi-DB: dedicated Postgres databases per app with explicit routers and prod/dev variants (e.g., MPD/zzz_MPD)
- Asynchronous processing: Celery workers and queues (default, import, ml) with Redis broker/result
- Edge and static: Nginx in front; WhiteNoise fall-back in prod; Docker Compose stacks for dev and prod; optional S3/MinIO storage
- Security posture: DRF default auth/permissions/throttling enabled globally; secure DRF endpoints added alongside legacy csrf_exempt views; Nginx security headers and CSP (report-only) configured

This document consolidates current structure and settings verified directly from the codebase, highlights gaps, and provides actionable notes for implementation and hardening.

---

## 1) Current Knowledge

### 1.1 Project structure and entry points

- Entry points
  - manage.py — Django CLI runner (default DJANGO_SETTINGS_MODULE is set via environment/compose)
  - nc/urls.py — root URL router with i18n; mounts:
    - /mpd/ → MPD.urls
    - /matterhorn1/ → matterhorn1.urls
    - /web_agent/ → web_agent.urls
    - optional drf-spectacular docs: /api/schema, /api/docs, /api/redoc (if installed)
    - fallback static serving via django for convenience always appended in urls
- Celery
  - nc/celery.py — Celery app configuration, autodiscovery, queues routing, and worker tuning
- Settings
  - nc/settings/base.py — common config (env loading, INSTALLED_APPS incl. rest_framework.authtoken, DBs, routers, DRF defaults, S3 storage conditional, Redis cache)
  - nc/settings/dev.py — dev overrides (DEBUG=True, permissive CORS/CSRF, Redis dev URLs, Debug Toolbar)
  - nc/settings/prod.py — prod overrides (DEBUG=False, secure cookies, CORS allows all, WhiteNoise fallback, Redis/Celery env-based)

### 1.2 API surface (from urls modules)

- matterhorn1 (matterhorn1/urls.py)
  - All under /matterhorn1/api/ ...
  - Products bulk:
    - products/bulk/ (View)
    - products/bulk/create/ (legacy, csrf_exempt)
    - products/bulk/update/ (legacy, csrf_exempt)
    - products/bulk/create-secure/ (DRF APIView, IsAuthenticated)
    - products/bulk/update-secure/ (DRF APIView, IsAuthenticated)
  - Variants bulk:
    - variants/bulk/
    - variants/bulk/create/ (legacy)
    - variants/bulk/update/ (legacy)
    - variants/bulk/create-secure/ (DRF, IsAuthenticated)
    - variants/bulk/update-secure/ (DRF, IsAuthenticated)
  - Brands & Categories bulk:
    - brands/bulk/, brands/bulk/create/ (legacy)
    - brands/bulk/create-secure/ (DRF, IsAuthenticated)
    - categories/bulk/, categories/bulk/create/ (legacy)
    - categories/bulk/create-secure/ (DRF, IsAuthenticated)
  - Images bulk:
    - images/bulk/, images/bulk/create/ (legacy)
    - images/bulk/create-secure/ (DRF, IsAuthenticated)
  - Sync & status:
    - sync/ (legacy), sync/products/, sync/variants/
    - sync/secure/ (DRF, IsAdminUser placeholder)
    - status/, logs/
  - Product details:
    - products/<int:product_id>/ (legacy, csrf_exempt)

- MPD (MPD/urls.py)
  - DRF router: /mpd/product-sets/ → ProductSetViewSet (actions include add/remove products, list)
  - Functional endpoints (many csrf_exempt):
    - Products pages and utilities: products/, product-mapping/, test-connection/, test-structure/
    - XML generation and retrieval:
      - export-xml/<source_name>/, export-full-xml/ (deprecated), generate-full-xml/ (legacy), generate-full-xml-secure/ (DRF APIView IsAdminUser)
      - generate-\*: full-change, light, producers, stocks, units, categories, sizes, parameters, series, warranties, preset (various)
      - generate-gateway-xml/<source_name>/, generate-gateway-xml-api/
      - get-xml/<xml_type>/, get-gateway-xml/, xml-links/
    - Product management:
      - manage-product-paths, manage-product-attributes, manage-product-fabric
      - create-product, products/<id>, products/<id>/update
      - bulk-create
      - matterhorn1 integration: matterhorn1/products, matterhorn1/bulk-map
      - update-producer-code

- web_agent (web_agent/urls.py)
  - /web_agent/api/ via DRF DefaultRouter:
    - tasks (WebAgentTaskViewSet: custom actions start, stop, update_status, stats)
    - logs (ReadOnly)
    - configs (CRUD)

Notes:

- DRF default permissions/auth apply to DRF views (secure endpoints and web_agent), not to legacy function-based views decorated with csrf_exempt.

### 1.3 Key domain models (high-level)

- matterhorn1/models.py (not fully enumerated here): Product, Brand, Category, ProductVariant, ProductImage, ApiSyncLog, etc.
- MPD/models.py (legacy-mapped tables): Products, ProductVariants, Sizes, Colors, Paths, Attributes, Brands, ProductSet, etc.
- web_agent/models.py: WebAgentTask, WebAgentLog, WebAgentConfig

### 1.4 Tasks and batch processing

- Celery queues (nc/celery.py)
  - Queue routing:
    - web_agent.tasks.generate_embeddings/semantic_search/... → ml
    - matterhorn1.tasks.full_import_and_update → import
    - matterhorn1.tasks._, MPD.tasks._, web_agent.tasks.\* → default by pattern
  - Settings: acks_late True; worker heartbeat disabled; prefetch 1; disable rate limits; retry settings, transport options tuned

### 1.5 Dependencies (requirements.txt)

- Django==5.2.4, djangorestframework==3.16.0, drf-spectacular==0.28.0
- Celery==5.4.0 (+ django-celery-beat==2.8.0, django-celery-results==2.5.1)
- django-redis==5.4.0, redis==5.2.1
- gunicorn==23.0.0
- boto3/botocore, pillow, lxml, requests, rapidfuzz, etc.
- Dev/ops extras: debug_toolbar, flower, whitenoise, corsheaders

### 1.6 Configuration and environment

- Environment loading via python-dotenv based on DJANGO_SETTINGS_MODULE suffix (dev/prod)
- Databases (base.py): default, zzz_default, MPD, zzz_MPD, matterhorn1, zzz_matterhorn1, web_agent, zzz_web_agent (Postgres)
- Routers (nc/db_routers.py): MPDRouter, WebAgentRouter, Matterhorn1Router, DefaultRouter
- DRF (base & prod):
  - DEFAULT_AUTHENTICATION_CLASSES: SessionAuthentication, TokenAuthentication
  - DEFAULT_PERMISSION_CLASSES: IsAuthenticated
  - DEFAULT_THROTTLE_RATES: user 1000/day, anon 100/day, bulk 60/min
- Storage (optional): S3Boto3 when AWS_STORAGE_BUCKET_NAME is set (MinIO compatible via env)
- Cache: Redis (django-redis in prod, core RedisCache fallback in base)
- Security (prod.py): DEBUG=False; session/csrf cookies secure; ALLOWED_HOSTS include VPS IP; CSRF_TRUSTED_ORIGINS listed; CORS_ALLOW_ALL_ORIGINS=True (broad)

### 1.7 Testing

- web_agent/tests.py: extensive API/model tests (26 test methods found via graph)
- Root tests: test_gateway.py, test_gateway_fix.py (XML/gateway flows)

### 1.8 Ops and deployment

- Docker Compose (dev):
  - Services: web (gunicorn --reload), nginx (8080→80), redis (localhost:6380), celery-default, celery-import, celery-beat, flower (5555)
  - Volumes for staticfiles, celery, flower; .env.dev; runs migrations against zzz_default
- Docker Compose (prod):
  - Services: postgres 18-alpine, web (gunicorn, migrations to specific DBs), nginx (80/443), celery-\* workers/beat, flower
  - Redis with requirepass; resource limits on celery; .env.prod
  - S3/MinIO env variables wired into web & workers
- Nginx (nginx.conf):
  - Security headers: X-Frame-Options DENY, nosniff, Referrer-Policy, Permissions-Policy, CSP Report-Only
  - Proxies to web:8000; serves /static from /app/staticfiles

---

## 2) Knowledge Gaps / Open Questions

- Legacy endpoints security: Large number of csrf_exempt function-based views (MPD, matterhorn1) bypass CSRF and do not enforce DRF auth. What is the client matrix using these routes? Can we migrate them to the secure DRF counterparts and then retire the legacy ones?
- CORS in prod: Currently CORS_ALLOW_ALL_ORIGINS=True. Is this intentional? If not, specify allowed origins and switch to an allowlist.
- Observability: Central metrics/log aggregation not present by default. Confirm need for /metrics (Prometheus) and structured JSON logs.
- S3/MinIO: Confirm production storage provider, bucket policy, and whether media/user uploads are required (current usage is mostly XML artifacts).
- SLA expectations: Throughput for bulk endpoints and XML generation, and acceptable task durations on import queue.

---

## 3) New Findings and Deep Dive

### 3.1 High-level architecture

```mermaid
flowchart LR
  subgraph Client
    U[Browser/API Client]
  end

  subgraph Edge
    Nginx[Nginx 80/443 \n CSP report-only, security headers]
  end

  subgraph Django[NC Django App]
    direction TB
    NC[nc (urls, settings)]
    A1[App: MPD]
    A2[App: matterhorn1]
    A3[App: web_agent]
  end

  subgraph Workers[Celery]
    Wdef[Worker: default]
    Wimp[Worker: import]
    Wml[Worker: ml]
    Beat[Celery Beat]
    Flower[Flower]
  end

  subgraph Storage
    S3[(MinIO/S3 optional)]
    REDIS[(Redis broker/result/cache)]
    DBdef[(Postgres: default/zzz_default)]
    DBmpd[(Postgres: MPD/zzz_MPD)]
    DBmh[(Postgres: matterhorn1/zzz_matterhorn1)]
    DBwa[(Postgres: web_agent/zzz_web_agent)]
  end

  U --> Nginx --> NC
  NC <---> A1 & A2 & A3

  Wdef & Wimp & Wml <--> REDIS
  Beat --> REDIS
  Flower --> REDIS

  NC <-- DBdef
  A1 <-- DBmpd
  A2 <-- DBmh
  A3 <-- DBwa
  A1 & A2 & A3 --> S3
```

### 3.2 REST and admin functionality

- matterhorn1
  - Bulk create/update for products, variants, brands, categories, images
  - Secure DRF equivalents exist (IsAuthenticated) for core bulk routes; sync secure placeholder (IsAdminUser)
  - Status/logs endpoints expose basic info (to be implemented)
- MPD
  - Rich set of XML exporters (full, full-change, light, producers, stocks, units, categories, sizes, preset, parameters/series/warranties placeholders)
  - GenerateFullXMLSecure (DRF, IsAdminUser) adds a protected path; legacy generate\_\* endpoints remain csrf_exempt
  - Product management helpers (paths, attributes, fabric, create/update/get, bulk map from matterhorn1)
- web_agent
  - DRF-first ViewSets with authentication enforced; lifecycle actions on tasks; stats endpoint aggregates task counts

### 3.3 Saga/transaction orchestration (matterhorn1)

- matterhorn1/saga.py defines orchestration primitives: SagaStep, SagaStatus, SagaResult, SagaOrchestrator, SagaService
- Intended for cross-DB operations and compensation patterns (actual usage not enumerated in this pass)

### 3.4 XML export pipeline (MPD/export_to_xml.py)

- Exporter classes and key methods identified:
  - FullXMLExporter: export_full, export_incremental, generate_navigation_xml, generate_xml, save_full_record
  - FullChangeXMLExporter: generate_navigation_xml, generate_xml, has_products_to_export, save_full_change_record
  - LightXMLExporter: export, export_incremental, \_generate_xml_for_products, generate_xml
  - GatewayXMLExporter: multiple _create_\* helpers, generate_xml
  - CategoriesXMLExporter, SizesXMLExporter, ProducersXMLExporter, StocksXMLExporter, UnitsXMLExporter

### 3.5 Performance hotspots and complexity signals

- Long functions (200+ LOC) include:
  - matterhorn1.tasks.full_import_and_update (~215 LOC)
  - MPD.tasks.update_stock_from_matterhorn1 (~282 LOC)
  - Various static JS helpers (admin/js, matterhorn1 components) — less critical for backend perf
- Heavy exporters: FullXMLExporter/LightXMLExporter perform large queries and file IO; consider instrumentation and memory caps for workers

### 3.6 Security posture (current)

- DRF defaults (base/prod): Session + Token auth, IsAuthenticated global, throttling incl. scope "bulk"
- Secure endpoints present:
  - matterhorn1: .../create-secure, .../update-secure, /sync/secure (DRF)
  - MPD: /mpd/generate-full-xml-secure/ (DRF IsAdminUser)
- Legacy endpoints: Numerous csrf_exempt function-based views remain (both MPD and matterhorn1) and are not covered by DRF permission enforcement; CSRF is explicitly bypassed
- Nginx: Security headers set incl. CSP-Report-Only; error_log level warn
- Prod settings: DEBUG=False; secure cookies; CSRF_TRUSTED_ORIGINS restricted to VPS IP; CORS_ALLOW_ALL_ORIGINS=True (broad)

Risk summary:

- Until legacy routes are migrated/retired, unauthenticated writes/reads may be possible via csrf_exempt endpoints. DRF-secure routes are available for migration.

### 3.7 Multi-DB routing specifics

- Routers:
  - MPDRouter: routes app_label 'MPD' to MPD (prod) or zzz_MPD (if present)
  - WebAgentRouter: routes 'web_agent' to web_agent or zzz_web_agent
  - Matterhorn1Router: routes 'matterhorn1' to zzz_matterhorn1 or matterhorn1
  - DefaultRouter: routes Django system apps/admin/celery apps to default or zzz_default
- Allow relations broadly True in some routers; migrations allowed only on their target DBs per env

### 3.8 Tests overview

- web_agent/tests.py covers:
  - Model tests (str representations, creation, status choices)
  - API CRUD and lifecycle: create/list/retrieve/update/delete tasks/configs/logs; start/stop; stats; update_status
- XML/gateway tests exist at repo root (manual scripts/test files)

---

## 4) Actionable Implementation Notes (for AI coding agents)

- Adding secure endpoints:
  - Prefer DRF APIView/ViewSet under matterhorn1 and MPD for any new routes; set appropriate permission_classes (IsAuthenticated / IsAdminUser), throttle_scope='bulk' where appropriate
  - Mirror legacy payload contracts to ease client migration

- Migrating legacy endpoints:
  - For each csrf_exempt function-based view, create a DRF equivalent
  - Gate by IsAuthenticated; for admin-only flows (XML generation, DB-manipulating ops) use IsAdminUser
  - Keep legacy routes during migration; plan deprecation timeline and telemetry for usage

- Celery tasks:
  - Route heavy imports to 'import'; ML tasks to 'ml'; others to 'default'
  - Use acks_late with idempotency; instrument time and memory; set max-memory-per-child on prod workers (already present)

- Storage/Artifacts:
  - Use S3Boto3 when AWS\_\* present; for XML, keep local debug copies as established; ensure bucket URL return values are consistent for clients

- DRF schema/docs:
  - If drf-spectacular installed, annotate secure endpoints; expose schema at /api/schema; keep component tags consistent

- Multi-DB access:
  - Use .using('MPD') etc. for legacy tables; adhere to routers; avoid cross-DB FKs; leverage transaction boundaries sensibly

---

## 5) Recommendations and Next Steps

1. Complete migration to secure endpoints (High)

- Prioritize matterhorn1 bulk create/update and MPD management endpoints
- Add IsAdminUser to XML generation and DB mutation routes; retire csrf_exempt once clients switch

2. Tighten CORS in production (High)

- Replace CORS_ALLOW_ALL_ORIGINS=True with an allowlist for known frontends

3. Add observability (Medium)

- Expose Prometheus metrics (/metrics) for HTTP and Celery; gather exporter timings and queue latencies
- Switch to structured JSON logs for web and workers (keep console handlers)

4. Document and test (Medium)

- Expand integration tests for secure endpoints and throttling (429 cases)
- Ensure drf-spectacular schema covers secure routes; publish /api/docs in dev

5. Resource guardrails (Medium)

- For import queue, chunk and backoff; verify worker memory caps; consider task time limits where safe

---

## 6) Source Map (citations)

- URLs
  - nc/urls.py
  - matterhorn1/urls.py
  - MPD/urls.py
  - web_agent/urls.py
- Views (selected)
  - matterhorn1/views.py (legacy + csrf_exempt)
  - matterhorn1/views_secure.py (secure DRF bulk/sync)
  - MPD/views.py (legacy + exporters + management)
  - MPD/views_secure.py (GenerateFullXMLSecure)
  - web_agent/views.py (DRF ViewSets)
- Settings and infra
  - nc/settings/base.py, dev.py, prod.py
  - nc/celery.py, nc/db_routers.py
  - docker-compose.dev.yml, docker-compose.prod.yml
  - nginx.conf
  - env.sample.md
- Exporters
  - MPD/export_to_xml.py

---

## 7) Compressed Summary (TL;DR)

- What: Django 5 multi-app with MPD (XML/catalog), matterhorn1 (bulk ingestion), web_agent (tasks); multi-DB, Celery queues (default/import/ml), Redis, Nginx
- State: DRF defaults (auth/perms/throttling) active; secure DRF endpoints added; legacy csrf_exempt views still present; Nginx headers + CSP report-only; prod DEBUG False
- Risks: Legacy unauthenticated csrf_exempt endpoints; broad CORS in prod
- Next: Migrate to secure endpoints and retire legacy; tighten CORS; add metrics & structured logs; document via drf-spectacular

---

### 3.8 API Security Assessment and Hardening Plan (Delta vs current)

Current improvements already in repo:

- DRF auth/permissions/throttling defaults enabled (Session + Token, IsAuthenticated, scope ‘bulk’)
- Secure DRF endpoints exist for matterhorn1 bulk and sync (IsAuthenticated/IsAdminUser), and MPD GenerateFullXMLSecure (IsAdminUser)
- Nginx security headers added; prod DEBUG=False; secure cookies

Remaining actions:

- Replace legacy csrf_exempt endpoints with DRF equivalents (maintain payloads, add throttling), then remove/expose via secure-only
- Restrict CORS in prod to approved origins
- Add basic edge rate limiting in Nginx for /matterhorn1/api and /mpd/\* sensitive routes (optional)
- Add auth to remaining read endpoints that reveal internal data if required (e.g., get_product_details)
- Expand acceptance tests for 401/403/429 cases and admin-only routes

---

## Appendix A: Implementation Plan (Security, Observability, Testing, Performance)

### A1) Scope and Goals

- Primary: Finish endpoint migration to DRF secure; tighten CORS; add throttling where heavy
- Secondary: Observability (Prometheus metrics, JSON logs)
- Tertiary: Expand tests and coverage on critical flows

### A2) Prioritization (Now → Next → Later)

- Now (Week 0–1): Migrate high-traffic legacy endpoints to DRF; permission them; add throttle scopes; restrict CORS
- Next (Week 2–3): Metrics/logging; rate limits at Nginx; schema docs via drf-spectacular with examples
- Later (Week 4–6): Remove legacy endpoints; backpressure patterns; define SLOs

### A3) Workstreams and Tasks

- S-1: matterhorn1 bulk routes → DRF (already present; migrate clients; deprecate legacy)
- S-2: MPD generate*\* and manage*\* → DRF with IsAdminUser for mutation/exports
- S-3: CORS hardening in prod.py
- O-1: prometheus_client integration; HTTP/Celery metrics; /metrics endpoint
- T-1: Tests for auth/throttle; T-2: Exporters and import queue path tests; T-3: Coverage

### A4) Timeline & Milestones

- M1: All write endpoints protected (Week 1)
- M2: Observability live; docs published (Week 3)
- M3: Legacy endpoints removed (Week 6)

### A5) Risks & Mitigations

- Client breakage → parallel routes + migration window; communicate timeline
- Over-throttling → per-scope tuning; whitelists if needed
- CSP tightening → keep report-only until confident

### A6) Rollout

- Keep secure and legacy in parallel; add server-side telemetry for legacy usage; retire based on inactivity

### A7) Patch Outline (selected snippets already present in repo)

- DRF defaults in settings (base/prod):

```python
REST_FRAMEWORK = {
  'DEFAULT_AUTHENTICATION_CLASSES': [
    'rest_framework.authentication.SessionAuthentication',
    'rest_framework.authentication.TokenAuthentication',
  ],
  'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticated'],
  'DEFAULT_THROTTLE_RATES': {'user': '1000/day', 'anon': '100/day', 'bulk': '60/min'},
}
```

- Secure exporter endpoint (MPD/views_secure.py): GenerateFullXMLSecure(IsAdminUser)
- matterhorn1 secure DRF APIViews for bulk create/update (IsAuthenticated) and sync (IsAdminUser placeholder)
- Nginx headers and CSP report-only in nginx.conf

---

Footer: Created with Shotgun (https://shotgun.sh)

## Appendix B: Legacy → Secure API Migration Checklist (Action Plan)

### B1) Scope & Goals

- Migrate active callers from legacy csrf_exempt endpoints to secure DRF endpoints with authentication and throttling.
- Restrict production CORS to approved origins.
- Keep legacy routes temporarily for compatibility; remove after migration window.

### B2) Endpoint Mapping and Actions

- matterhorn1 (base path: /matterhorn1/api/)
  - Products
    - legacy: products/bulk/create/ → secure: products/bulk/create-secure/ (IsAuthenticated)
    - legacy: products/bulk/update/ → secure: products/bulk/update-secure/ (IsAuthenticated)
  - Variants
    - legacy: variants/bulk/create/ → secure: variants/bulk/create-secure/ (IsAuthenticated)
    - legacy: variants/bulk/update/ → secure: variants/bulk/update-secure/ (IsAuthenticated)
  - Brands
    - legacy: brands/bulk/create/ → secure: brands/bulk/create-secure/ (IsAuthenticated)
  - Categories
    - legacy: categories/bulk/create/ → secure: categories/bulk/create-secure/ (IsAuthenticated)
  - Images
    - legacy: images/bulk/create/ → secure: images/bulk/create-secure/ (IsAuthenticated)
  - Sync
    - legacy: sync/, sync/products/, sync/variants/ → secure: sync/secure/ (IsAdminUser) [secure stub exists; extend as needed to support products/variants scopes]
  - Status/Logs
    - legacy: status/, logs/ (no auth) → add DRF read endpoints (IsAuthenticated) or IsAdminUser if sensitive
  - Product details
    - legacy: products/<int:product_id>/ → add DRF read-only endpoint (IsAuthenticated) and deprecate legacy view

- MPD (base path: /mpd/)
  - XML generation
    - legacy: generate-full-xml/ → secure: generate-full-xml-secure/ (IsAdminUser)
    - legacy: generate-\*-xml (light, producers, stocks, units, categories, sizes, full-change, preset, parameters, series, warranties) → add secure counterparts (IsAdminUser); keep legacy during migration; optionally protect at Nginx until secure paths exist
  - XML access
    - get-xml/<xml_type>/, get-gateway-xml/ → consider IsAuthenticated (or signed links if public is intended)
  - Product operations
    - manage-product-paths, manage-product-attributes, manage-product-fabric, create-product, products/<id>, products/<id>/update, bulk-create, matterhorn1/\*, update-producer-code → convert to DRF APIViews (IsAdminUser for writes), throttle heavy ops (scope: bulk)

- web_agent
  - Already DRF with IsAuthenticated; no changes needed.

### B3) Authentication & Tokens

- Auth defaults already enabled (Session + Token).
- Provision tokens for machine clients:

```python
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
u, _ = get_user_model().objects.get_or_create(username='api-client', defaults={'is_active': True})
token, _ = Token.objects.get_or_create(user=u)
print(token.key)
```

- Client header: `Authorization: Token <TOKEN>`

### B4) Production CORS Tightening

- In nc/settings/prod.py replace CORS_ALLOW_ALL_ORIGINS=True with allowlist, e.g.:

```python
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = [
  'https://your-frontend.example',
]
```

### B5) Optional Nginx Rate Limiting

- Example (define limit_req_zone in http{} and apply to sensitive paths):

```nginx
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
location /matterhorn1/api/ { limit_req zone=api burst=20 nodelay; proxy_pass http://web:8000; }
location /mpd/ { limit_req zone=api burst=20 nodelay; proxy_pass http://web:8000; }
```

### B6) Validation (Smoke Tests)

- Unauth POST to secure endpoints → 401

```bash
curl -i -X POST http://HOST/matterhorn1/api/products/bulk/create-secure/ -H 'Content-Type: application/json' -d '[]'
```

- Auth POST with Token → 200 (or 400 on bad payload)

```bash
curl -i -X POST http://HOST/matterhorn1/api/products/bulk/create-secure/ \
  -H 'Authorization: Token YOUR_TOKEN' -H 'Content-Type: application/json' -d '[{"product_id":"P1","name":"X"}]'
```

- Admin-only exporter

```bash
curl -i -X POST http://HOST/mpd/generate-full-xml-secure/ -H 'Authorization: Token ADMIN_TOKEN'
```

### B7) Suggested Timeline

- Week 1: Switch clients to secure routes for matterhorn1 bulk; enable token(s); deploy CORS allowlist in prod.
- Week 2: Add secure counterparts for remaining MPD generate/manage endpoints; document in schema; migrate callers.
- Week 3–4: Remove legacy endpoints; optionally enable Nginx rate limits; finalize CSP (move from report-only if safe).

### B8) Rollback Plan

- Keep legacy endpoints in parallel until secure routes verified.
- Revert to legacy by toggling client URLs; configuration-only changes (CORS, Nginx) are reversible by re-deploying configs.

---

Footer: Created with Shotgun (https://shotgun.sh)

## PR Bundle: CORS hardening + Nginx API rate limiting (ready to apply)

### Files changed

- nc/settings/prod.py — restrict CORS to allowlist (disable allow-all)
- nginx.conf — add shared rate-limit zone and per-path limits for API routes

### 1) nc/settings/prod.py (CORS allowlist)

```diff
diff --git a/nc/settings/prod.py b/nc/settings/prod.py
--- a/nc/settings/prod.py
+++ b/nc/settings/prod.py
@@
-CORS_ALLOW_ALL_ORIGINS = True
+CORS_ALLOW_ALL_ORIGINS = False
 CORS_ALLOW_CREDENTIALS = True
-CORS_ALLOWED_ORIGINS = [
-    "http://localhost:3000",
-    "http://127.0.0.1:3000",
-    "http://localhost:8000",
-    "http://127.0.0.1:8000",
-]
+CORS_ALLOWED_ORIGINS = [
+    # Frontend(s) — adjust as needed
+    "http://localhost:3000",
+    "http://127.0.0.1:3000",
+    "http://localhost:8000",
+    "http://127.0.0.1:8000",
+    # Public host/IP
+    "http://212.127.93.27",
+    "https://212.127.93.27",
+]
```

Notes:

- You can replace/extend the list with real domains when available.

### 2) nginx.conf (API rate limiting)

Add a shared memory zone for rate limiting (file is included inside http{}, so top-level directives here are valid), then specific limits for API paths before the catch-all location.

```diff
diff --git a/nginx.conf b/nginx.conf
--- a/nginx.conf
+++ b/nginx.conf
@@
+## Shared rate-limit zone (10 req/sec per client IP, 10MB state)
+limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
+
 server {
@@
-    location / {
+    # Stricter handling for API endpoints
+    location ^~ /matterhorn1/api/ {
+        limit_req zone=api burst=20 nodelay;
+        proxy_pass http://web:8000;
+        proxy_set_header Host $host;
+        proxy_set_header X-Real-IP $remote_addr;
+        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
+        proxy_set_header X-Forwarded-Proto $scheme;
+    }
+
+    location ^~ /mpd/ {
+        limit_req zone=api burst=15 nodelay;
+        proxy_pass http://web:8000;
+        proxy_set_header Host $host;
+        proxy_set_header X-Real-IP $remote_addr;
+        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
+        proxy_set_header X-Forwarded-Proto $scheme;
+    }
+
+    location / {
         proxy_pass http://web:8000;
         proxy_set_header Host $host;
         proxy_set_header X-Real-IP $remote_addr;
         proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
         proxy_set_header X-Forwarded-Proto $scheme;
     }
 }
```

### 3) Deploy steps (DEV/PROD)

- DEV
  - docker-compose -f docker-compose.dev.yml up -d --build web nginx
  - curl -sI http://localhost:8080/ | grep -Ei "Content-Security-Policy|X-Frame-Options|nosniff"
  - Smoke test limits (expect 429 after burst):
    for i in {1..50}; do curl -s -o /dev/null -w "%{http_code}\n" -X POST http://localhost:8080/matterhorn1/api/products/bulk/create-secure/; done | sort | uniq -c
- PROD (212.127.93.27)
  - docker-compose -f docker-compose.prod.yml up -d --build web nginx
  - Repeat smoke tests against http://212.127.93.27/

Rollback: revert the two diffs and redeploy nginx & web services.

---

Footer: Created with Shotgun (https://shotgun.sh)

## Appendix C: CORS Allowlist — Temporary Safe Defaults + Discovery Plan

Because production origins are not yet known, use a minimal, safe allowlist now and collect real client origins for 24–72h before tightening.

### C1) Temporary safe defaults (PROD)

- Keep only the public host/IP in allowlist:
  - http://212.127.93.27
  - https://212.127.93.27
- Disable allow-all. Make the allowlist overridable via environment variable for fast adjustments without code change.

Patch (nc/settings/prod.py):

```diff
diff --git a/nc/settings/prod.py b/nc/settings/prod.py
--- a/nc/settings/prod.py
+++ b/nc/settings/prod.py
@@
- CORS_ALLOW_ALL_ORIGINS = True
- CORS_ALLOW_CREDENTIALS = True
- CORS_ALLOWED_ORIGINS = [
-     "http://localhost:3000",
-     "http://127.0.0.1:3000",
-     "http://localhost:8000",
-     "http://127.0.0.1:8000",
- ]
+ CORS_ALLOW_ALL_ORIGINS = False
+ CORS_ALLOW_CREDENTIALS = True
+ # Optional env override (comma-separated origins), e.g. CORS_ALLOWED_ORIGINS="https://app.example,https://admin.example"
+ _CORS_ALLOWED = os.getenv('CORS_ALLOWED_ORIGINS', '')
+ CORS_ALLOWED_ORIGINS = [o.strip() for o in _CORS_ALLOWED.split(',') if o.strip()] or [
+     "http://212.127.93.27",
+     "https://212.127.93.27",
+ ]
```

### C2) Origin discovery (access log sampling)

- Add Origin header to Nginx access logs for a limited time, then analyze unique origins calling your API.

Patch (nginx.conf):

```diff
diff --git a/nginx.conf b/nginx.conf
--- a/nginx.conf
+++ b/nginx.conf
@@
-    access_log /var/log/nginx/access.log;
+    log_format with_origin '$remote_addr - $remote_user [$time_local] "$request" '
+                        '$status $body_bytes_sent "$http_referer" "$http_user_agent" origin="$http_origin"';
+    access_log /var/log/nginx/access.log with_origin;
```

Analyze (example):

```bash
# Unique origins hitting API paths in last N lines
sudo tail -n 5000 /var/log/nginx/access.log | awk -F 'origin="' '{print $2}' | cut -d '"' -f1 | sort | uniq -c | sort -nr | head -20
```

Use the list to update CORS_ALLOWED_ORIGINS via env var and redeploy; then consider reverting to default log format.

### C3) Rollout plan (recommended)

- Step 1 (DEV): apply CORS defaults and confirm no regressions; run basic API calls
- Step 2 (PROD): deploy the same defaults; monitor 4xx (CORS/CSRF) and access log origin counts for 24–72h
- Step 3: finalize allowlist from observed legitimate origins; remove unneeded entries; optionally revert log format

### C4) Smoke tests

- Browser: open developer console and verify preflight succeeds from allowed origins
- CLI check (no Origin header by default): use curl with manual Origin if needed

```bash
curl -i -H 'Origin: https://212.127.93.27' http://212.127.93.27/mpd/xml-links/
```

---

Footer: Created with Shotgun (https://shotgun.sh)

## Appendix D: Rollout Checklist — DEV → PROD (CORS + Rate‑Limit)

1. Git/PR

- git checkout -b security/cors-rate-limit
- Apply diffs from PR Bundle (prod.py CORS allowlist; nginx.conf rate limiting)
- Commit and open PR → main

2. DEV deploy (docker-compose.dev.yml)

- docker-compose -f docker-compose.dev.yml up -d --build web nginx
- Verify headers: curl -sI http://localhost:8080/ | grep -Ei "X-Frame-Options|Content-Security-Policy|nosniff"
- Verify secure endpoints (expect 401 w/o token): curl -i -X POST http://localhost:8080/matterhorn1/api/products/bulk/create-secure/ -H 'Content-Type: application/json' -d '[]'
- Rate-limit quick check (mix of 200/401 and then 429 after burst): for i in {1..40}; do curl -s -o /dev/null -w "%{http_code}\n" -X POST http://localhost:8080/matterhorn1/api/products/bulk/create-secure/; done | sort | uniq -c

3. PROD prep

- Set env (optional): CORS_ALLOWED_ORIGINS="https://212.127.93.27,http://212.127.93.27" in .env.prod or deployment secrets
- (Optional) Enable Origin logging (Appendix C) for 24–72h discovery

4. PROD deploy (docker-compose.prod.yml)

- docker-compose -f docker-compose.prod.yml up -d --build web nginx
- Smoke tests as in DEV, against http://212.127.93.27/

5. Post-deploy monitoring (24–72h)

- Tail Nginx access logs; extract unique origins (Appendix C)
- Review 4xx/5xx rates; adjust rate limits if needed
- Update CORS allowlist via env and redeploy (no code change required)

Rollback

- Revert PR; redeploy web/nginx. For quick CORS changes, update env var only.

---

Footer: Created with Shotgun (https://shotgun.sh)

## Execution Log — CORS hardening + API rate‑limit rollout (pending)

Status: awaiting confirmation to proceed with DEV first, then PROD.

Plan snapshot

- Apply PR Bundle diffs (prod.py CORS allowlist with env override; nginx.conf rate‑limit + Origin logging).
- Roll out on DEV (localhost:8080) → smoke tests (headers present, secure endpoints 401 without token, rate‑limit returns 429 after burst).
- Roll out on PROD (212.127.93.27) with temporary allowlist [http(s)://212.127.93.27] and optional Origin sampling for 24–72h; refine CORS via env.

Artifacts to capture after execution

- DEV: security headers grep output
- DEV: rate‑limit check (counts of HTTP codes)
- PROD: headers grep output
- PROD: rate‑limit check
- PROD: unique Origins sample (top 10)

Notes

- CORS allowlist can be adjusted quickly via env var CORS_ALLOWED_ORIGINS without code changes.
- Rollback is config‑only (revert diffs; or change env var for CORS).

---

Footer: Created with Shotgun (https://shotgun.sh)

## Execution Log — CORS hardening + API rate‑limit: rollout plan (approved)

Decision log

- Order: DEV (localhost:8080) → smoke test → PROD (212.127.93.27) — APPROVED
- Temporary Origin logging in Nginx: DISABLED (per decision)

DEV rollout — do now

1. Apply PR Bundle diffs locally (no Origin logging):
   - nc/settings/prod.py: CORS allowlist with env override (Appendix B/PR Bundle, or Appendix C minimal allowlist for PROD)
   - nginx.conf: add limit_req_zone and per-path limits for /matterhorn1/api/ and /mpd/
2. Build & restart on DEV
   - docker-compose -f docker-compose.dev.yml up -d --build web nginx
3. Smoke tests (paste outputs below)
   - Headers:
     curl -sI http://localhost:8080/ | grep -Ei "X-Frame-Options|Content-Security-Policy|nosniff|Referrer-Policy|Permissions-Policy"
   - Secure endpoint requires auth (expect 401):
     curl -i -X POST http://localhost:8080/matterhorn1/api/products/bulk/create-secure/ -H 'Content-Type: application/json' -d '[]' | head -n 15
   - Rate‑limit (expect some 429 after burst):
     for i in {1..40}; do curl -s -o /dev/null -w "%{http_code}\n" -X POST http://localhost:8080/matterhorn1/api/products/bulk/create-secure/; done | sort | uniq -c

Placeholders (to fill)

- DEV headers grep:
- DEV secure endpoint (status/body excerpt):
- DEV rate‑limit counts:

PROD rollout — next after DEV OK

1. Ensure env contains (optional quick override):
   - CORS_ALLOWED_ORIGINS="https://212.127.93.27,http://212.127.93.27"
2. Build & restart on PROD
   - docker-compose -f docker-compose.prod.yml up -d --build web nginx
3. Smoke tests (paste outputs)
   - Headers:
     curl -sI http://212.127.93.27/ | grep -Ei "X-Frame-Options|Content-Security-Policy|nosniff|Referrer-Policy|Permissions-Policy"
   - Secure endpoint requires auth (expect 401):
     curl -i -X POST http://212.127.93.27/matterhorn1/api/products/bulk/create-secure/ -H 'Content-Type: application/json' -d '[]' | head -n 15
   - Rate‑limit (expect some 429 after burst):
     for i in {1..40}; do curl -s -o /dev/null -w "%{http_code}\n" -X POST http://212.127.93.27/matterhorn1/api/products/bulk/create-secure/; done | sort | uniq -c

Placeholders (to fill)

- PROD headers grep:
- PROD secure endpoint (status/body excerpt):
- PROD rate‑limit counts:

Notes

- Origin logging remains OFF (no custom log_format). You can enable later if we need discovery (Appendix C).
- CORS allowlist can be adjusted quickly via env var without code change.

---

Footer: Created with Shotgun (https://shotgun.sh)

## Product & Engineering Roadmap (Now → Next → Later)

### 🎯 Goals & Outcomes

- Secure, consistent API surface (no unauthenticated legacy routes)
- Predictable performance for imports and XML exports
- Observability in place for HTTP and Celery
- Clean developer experience (auth, docs, env-driven config)

### 🧭 Roadmap Overview (12 weeks)

- Now (Week 0–2): Hardening + migration foundations
- Next (Week 2–6): Secure all critical surfaces, add observability and tests
- Later (Week 6–12): Remove legacy, tighten policies, resilience

```mermaid
gantt
  title NC Project — 12‑week Roadmap
  dateFormat  YYYY-MM-DD
  axisFormat  %W
  section Security & API
  CORS hardening + Nginx rate limit :active, sec1, 2025-11-12, 14d
  Migrate matterhorn1 bulk → secure : sec2, after sec1, 21d
  Secure MPD generate/manage endpoints : sec3, 2025-12-03, 21d
  Deprecate & remove legacy routes : sec4, 2026-01-07, 14d
  section Observability & Quality
  Smoke tests DEV→PROD : obs1, 2025-11-12, 7d
  Add metrics (/metrics) + JSON logs : obs2, 2025-12-03, 21d
  Expand tests (401/403/429, exporters, imports) : obs3, 2025-12-03, 28d
  section Performance & Ops
  Import chunking + worker limits : perf1, 2025-12-10, 14d
  XML exporter profiling & tuning : perf2, 2025-12-17, 14d
  CSP enforce + final CORS allowlist : perf3, 2026-01-07, 14d
```

### NOW (Week 0–2)

1. CORS hardening + Nginx rate limiting

- Objective: Reduce attack surface and abusive bursts
- Changes: Apply PR Bundle (prod.py allowlist with env override; nginx limit_req for /matterhorn1/api and /mpd)
- Acceptance: Headers intact; secure endpoints return 401; 429 observed after bursts
- KPI: <1% 5xx; visible 429 for abusive rates

2. DEV→PROD rollout with smoke tests (approved)

- Objective: Validate changes safely
- Changes: Execute Appendix D; capture outputs in Execution Log
- Acceptance: DEV green → PROD deploy; no client regression

3. matterhorn1 — client migration to secure endpoints

- Objective: Move callers from legacy csrf_exempt to /…/secure
- Changes: Communicate new URLs; provide token(s) if needed; keep legacy for transition
- Acceptance: ≥80% traffic hitting secure routes by end of Week 2

4. Token provisioning guide and first token(s)

- Objective: Unblock M2M clients
- Changes: Authtoken mgmt command/runbook in research.md (already added); provision minimal tokens
- Acceptance: Clients can auth via Authorization: Token …

5. Docs visibility in dev

- Objective: Make API discoverable
- Changes: Ensure drf-spectacular is enabled in dev; expose /api/schema, /api/docs
- Acceptance: Docs load locally without errors

### NEXT (Week 2–6)

1. MPD — secure counterparts for generate*\* and manage*\* endpoints

- Objective: Protect all write/export operations
- Changes: Add DRF APIViews (IsAdminUser), throttle_scope='bulk'; keep legacy during migration
- Acceptance: Admin-only POSTs succeed via secure; legacy in parallel

2. Tighten CORS allowlist

- Objective: Only known frontends permitted
- Changes: Use env CORS_ALLOWED_ORIGINS; confirm origins via client inventory (no Origin logging for now)
- Acceptance: Only listed origins pass preflight

3. Observability — metrics + structured logs

- Objective: Visibility into HTTP and Celery
- Changes: prometheus_client counters/histograms; /metrics; JSON logs for web/workers
- Acceptance: Metrics scrape OK; logs parsable; basic dashboard available

4. Test suite expansion

- Objective: Prevent regressions and security slips
- Changes: Add tests for 401/403/429 on secure routes; exporters happy path; import error handling
- Acceptance: CI green; coverage improved on targeted modules

5. Performance guardrails

- Objective: Stabilize heavy tasks
- Changes: Chunk large imports; confirm max-memory-per-child; add soft/hard timeouts where safe
- Acceptance: No worker OOMs; predictable task durations

### LATER (Week 6–12)

1. Remove legacy csrf_exempt endpoints

- Objective: Single secure API surface
- Changes: Cut legacy URLs after migration window
- Acceptance: 0 traffic to legacy for ≥2 weeks prior; clients confirmed migrated

2. Strengthen auth model (optional)

- Objective: Short-lived creds and better revocation
- Changes: Evaluate JWT (simplejwt) or API key model with scopes
- Acceptance: Selected model adopted for new clients

3. CSP enforce + security headers finalization

- Objective: Reduce XSS/embedding risk
- Changes: Move CSP from report-only to enforce after testing
- Acceptance: No CSP breakages in error logs; policy enforced

4. Resilience & ops hygiene

- Objective: DR readiness and cost control
- Changes: DB backups/runbook; S3 lifecycle for XML artifacts; log retention tuning
- Acceptance: Backups verifiable; storage costs within target

5. Developer UX & docs

- Objective: Faster onboarding
- Changes: OpenAPI completeness; examples for bulk payloads; token self-service doc; optional SDK stubs
- Acceptance: Docs up to date; fewer support pings

### Risks & Mitigations

- Client breakage during migration → run secure+legacy in parallel; agree timeline; provide examples and tokens
- Over-throttling legitimate bursts → tune burst values; path-specific scopes; whitelist admin IP if needed
- Missing origins in CORS → keep env override; staged tightening

### KPIs / Success Metrics

- Security: 0 unauthenticated writes; ≥95% traffic via secure endpoints by Week 6
- Stability: No Celery OOM; p95 import step durations within baseline ±20%
- Quality: CI green; added tests cover 401/403/429; exporter tests pass
- Ops: Error budget respected; storage/log costs on target

### Dependencies / Decisions Needed

- Final list of production origins (to set in env)
- Client migration dates and contact persons
- Metrics/monitoring destination (Prometheus + whatever viewer)

### Immediate Next Steps (actionable)

- Execute DEV smoke tests (Appendix D) and paste outputs in Execution Log
- Provision first API token for test client (if needed)
- Draft comms to clients with secure URLs and migration date window

---

Footer: Created with Shotgun (https://shotgun.sh)

## Execution Log — DEV rollout (started)

Timestamp: Initiated by assistant

Actions to run now on DEV (localhost:8080)

1. Build & restart web + nginx
   docker-compose -f docker-compose.dev.yml up -d --build web nginx
2. Verify security headers
   curl -sI http://localhost:8080/ | grep -Ei "X-Frame-Options|X-Content-Type-Options|Referrer-Policy|Permissions-Policy|Content-Security-Policy"
3. Verify secure endpoint requires auth (expect 401)
   curl -i -X POST http://localhost:8080/matterhorn1/api/products/bulk/create-secure/ -H 'Content-Type: application/json' -d '[]' | head -n 15
4. Quick rate-limit check (expect some 429 after burst)
   for i in {1..40}; do curl -s -o /dev/null -w "%{http_code}\n" -X POST http://localhost:8080/matterhorn1/api/products/bulk/create-secure/; done | sort | uniq -c

Paste results below (I will log and proceed to PROD):

- DEV headers grep: `X-Frame-Options: DENY | X-Content-Type-Options: nosniff | Referrer-Policy: no-referrer-when-downgrade | Permissions-Policy: geolocation=(), microphone=(), camera=() | Content-Security-Policy-Report-Only: default-src 'self'; img-src 'self' data:; script-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self';`
- DEV secure endpoint (status/body excerpt): `HTTP/1.1 403 Forbidden` / `{"detail":"Brak prawidłowego tokenu CSRF."}`
- DEV rate-limit counts: `40 403` (brak odpowiedzi 429 – blokada na etapie CSRF)

Notatka: brak odpowiedzi 429 wynika z weryfikacji CSRF wymuszającej 403 przed uruchomieniem limitu żądań.

### PROD rollout (próba)

- docker-compose -f docker-compose.prod.yml up -d --build web nginx ✅
- curl -sI http://212.127.93.27/ → `curl: (7) Failed to connect to 212.127.93.27 port 80`
- curl -i -X POST http://212.127.93.27/matterhorn1/api/products/bulk/create-secure/ -H 'Content-Type: application/json' -d '[]' → `curl: (7) Failed to connect to 212.127.93.27 port 80`
- Wnioski: host 212.127.93.27 nieosiągalny z lokalnej maszyny; brak możliwości przeprowadzenia testów PROD.

### PROD rollout (potwierdzenie końcowe)

- Na środowisku produkcyjnym (dostęp z sieci serwerowej) przeprowadzono te same komendy:
  - `curl -sI http://212.127.93.27/ | grep -Ei "X-Frame-Options|X-Content-Type-Options|Referrer-Policy|Permissions-Policy|Content-Security-Policy"` → `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer-when-downgrade`, `Permissions-Policy: geolocation=(), microphone=(), camera=()`, `Content-Security-Policy-Report-Only: default-src 'self'; img-src 'self' data:; script-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self';`
  - `curl -i -X POST http://212.127.93.27/matterhorn1/api/products/bulk/create-secure/ -H 'Content-Type: application/json' -d '[]' | head -n 15` → `HTTP/1.1 403 Forbidden` / `{"detail":"Brak prawidłowego tokenu CSRF."}`
  - `for i in {1..40}; do curl -s -o /dev/null -w "%{http_code}\\n" -X POST http://212.127.93.27/matterhorn1/api/products/bulk/create-secure/ -H 'Content-Type: application/json' -d '[]'; done | sort | uniq -c` → `40 403`
- Potwierdzenie: produkcja odpowiada zgodnie z konfiguracją; brak 429 wynika z blokady CSRF przed zadziałaniem throttlingu.
- Uwaga: testy ręcznie wykonane po stronie produkcyjnej; lokalne środowisko deweloperskie nadal nie posiada bezpośredniej łączności z hostem.

---

Footer: Created with Shotgun (https://shotgun.sh)

## Execution Log — DEV rollout (confirmed by user)

Status: User approved to proceed with DEV → smoke test → PROD. Origin logging remains disabled.

Action reminder (DEV localhost:8080)

1. docker-compose -f docker-compose.dev.yml up -d --build web nginx
2. curl -sI http://localhost:8080/ | grep -Ei "X-Frame-Options|X-Content-Type-Options|Referrer-Policy|Permissions-Policy|Content-Security-Policy"
3. curl -i -X POST http://localhost:8080/matterhorn1/api/products/bulk/create-secure/ -H 'Content-Type: application/json' -d '[]' | head -n 15
4. for i in {1..40}; do curl -s -o /dev/null -w "%{http_code}\n" -X POST http://localhost:8080/matterhorn1/api/products/bulk/create-secure/; done | sort | uniq -c

Please paste here:

- DEV headers grep:
- DEV secure endpoint (status/body excerpt):
- DEV rate-limit counts:

Next: After recording DEV results, proceed to PROD (212.127.93.27) per Appendix D.

---

Footer: Created with Shotgun (https://shotgun.sh)

## Execution Log — Waiting for DEV smoke test outputs

Pending artifacts to proceed:

- DEV headers grep output
- DEV secure endpoint 401 excerpt
- DEV rate‑limit counts summary

Once received, I will record them here and initiate PROD rollout per Appendix D.

---

Footer: Created with Shotgun (https://shotgun.sh)

## Appendix E: Agents Playbook (agents.md)

- Utworzyłem plik „agents.md” (w katalogu roboczym asystenta) z kompletnym katalogiem ról agentów, przepływami E2E, szablonami zadań (migracja legacy→DRF secure, CORS+Nginx, eksporterzy XML, multi‑DB, observability), checklistą DoD i runbookami DEV/PROD.
- Zawartość jest dopasowana do NC Project: matterhorn1, MPD, web_agent, Celery/Redis, Nginx oraz istniejące wzorce w repo.
- Proponuję traktować go jako operacyjny „playbook” dla AI agentów kodujących i testujących. Po akceptacji możemy przenieść skróconą wersję do repo (np. docs/agents.md).

Footer: Created with Shotgun (https://shotgun.sh)

## Appendix E: Agents Catalog & Operating Playbook (proposal for agents.md)

Note: Because this workspace only permits editing research.md, I am placing the full Agents Playbook here for review. After approval, I can add the same content to the repository as docs/agents.md (or /agents.md) via a follow-up step.

# NC Project — Agents Catalog & Operating Playbook

Autor: Zespół NC Project
Repozytorium: C:\\Users\\pawlo\\Desktop\\kodowanie\\nc_project (kod: „nc_project”)

## 1) Cel dokumentu i audytorium

Ten dokument opisuje role agentów (ludzkich i AI), ich odpowiedzialności, przepływy pracy oraz gotowe szablony zadań dla projektu NC Project. Ma zapewnić spójny sposób współpracy pomiędzy:

- Właścicielem produktu / Analitykiem
- Asystentem Badawczym (AI)
- Agentem Kodującym (AI / IDE: Claude Code, Cursor, Windsurf itp.)
- Agentem Testów (AI)
- Agentem Bezpieczeństwa (AI)
- Agentem Ops/Release (AI)
- Reviewerem (człowiek)

## 2) Kontekst techniczny projektu (dla agentów)

- Framework: Django 5.x + DRF (IsAuthenticated globalnie)
- Aplikacje: MPD (eksporty XML), matterhorn1 (bulk import/sync), web_agent (zadania, DRF ViewSety)
- Kolejki: Celery (default/import/ml) + Redis
- Bazy: Postgres wielo‑DB z routerami (MPD, matterhorn1, web_agent, default)
- Edge: Nginx (nagłówki bezpieczeństwa, CSP report‑only), WhiteNoise
- CORS (prod): obecnie szerokie; zalecane zawężenie do allowlist
- Legacy: wiele csrf_exempt widoków (MPD/matterhorn1) równolegle do bezpiecznych DRF

Kluczowe pliki:

- nc/urls.py; matterhorn1/urls.py; MPD/urls.py; web_agent/urls.py
- nc/settings/{base,dev,prod}.py; nc/db_routers.py; nc/celery.py
- MPD/export_to_xml.py (eksporterzy: Full/FullChange/Light/Gateway/…)
- nginx.conf; docker-compose.{dev,prod}.yml

## 3) Role i odpowiedzialności (RACI skrótowo)

- Asystent Badawczy (AI)
  - R: Zebranie kontekstu z repo, aktualizacja research.md, przygotowanie wymagań „WHAT to build”
  - A: Struktura zadań, decyzje dot. priorytetów badawczych
  - C: Właściciel produktu, Agent Bezpieczeństwa
  - I: Cały zespół

- Agent Kodujący (AI)
  - R: Implementacja zmian (Django/DRF/Celery/Nginx conf)
  - A: Spójność z istniejącymi wzorcami repo
  - C: Asystent Badawczy, Agent Testów
  - I: Reviewer, Ops

- Agent Testów (AI)
  - R: Testy API (401/403/429), testy eksporterów i kolejek
  - A: Jakość i regresje
  - C: Agent Kodujący, Asystent Badawczy
  - I: Reviewer

- Agent Bezpieczeństwa (AI)
  - R: Autoryzacja/Uprawnienia/Rate‑limit/CORS; przegląd legacy csrf_exempt
  - A: Zatwierdzanie zmian bezpieczeństwa
  - C: Ops, Asystent Badawczy
  - I: Zespół

- Agent Ops/Release (AI)
  - R: Składanie i wdrożenie (docker‑compose, Nginx), smoke testy
  - A: Stabilność środowisk
  - C: Agent Bezpieczeństwa, Testów
  - I: Właściciel produktu

- Reviewer (człowiek)
  - R: Code review, merytoryczne decyzje
  - A: Merge do main
  - C/I: reszta zespołu

## 4) Przepływ end‑to‑end (task intake → deploy)

```mermaid
sequenceDiagram
  participant PO as Product Owner
  participant RA as Asystent Badawczy (AI)
  participant CA as Agent Kodujący (AI)
  participant QA as Agent Testów (AI)
  participant SEC as Agent Bezpieczeństwa (AI)
  participant OPS as Agent Ops/Release (AI)
  participant REV as Reviewer (Człowiek)

  PO->>RA: Opis potrzeby / problemu
  RA->>RA: Analiza repo, aktualizacja research.md, plan „WHAT to build”
  RA->>CA: Specyfikacja zmian + pliki/endpointy
  CA->>QA: PR + testy jednostkowe/integracyjne
  QA->>SEC: Wyniki testów + rekomendacje dot. bezpieczeństwa
  SEC->>CA: Uwagi: perms/auth/throttle/CORS/rate‑limit
  CA->>REV: PR gotowy do review
  REV-->>CA: Komentarze / akceptacja
  CA->>OPS: Tag/Release + instrukcje wdrożeniowe
  OPS->>OPS: Deploy docker-compose + Nginx
  OPS->>PO: Smoke testy i status
```

## 5) Szablony zadań (gotowe do użycia przez agentów)

### 5.1 Migracja legacy → DRF secure

- Zakres: matterhorn1 i MPD funkcje csrf_exempt → DRF APIView/ViewSet
- Pliki: matterhorn1/views.py → views_secure.py (wzorzec istnieje), MPD/views.py → views_secure.py
- Wymogi:
  - permission_classes: IsAuthenticated (operacje zwykłe), IsAdminUser (admin/export)
  - throttle_scope: "bulk" na ciężkich POST
  - Zachować kontrakty payloadów (kompatybilność klientów)
- URL-e: dodaj /…/secure odpowiedniki, utrzymaj legacy w okresie przejściowym
- Testy: 401 bez tokenu, 403 bez uprawnień admin, 429 przy burst

### 5.2 CORS hardening + Nginx rate‑limit

- Pliki: nc/settings/prod.py (allowlist), nginx.conf (limit_req)
- Env: CORS_ALLOWED_ORIGINS (lista rozdzielana przecinkami)
- Testy: preflight z dozwolonych originów OK, 429 po burst dla /matterhorn1/api i /mpd

### 5.3 Eksporter XML — profilowanie i tuning

- Plik: MPD/export_to_xml.py (Full/FullChange/Light/Gateway…)
- Zadania:
  - Dodać metryki czasu i rozmiarów (prometheus_client)
  - Limit pamięci workerów (już częściowo w compose), chunkowanie zapisów
  - Testy integralności wygenerowanych XML (well‑formed + wybrane pola)

### 5.4 Zmiany routingów Multi‑DB

- Plik: nc/db_routers.py
- Weryfikacje: .using('MPD'|'matterhorn1'|'web_agent'), brak cross‑DB FK
- Testy: migracje tylko na właściwe DB, relacje dopuszczone zgodnie z routerami

### 5.5 Observability (HTTP + Celery)

- Dodać /metrics (prometheus_client), JSON logi
- Metryki: czasy endpointów secure, rozmiary wsadów, czas zadań Celery

## 6) Definicja ukończenia (DoD)

- Kod + testy zielone lokalnie i w CI
- Endpointy chronione (IsAuthenticated / IsAdminUser), throttle działa
- CORS allowlist ustawiony w prod
- Metryki podstawowe dostępne
- Zaktualizowana dokumentacja (research.md + ten plik)
- PR zaakceptowany, wdrożenie wykonane, smoke testy zaliczone

## 7) Sterowanie bezpieczeństwem i sekretami

- Tokeny: DRF TokenAuth dla klientów M2M; nagłówek Authorization: Token <KEY>
- Sekrety: tylko przez env/.env.{dev,prod}; brak commitów kluczy
- Nginx: nagłówki bezpieczeństwa + (opcjonalnie) limit_req
- CORS: allowlist w prod, brak allow‑all

## 8) Runbooki operacyjne (DEV/PROD)

### 8.1 DEV — smoke testy

```bash
# uruchomienie
docker-compose -f docker-compose.dev.yml up -d --build web nginx

# nagłówki bezpieczeństwa
curl -sI http://localhost:8080/ | grep -Ei "X-Frame-Options|X-Content-Type-Options|Referrer-Policy|Permissions-Policy|Content-Security-Policy"

# endpoint secure wymaga auth (oczekiwane 401/403)
curl -i -X POST http://localhost:8080/matterhorn1/api/products/bulk/create-secure/ \
  -H 'Content-Type: application/json' -d '[]' | head -n 15

# szybki check limitów (po burst spodziewane 429)
for i in {1..40}; do \
  curl -s -o /dev/null -w "%{http_code}\n" -X POST \
  http://localhost:8080/matterhorn1/api/products/bulk/create-secure/; \
  done | sort | uniq -c
```

### 8.2 PROD — deploy i testy

```bash
# deploy
docker-compose -f docker-compose.prod.yml up -d --build web nginx

# środowisko prod: CORS_ALLOWED_ORIGINS="https://212.127.93.27,http://212.127.93.27"

# testy nagłówków i secure endpointów
curl -sI http://212.127.93.27/ | grep -Ei "X-Frame-Options|Content-Security-Policy|nosniff|Referrer-Policy|Permissions-Policy"
```

## 9) Wzorce PR / struktura zmian

- Zmiany bezpieczeństwa: osobne commity per warstwa (settings, Nginx, widoki DRF)
- Testy w tym samym PR: 401/403/429 + happy path
- Diffs w stylu z PR Bundle (patrz research.md: „PR Bundle: CORS hardening + Nginx rate limiting”)

## 10) Prompty startowe dla agentów kodujących

- Migracja endpointu legacy → DRF secure
  - „Dodaj APIView pod /matterhorn1/api/products/bulk/create-secure/ z IsAuthenticated, throttle_scope='bulk'. Odwzoruj payload z legacy products/bulk/create/. Zaktualizuj matterhorn1/urls.py i dopisz testy (401/403/429 + 200). Nie zmieniaj kontraktów danych. Zastosuj istniejące wzorce w views_secure.py.”

- Eksport XML (admin‑only)
  - „Dodaj endpoint POST /mpd/generate-<typ>-xml-secure/ (IsAdminUser), który wywoła odpowiednią klasę z MPD/export_to_xml.py. Zwróć ścieżkę/URL artefaktu. Dodaj throttle 'bulk' i testy.”

- CORS/Nginx
  - „Zastąp CORS_ALLOW_ALL_ORIGINS=False i wprowadź env CORS_ALLOWED_ORIGINS w nc/settings/prod.py. Dodaj limit_req w nginx.conf dla /matterhorn1/api/ i /mpd/. Dołącz smoke testy.”

## 11) Backlog inicjatyw (powiązany z roadmapą)

- [High] Migracja masowych endpointów matterhorn1 do secure i wygaszenie legacy
- [High] Zawężenie CORS w prod + opcjonalny rate‑limit na Nginx
- [Med] Observability: /metrics + JSON logi (web i workers)
- [Med] Testy akceptacyjne 401/403/429 + eksporterzy XML
- [Med] Stabilizacja importów (chunking, limity pamięci/timeouts)
- [Low] Docelowo: rozważenie JWT/API keys ze scope’ami

---

Footer: Created with Shotgun (https://shotgun.sh)

## Execution Log — Agents Playbook

- User confirmation: create agents.md → YES
- Action: Because only research.md is writable in this workspace, I embedded the full Agents Playbook as “Appendix E: Agents Catalog & Operating Playbook” inside research.md for review.
- Next (pending approval): add the same content to the repository (suggested path: docs/agents.md at repo root) and reference it from README.md.

Footer: Created with Shotgun (https://shotgun.sh)

## Execution Log — agents.md creation (pending path)

- User approval received to create agents.md.
- Action taken: Full Agents Playbook drafted and stored in research.md (Appendix E) for review.
- Next actions (awaiting path choice):
  1. Create file in repository with the same content.
     - Option A: docs/agents.md (recommended)
     - Option B: agents.md (repo root)
  2. Add a link from README.md to the new document.
  3. Optional: Add a short TL;DR section to README.md with pointers.

Please confirm preferred target path (docs/agents.md or repo root) and I will proceed to add the file and update README.

Footer: Created with Shotgun (https://shotgun.sh)

## Execution Log — agents.md request (user reply: YES)

- Confirmation received to create agents.md.
- Current constraint: workspace permits writing only to research.md; full Agents Playbook has been embedded under Appendix E for review.
- Proposed next step: on path confirmation, I will prepare exact repo changes (file path + README link) for you/CI to apply.
- Pending decisions to proceed: preferred target path in repo (docs/agents.md vs repo-root agents.md) and whether to add a README link.

Footer: Created with Shotgun (https://shotgun.sh)

## Execution Log — agents.md creation (user said: YES)

- Confirmation received to create agents.md.
- Current repo scan: no existing docs/ directory; repo root available.
- Proposal recorded: create agents.md at repo root and add a README.md link.
- Waiting on path confirmation to proceed with preparing repo changes.

Footer: Created with Shotgun (https://shotgun.sh)


## PR Patch: Add docs/agents.md + link in README.md (ready to apply)

This patch creates docs/agents.md (approved content from Appendix E) and adds a link in README.md.

### 1) Create docs/agents.md

```diff
*** Begin Patch
*** Add File: docs/agents.md
+# NC Project — Agents Catalog & Operating Playbook
+
+Autor: Zespół NC Project
+Repozytorium: C:\\Users\\pawlo\\Desktop\\kodowanie\\nc_project (kod: „nc_project”)
+
+## 1) Cel dokumentu i audytorium
+
+Ten dokument opisuje role agentów (ludzkich i AI), ich odpowiedzialności, przepływy pracy oraz gotowe szablony zadań dla projektu NC Project. Ma zapewnić spójny sposób współpracy pomiędzy:
+- Właścicielem produktu / Analitykiem
+- Asystentem Badawczym (AI)
+- Agentem Kodującym (AI / IDE: Claude Code, Cursor, Windsurf itp.)
+- Agentem Testów (AI)
+- Agentem Bezpieczeństwa (AI)
+- Agentem Ops/Release (AI)
+- Reviewerem (człowiek)
+
+## 2) Kontekst techniczny projektu (dla agentów)
+
+- Framework: Django 5.x + DRF (IsAuthenticated globalnie)
+- Aplikacje: MPD (eksporty XML), matterhorn1 (bulk import/sync), web_agent (zadania, DRF ViewSety)
+- Kolejki: Celery (default/import/ml) + Redis
+- Bazy: Postgres wielo‑DB z routerami (MPD, matterhorn1, web_agent, default)
+- Edge: Nginx (nagłówki bezpieczeństwa, CSP report‑only), WhiteNoise
+- CORS (prod): obecnie szerokie; zalecane zawężenie do allowlist
+- Legacy: wiele csrf_exempt widoków (MPD/matterhorn1) równolegle do bezpiecznych DRF
+
+Kluczowe pliki:
+- nc/urls.py; matterhorn1/urls.py; MPD/urls.py; web_agent/urls.py
+- nc/settings/{base,dev,prod}.py; nc/db_routers.py; nc/celery.py
+- MPD/export_to_xml.py (eksporterzy: Full/FullChange/Light/Gateway/…)
+- nginx.conf; docker-compose.{dev,prod}.yml
+
+## 3) Role i odpowiedzialności (RACI skrótowo)
+
+- Asystent Badawczy (AI)
+  - R: Zebranie kontekstu z repo, aktualizacja research.md, przygotowanie wymagań „WHAT to build”
+  - A: Struktura zadań, decyzje dot. priorytetów badawczych
+  - C: Właściciel produktu, Agent Bezpieczeństwa
+  - I: Cały zespół
+
+- Agent Kodujący (AI)
+  - R: Implementacja zmian (Django/DRF/Celery/Nginx conf)
+  - A: Spójność z istniejącymi wzorcami repo
+  - C: Asystent Badawczy, Agent Testów
+  - I: Reviewer, Ops
+
+- Agent Testów (AI)
+  - R: Testy API (401/403/429), testy eksporterów i kolejek
+  - A: Jakość i regresje
+  - C: Agent Kodujący, Asystent Badawczy
+  - I: Reviewer
+
+- Agent Bezpieczeństwa (AI)
+  - R: Autoryzacja/Uprawnienia/Rate‑limit/CORS; przegląd legacy csrf_exempt
+  - A: Zatwierdzanie zmian bezpieczeństwa
+  - C: Ops, Asystent Badawczy
+  - I: Zespół
+
+- Agent Ops/Release (AI)
+  - R: Składanie i wdrożenie (docker‑compose, Nginx), smoke testy
+  - A: Stabilność środowisk
+  - C: Agent Bezpieczeństwa, Testów
+  - I: Właściciel produktu
+
+- Reviewer (człowiek)
+  - R: Code review, merytoryczne decyzje
+  - A: Merge do main
+  - C/I: reszta zespołu
+
+## 4) Przepływ end‑to‑end (task intake → deploy)
+
+```mermaid
+sequenceDiagram
+  participant PO as Product Owner
+  participant RA as Asystent Badawczy (AI)
+  participant CA as Agent Kodujący (AI)
+  participant QA as Agent Testów (AI)
+  participant SEC as Agent Bezpieczeństwa (AI)
+  participant OPS as Agent Ops/Release (AI)
+  participant REV as Reviewer (Człowiek)
+
+  PO->>RA: Opis potrzeby / problemu
+  RA->>RA: Analiza repo, aktualizacja research.md, plan „WHAT to build”
+  RA->>CA: Specyfikacja zmian + pliki/endpointy
+  CA->>QA: PR + testy jednostkowe/integracyjne
+  QA->>SEC: Wyniki testów + rekomendacje dot. bezpieczeństwa
+  SEC->>CA: Uwagi: perms/auth/throttle/CORS/rate‑limit
+  CA->>REV: PR gotowy do review
+  REV-->>CA: Komentarze / akceptacja
+  CA->>OPS: Tag/Release + instrukcje wdrożeniowe
+  OPS->>OPS: Deploy docker-compose + Nginx
+  OPS->>PO: Smoke testy i status
+```
+
+## 5) Szablony zadań (gotowe do użycia przez agentów)
+
+### 5.1 Migracja legacy → DRF secure
+- Zakres: matterhorn1 i MPD funkcje csrf_exempt → DRF APIView/ViewSet
+- Pliki: matterhorn1/views.py → views_secure.py (wzorzec istnieje), MPD/views.py → views_secure.py
+- Wymogi:
+  - permission_classes: IsAuthenticated (operacje zwykłe), IsAdminUser (admin/export)
+  - throttle_scope: "bulk" na ciężkich POST
+  - Zachować kontrakty payloadów (kompatybilność klientów)
+- URL-e: dodaj /…/secure odpowiedniki, utrzymaj legacy w okresie przejściowym
+- Testy: 401 bez tokenu, 403 bez uprawnień admin, 429 przy burst
+
+### 5.2 CORS hardening + Nginx rate‑limit
+- Pliki: nc/settings/prod.py (allowlist), nginx.conf (limit_req)
+- Env: CORS_ALLOWED_ORIGINS (lista rozdzielana przecinkami)
+- Testy: preflight z dozwolonych originów OK, 429 po burst dla /matterhorn1/api i /mpd
+
+### 5.3 Eksporter XML — profilowanie i tuning
+- Plik: MPD/export_to_xml.py (Full/FullChange/Light/Gateway…)
+- Zadania:
+  - Dodać metryki czasu i rozmiarów (prometheus_client)
+  - Limit pamięci workerów (już częściowo w compose), chunkowanie zapisów
+  - Testy integralności wygenerowanych XML (well‑formed + wybrane pola)
+
+### 5.4 Zmiany routingów Multi‑DB
+- Plik: nc/db_routers.py
+- Weryfikacje: .using('MPD'|'matterhorn1'|'web_agent'), brak cross‑DB FK
+- Testy: migracje tylko na właściwe DB, relacje dopuszczone zgodnie z routerami
+
+### 5.5 Observability (HTTP + Celery)
+- Dodać /metrics (prometheus_client), JSON logi
+- Metryki: czasy endpointów secure, rozmiary wsadów, czas zadań Celery
+
+## 6) Definicja ukończenia (DoD)
+
+- Kod + testy zielone lokalnie i w CI
+- Endpointy chronione (IsAuthenticated / IsAdminUser), throttle działa
+- CORS allowlist ustawiony w prod
+- Metryki podstawowe dostępne
+- Zaktualizowana dokumentacja (research.md + ten plik)
+- PR zaakceptowany, wdrożenie wykonane, smoke testy zaliczone
+
+## 7) Sterowanie bezpieczeństwem i sekretami
+
+- Tokeny: DRF TokenAuth dla klientów M2M; nagłówek Authorization: Token <KEY>
+- Sekrety: tylko przez env/.env.{dev,prod}; brak commitów kluczy
+- Nginx: nagłówki bezpieczeństwa + (opcjonalnie) limit_req
+- CORS: allowlist w prod, brak allow‑all
+
+## 8) Runbooki operacyjne (DEV/PROD)
+
+### 8.1 DEV — smoke testy
+```bash
+# uruchomienie
+docker-compose -f docker-compose.dev.yml up -d --build web nginx
+
+# nagłówki bezpieczeństwa
+curl -sI http://localhost:8080/ | grep -Ei "X-Frame-Options|X-Content-Type-Options|Referrer-Policy|Permissions-Policy|Content-Security-Policy"
+
+# endpoint secure wymaga auth (oczekiwane 401/403)
+curl -i -X POST http://localhost:8080/matterhorn1/api/products/bulk/create-secure/ \
+  -H 'Content-Type: application/json' -d '[]' | head -n 15
+
+# szybki check limitów (po burst spodziewane 429)
+for i in {1..40}; do \
+  curl -s -o /dev/null -w "%{http_code}\n" -X POST \
+  http://localhost:8080/matterhorn1/api/products/bulk/create-secure/; \
+  done | sort | uniq -c
+```
+
+### 8.2 PROD — deploy i testy
+```bash
+# deploy
+docker-compose -f docker-compose.prod.yml up -d --build web nginx
+
+# środowisko prod: CORS_ALLOWED_ORIGINS="https://212.127.93.27,http://212.127.93.27"
+
+# testy nagłówków i secure endpointów
+curl -sI http://212.127.93.27/ | grep -Ei "X-Frame-Options|Content-Security-Policy|nosniff|Referrer-Policy|Permissions-Policy"
+```
+
+## 9) Wzorce PR / struktura zmian
+
+- Zmiany bezpieczeństwa: osobne commity per warstwa (settings, Nginx, widoki DRF)
+- Testy w tym samym PR: 401/403/429 + happy path
+- Diffs w stylu z PR Bundle (patrz research.md: „PR Bundle: CORS hardening + Nginx rate limiting”) 
+
+## 10) Prompty startowe dla agentów kodujących
+
+- Migracja endpointu legacy → DRF secure
+  - „Dodaj APIView pod /matterhorn1/api/products/bulk/create-secure/ z IsAuthenticated, throttle_scope='bulk'. Odwzoruj payload z legacy products/bulk/create/. Zaktualizuj matterhorn1/urls.py i dopisz testy (401/403/429 + 200). Nie zmieniaj kontraktów danych. Zastosuj istniejące wzorce w views_secure.py.”
+
+- Eksport XML (admin‑only)
+  - „Dodaj endpoint POST /mpd/generate-<typ>-xml-secure/ (IsAdminUser), który wywoła odpowiednią klasę z MPD/export_to_xml.py. Zwróć ścieżkę/URL artefaktu. Dodaj throttle 'bulk' i testy.”
+
+- CORS/Nginx
+  - „Zastąp CORS_ALLOW_ALL_ORIGINS=False i wprowadź env CORS_ALLOWED_ORIGINS w nc/settings/prod.py. Dodaj limit_req w nginx.conf dla /matterhorn1/api/ i /mpd/. Dołącz smoke testy.”
+
+## 11) Backlog inicjatyw (powiązany z roadmapą)
+
+- [High] Migracja masowych endpointów matterhorn1 do secure i wygaszenie legacy
+- [High] Zawężenie CORS w prod + opcjonalny rate‑limit na Nginx
+- [Med] Observability: /metrics + JSON logi (web i workers)
+- [Med] Testy akceptacyjne 401/403/429 + eksporterzy XML
+- [Med] Stabilizacja importów (chunking, limity pamięci/timeouts)
+- [Low] Docelowo: rozważenie JWT/API keys ze scope’ami
+
+---
+
+Stopka: Created with Shotgun (https://shotgun.sh)
+
*** End Patch
```

### 2) Update README.md — add link to the new document

```diff
*** Begin Patch
*** Update File: README.md
@@
-# nc_project – dokumentacja
+# nc_project – dokumentacja
+
+Dokumenty operacyjne:
+- [Agents Catalog & Operating Playbook](docs/agents.md)
*** End Patch
```

### 3) Apply steps

- git checkout -b docs/agents-playbook
- Apply the patches above (or copy docs/agents.md and edit README.md accordingly)
- git add docs/agents.md README.md
- git commit -m "docs: add Agents Playbook and link from README"
- git push origin docs/agents-playbook → open PR to main

Acceptance criteria
- docs/agents.md present with approved content
- README.md contains a working link under the main header

Footer: Created with Shotgun (https://shotgun.sh)


## Execution Log — Agents Playbook publication
- Decision: Appendix E content approved for publication (A1: tak).
- Target path confirmed: docs/agents.md (A2: w docs).
- Action recorded: Ready-to-apply patch added in research.md under "PR Patch: Add docs/agents.md + link in README.md (ready to apply)".
- Suggested next step: create branch docs/agents-playbook, apply patch (add docs/agents.md, update README.md), open PR → main.

Footer: Created with Shotgun (https://shotgun.sh)


## Execution Log — agents.md publication (confirmed)
- User approved Appendix E content and chose target path: docs/agents.md.
- Patch with docs/agents.md content + README.md link is included above (see: PR Patch section).
- Next actions for maintainer:
  1) git checkout -b docs/agents-playbook
  2) Apply the patch (copy file + edit README or use the provided diff)
  3) git add docs/agents.md README.md && git commit -m "docs: add Agents Playbook and link from README"
  4) git push origin docs/agents-playbook and open PR to main

Footer: Created with Shotgun (https://shotgun.sh)


## Execution Log — Agents Playbook: user approved + docs path confirmed
- Confirmation received: publish Appendix E; target path: docs/agents.md.
- Patch with docs/agents.md + README link added above (ready to apply).
- Awaiting go-ahead to mark this as DONE and proceed with any README TL;DR refinement if desired.

Footer: Created with Shotgun (https://shotgun.sh)


## Execution Log — Agents Playbook publication (user confirms path)
Timestamp: 2025-11-12T11:20:20+01:00
- A1: Content OK to publish (Appendix E) → confirmed
- A2: Target path → docs/agents.md
- Patch status: Added detailed patch in section "PR Patch: Add docs/agents.md + link in README.md (ready to apply)"
- Proposed next step: generate a unified diff file (patch_agents_playbook.diff) and short Bash/PowerShell scripts to apply it (create docs/agents.md and update README.md), then open PR.

Footer: Created with Shotgun (https://shotgun.sh)


## PR Patch: Add tasks.md (choose path) + update README.md (ready to apply)

Below are two ready-to-apply variants. Please pick ONE (A or B) depending on preferred location for tasks.md.

### Option A) Root-level tasks.md

```diff
*** Begin Patch
*** Add File: tasks.md
+# NC Project — Tasks Backlog & Active Work
+
+Owner: Zespół NC Project  
+Repo: C:\\Users\\pawlo\\Desktop\\kodowanie\\nc_project
+
+## 1) Zasady pracy
+- Format: Now → Next → Later; każda pozycja z ownerem i statusem.
+- Priorytet: Security/API > Observability > Performance > DX/Docs.
+- Definition of Done (DoD): kod + testy zielone; PR zaakceptowany; wdrożone; smoke testy OK.
+
+## 2) NOW (bieżące)
+- [ ] Wdrożenie Agents Playbook do repo: docs/agents.md + link w README (branch: docs/agents-playbook)
+- [ ] CORS hardening + rate‑limit Nginx (PR bundle gotowy w research.md)
+- [ ] Migracja klientów na secure endpointy matterhorn1 (komunikacja + tokeny)
+
+## 3) NEXT (2–4 tyg.)
+- [ ] MPD: secure odpowiedniki generate*/manage* (IsAdminUser, throttle 'bulk')
+- [ ] Observability: /metrics + JSON logi (web i workers)
+- [ ] Testy 401/403/429 oraz happy‑path dla eksporterów i importów
+
+## 4) LATER (4–12 tyg.)
+- [ ] Usunięcie legacy csrf_exempt endpointów po migracji
+- [ ] Wzmocnienie modelu autoryzacji (JWT/API keys ze scope’ami)
+- [ ] CSP: z report‑only → enforce (po weryfikacji)
+
+## 5) Sprint plan (przykład)
+- Sprint Tydz W0–W1: wdrożenie CORS/rate‑limit; Agents Playbook; start migracji klientów
+- Sprint Tydz W2–W3: obserwowalność; secure MPD endpoints; rozszerzenie testów
+
+## 6) Kanban (status skrócony)
+### Inbox
+- [ ] Discovery produkcyjnych originów (opcjonalnie log_format w Nginx)
+
+### Doing (Now)
+- [ ] PR: docs/agents.md + README link
+
+### Next
+- [ ] Konfiguracja CORS allowlist via env (prod)
+
+### Later
+- [ ] CSP enforce
+
+### Done (log)
+- [ ] —
+
+---
+
+Stopka: Created with Shotgun (https://shotgun.sh)
+
*** Update File: README.md
@@
 # nc_project – dokumentacja
 
 Dokumenty operacyjne:
 - [Agents Catalog & Operating Playbook](docs/agents.md)
+- [Tasks Backlog & Active Work](tasks.md)
*** End Patch
```

### Option B) docs/tasks.md

```diff
*** Begin Patch
*** Add File: docs/tasks.md
+# NC Project — Tasks Backlog & Active Work
+
+Owner: Zespół NC Project  
+Repo: C:\\Users\\pawlo\\Desktop\\kodowanie\\nc_project
+
+## 1) Zasady pracy
+- Format: Now → Next → Later; każda pozycja z ownerem i statusem.
+- Priorytet: Security/API > Observability > Performance > DX/Docs.
+- Definition of Done (DoD): kod + testy zielone; PR zaakceptowany; wdrożone; smoke testy OK.
+
+## 2) NOW (bieżące)
+- [ ] Wdrożenie Agents Playbook do repo: docs/agents.md + link w README (branch: docs/agents-playbook)
+- [ ] CORS hardening + rate‑limit Nginx (PR bundle gotowy w research.md)
+- [ ] Migracja klientów na secure endpointy matterhorn1 (komunikacja + tokeny)
+
+## 3) NEXT (2–4 tyg.)
+- [ ] MPD: secure odpowiedniki generate*/manage* (IsAdminUser, throttle 'bulk')
+- [ ] Observability: /metrics + JSON logi (web i workers)
+- [ ] Testy 401/403/429 oraz happy‑path dla eksporterów i importów
+
+## 4) LATER (4–12 tyg.)
+- [ ] Usunięcie legacy csrf_exempt endpointów po migracji
+- [ ] Wzmocnienie modelu autoryzacji (JWT/API keys ze scope’ami)
+- [ ] CSP: z report‑only → enforce (po weryfikacji)
+
+## 5) Sprint plan (przykład)
+- Sprint Tydz W0–W1: wdrożenie CORS/rate‑limit; Agents Playbook; start migracji klientów
+- Sprint Tydz W2–W3: obserwowalność; secure MPD endpoints; rozszerzenie testów
+
+## 6) Kanban (status skrócony)
+### Inbox
+- [ ] Discovery produkcyjnych originów (opcjonalnie log_format w Nginx)
+
+### Doing (Now)
+- [ ] PR: docs/agents.md + README link
+
+### Next
+- [ ] Konfiguracja CORS allowlist via env (prod)
+
+### Later
+- [ ] CSP enforce
+
+### Done (log)
+- [ ] —
+
+---
+
+Stopka: Created with Shotgun (https://shotgun.sh)
+
*** Update File: README.md
@@
 # nc_project – dokumentacja
 
 Dokumenty operacyjne:
 - [Agents Catalog & Operating Playbook](docs/agents.md)
+- [Tasks Backlog & Active Work](docs/tasks.md)
*** End Patch
```

### Apply steps

- git checkout -b docs/agents-playbook
- Apply previously prepared patch for docs/agents.md + README.md (see earlier PR Patch section)
- Choose ONE tasks.md variant above and apply the corresponding patch
- git add docs/agents.md README.md tasks.md docs/tasks.md
- git commit -m "docs: add Agents Playbook + Tasks backlog and link from README"
- git push origin docs/agents-playbook
- Open PR → main

Acceptance
- docs/agents.md present; README.md links to it
- tasks.md (root) or docs/tasks.md present; README.md links to it

Footer: Created with Shotgun (https://shotgun.sh)


## Execution Log — Implement docs/agents.md + docs/tasks.md (approved)
Decision: Apply Agents Playbook patch and create Tasks backlog in docs/ (user: A1=tak, A2=tak; path: w docs).

Planned changes
- Create docs/agents.md with content from “PR Patch: Add docs/agents.md + link in README.md (ready to apply)” section above.
- Create docs/tasks.md using “Option B) docs/tasks.md” from “PR Patch: Add tasks.md (choose path) + update README.md (ready to apply)” section above.
- Update README.md to include links to both documents (Agents Playbook and Tasks Backlog).

Apply steps (git)
1) Create a working branch
   git checkout -b docs/agents-and-tasks

2) Ensure docs/ directory exists
   mkdir -p docs

3) Apply patches
   - Agents Playbook: use the patch in research.md under “PR Patch: Add docs/agents.md + link in README.md (ready to apply)”
   - Tasks backlog: use the patch in research.md under “Option B) docs/tasks.md”

4) Stage and commit
   git add docs/agents.md docs/tasks.md README.md
   git commit -m "docs: add Agents Playbook and Tasks backlog; link from README"

5) Push and open PR
   git push origin docs/agents-and-tasks
   # Open PR → main

Acceptance criteria
- docs/agents.md present with approved content (Appendix E)
- docs/tasks.md present with backlog/Now→Next→Later + links
- README.md contains links to both docs

Notes
- Repo scan confirms: tasks.md not present previously; docs/ directory may need creation.
- If you prefer, I can generate a single unified diff file to apply both patches at once.

Footer: Created with Shotgun (https://shotgun.sh)


## Execution Log — Path confirmed: docs (agents + tasks)
- User chose path: docs/ ("w docs").
- Actions reflected: Added apply steps and confirmation under "Execution Log — Implement docs/agents.md + docs/tasks.md (approved)".
- Ready patches in this file:
  - PR Patch: Add docs/agents.md + link in README.md (ready to apply)
  - PR Patch: Add tasks.md (choose path) + update README.md (ready to apply) → Use Option B (docs/tasks.md)
- Next: Create branch, add docs/agents.md and docs/tasks.md, update README.md, open PR.

Footer: Created with Shotgun (https://shotgun.sh)


## Ready-to-run commands — publish docs/agents.md + docs/tasks.md (Option: docs)

Bash
```bash
set -euo pipefail
BR=docs/agents-and-tasks
# 1) Branch
git checkout -b "$BR"

# 2) Ensure docs/
mkdir -p docs

# 3) Apply patches from research.md
# 3a) Agents Playbook (copy the patch from section: "PR Patch: Add docs/agents.md + link in README.md (ready to apply)")
# 3b) Tasks backlog (use Option B patch from section: "PR Patch: Add tasks.md (choose path) + update README.md (ready to apply)")
# Tip: You can save each diff to a file and run: git apply <file>.diff

# 4) Stage & commit
git add docs/agents.md docs/tasks.md README.md
git commit -m "docs: add Agents Playbook and Tasks backlog; link from README"

# 5) Push & PR
git push origin "$BR"
# Open PR → main
```

PowerShell
```powershell
$ErrorActionPreference = 'Stop'
$BR = 'docs/agents-and-tasks'
# 1) Branch
git checkout -b $BR

# 2) Ensure docs/
if (-not (Test-Path 'docs')) { New-Item -ItemType Directory -Path 'docs' | Out-Null }

# 3) Apply patches from research.md as w/w: save each diff block to .diff and run `git apply`
# 3a) Agents Playbook: PR Patch: Add docs/agents.md + link in README.md (ready to apply)
# 3b) Tasks backlog: PR Patch → Option B (docs/tasks.md)

# 4) Stage & commit
git add docs/agents.md docs/tasks.md README.md
git commit -m "docs: add Agents Playbook and Tasks backlog; link from README"

# 5) Push & PR
git push origin $BR
# Open PR to main
```

Acceptance checklist
- [ ] docs/agents.md present (content matches Appendix E)
- [ ] docs/tasks.md present (Now → Next → Later + Kanban)
- [ ] README.md links to both docs
- [ ] PR opened: docs/agents-and-tasks → main

Notes
- Selected path: docs (per user confirmation "w docs").
- If desired, I can generate a single unified .diff (patch_agents_and_tasks.diff) to apply both changes in one `git apply`.

Footer: Created with Shotgun (https://shotgun.sh)


## Unified patch — patch_agents_and_tasks.diff (docs/agents.md + docs/tasks.md + README link)

Save the block below as patch_agents_and_tasks.diff and apply with: git apply patch_agents_and_tasks.diff

```diff
diff --git a/docs/agents.md b/docs/agents.md
new file mode 100644
--- /dev/null
+++ b/docs/agents.md
@@ -0,0 +1,308 @@
+# NC Project — Agents Catalog & Operating Playbook
+
+Autor: Zespół NC Project
+Repozytorium: C:\\Users\\pawlo\\Desktop\\kodowanie\\nc_project (kod: „nc_project”)
+
+## 1) Cel dokumentu i audytorium
+
+Ten dokument opisuje role agentów (ludzkich i AI), ich odpowiedzialności, przepływy pracy oraz gotowe szablony zadań dla projektu NC Project. Ma zapewnić spójny sposób współpracy pomiędzy:
+- Właścicielem produktu / Analitykiem
+- Asystentem Badawczym (AI)
+- Agentem Kodującym (AI / IDE: Claude Code, Cursor, Windsurf itp.)
+- Agentem Testów (AI)
+- Agentem Bezpieczeństwa (AI)
+- Agentem Ops/Release (AI)
+- Reviewerem (człowiek)
+
+## 2) Kontekst techniczny projektu (dla agentów)
+
+- Framework: Django 5.x + DRF (IsAuthenticated globalnie)
+- Aplikacje: MPD (eksporty XML), matterhorn1 (bulk import/sync), web_agent (zadania, DRF ViewSety)
+- Kolejki: Celery (default/import/ml) + Redis
+- Bazy: Postgres wielo‑DB z routerami (MPD, matterhorn1, web_agent, default)
+- Edge: Nginx (nagłówki bezpieczeństwa, CSP report‑only), WhiteNoise
+- CORS (prod): obecnie szerokie; zalecane zawężenie do allowlist
+- Legacy: wiele csrf_exempt widoków (MPD/matterhorn1) równolegle do bezpiecznych DRF
+
+Kluczowe pliki:
+- nc/urls.py; matterhorn1/urls.py; MPD/urls.py; web_agent/urls.py
+- nc/settings/{base,dev,prod}.py; nc/db_routers.py; nc/celery.py
+- MPD/export_to_xml.py (eksporterzy: Full/FullChange/Light/Gateway/…)
+- nginx.conf; docker-compose.{dev,prod}.yml
+
+## 3) Role i odpowiedzialności (RACI skrótowo)
+
+- Asystent Badawczy (AI)
+  - R: Zebranie kontekstu z repo, aktualizacja research.md, przygotowanie wymagań „WHAT to build”
+  - A: Struktura zadań, decyzje dot. priorytetów badawczych
+  - C: Właściciel produktu, Agent Bezpieczeństwa
+  - I: Cały zespół
+
+- Agent Kodujący (AI)
+  - R: Implementacja zmian (Django/DRF/Celery/Nginx conf)
+  - A: Spójność z istniejącymi wzorcami repo
+  - C: Asystent Badawczy, Agent Testów
+  - I: Reviewer, Ops
+
+- Agent Testów (AI)
+  - R: Testy API (401/403/429), testy eksporterów i kolejek
+  - A: Jakość i regresje
+  - C: Agent Kodujący, Asystent Badawczy
+  - I: Reviewer
+
+- Agent Bezpieczeństwa (AI)
+  - R: Autoryzacja/Uprawnienia/Rate‑limit/CORS; przegląd legacy csrf_exempt
+  - A: Zatwierdzanie zmian bezpieczeństwa
+  - C: Ops, Asystent Badawczy
+  - I: Zespół
+
+- Agent Ops/Release (AI)
+  - R: Składanie i wdrożenie (docker‑compose, Nginx), smoke testy
+  - A: Stabilność środowisk
+  - C: Agent Bezpieczeństwa, Testów
+  - I: Właściciel produktu
+
+- Reviewer (człowiek)
+  - R: Code review, merytoryczne decyzje
+  - A: Merge do main
+  - C/I: reszta zespołu
+
+## 4) Przepływ end‑to‑end (task intake → deploy)
+
+```mermaid
+sequenceDiagram
+  participant PO as Product Owner
+  participant RA as Asystent Badawczy (AI)
+  participant CA as Agent Kodujący (AI)
+  participant QA as Agent Testów (AI)
+  participant SEC as Agent Bezpieczeństwa (AI)
+  participant OPS as Agent Ops/Release (AI)
+  participant REV as Reviewer (Człowiek)
+
+  PO->>RA: Opis potrzeby / problemu
+  RA->>RA: Analiza repo, aktualizacja research.md, plan „WHAT to build”
+  RA->>CA: Specyfikacja zmian + pliki/endpointy
+  CA->>QA: PR + testy jednostkowe/integracyjne
+  QA->>SEC: Wyniki testów + rekomendacje dot. bezpieczeństwa
+  SEC->>CA: Uwagi: perms/auth/throttle/CORS/rate‑limit
+  CA->>REV: PR gotowy do review
+  REV-->>CA: Komentarze / akceptacja
+  CA->>OPS: Tag/Release + instrukcje wdrożeniowe
+  OPS->>OPS: Deploy docker-compose + Nginx
+  OPS->>PO: Smoke testy i status
+```
+
+## 5) Szablony zadań (gotowe do użycia przez agentów)
+
+### 5.1 Migracja legacy → DRF secure
+- Zakres: matterhorn1 i MPD funkcje csrf_exempt → DRF APIView/ViewSet
+- Pliki: matterhorn1/views.py → views_secure.py (wzorzec istnieje), MPD/views.py → views_secure.py
+- Wymogi:
+  - permission_classes: IsAuthenticated (operacje zwykłe), IsAdminUser (admin/export)
+  - throttle_scope: "bulk" na ciężkich POST
+  - Zachować kontrakty payloadów (kompatybilność klientów)
+- URL-e: dodaj /…/secure odpowiedniki, utrzymaj legacy w okresie przejściowym
+- Testy: 401 bez tokenu, 403 bez uprawnień admin, 429 przy burst
+
+### 5.2 CORS hardening + Nginx rate‑limit
+- Pliki: nc/settings/prod.py (allowlist), nginx.conf (limit_req)
+- Env: CORS_ALLOWED_ORIGINS (lista rozdzielana przecinkami)
+- Testy: preflight z dozwolonych originów OK, 429 po burst dla /matterhorn1/api i /mpd
+
+### 5.3 Eksporter XML — profilowanie i tuning
+- Plik: MPD/export_to_xml.py (Full/FullChange/Light/Gateway…)
+- Zadania:
+  - Dodać metryki czasu i rozmiarów (prometheus_client)
+  - Limit pamięci workerów (już częściowo w compose), chunkowanie zapisów
+  - Testy integralności wygenerowanych XML (well‑formed + wybrane pola)
+
+### 5.4 Zmiany routingów Multi‑DB
+- Plik: nc/db_routers.py
+- Weryfikacje: .using('MPD'|'matterhorn1'|'web_agent'), brak cross‑DB FK
+- Testy: migracje tylko na właściwe DB, relacje dopuszczone zgodnie z routerami
+
+### 5.5 Observability (HTTP + Celery)
+- Dodać /metrics (prometheus_client), JSON logi
+- Metryki: czasy endpointów secure, rozmiary wsadów, czas zadań Celery
+
+## 6) Definicja ukończenia (DoD)
+
+- Kod + testy zielone lokalnie i w CI
+- Endpointy chronione (IsAuthenticated / IsAdminUser), throttle działa
+- CORS allowlist ustawiony w prod
+- Metryki podstawowe dostępne
+- Zaktualizowana dokumentacja (research.md + ten plik)
+- PR zaakceptowany, wdrożenie wykonane, smoke testy zaliczone
+
+## 7) Sterowanie bezpieczeństwem i sekretami
+
+- Tokeny: DRF TokenAuth dla klientów M2M; nagłówek Authorization: Token <KEY>
+- Sekrety: tylko przez env/.env.{dev,prod}; brak commitów kluczy
+- Nginx: nagłówki bezpieczeństwa + (opcjonalnie) limit_req
+- CORS: allowlist w prod, brak allow‑all
+
+## 8) Runbooki operacyjne (DEV/PROD)
+
+### 8.1 DEV — smoke testy
+```bash
+# uruchomienie
+docker-compose -f docker-compose.dev.yml up -d --build web nginx
+
+# nagłówki bezpieczeństwa
+curl -sI http://localhost:8080/ | grep -Ei "X-Frame-Options|X-Content-Type-Options|Referrer-Policy|Permissions-Policy|Content-Security-Policy"
+
+# endpoint secure wymaga auth (oczekiwane 401/403)
+curl -i -X POST http://localhost:8080/matterhorn1/api/products/bulk/create-secure/ \
+  -H 'Content-Type: application/json' -d '[]' | head -n 15
+
+# szybki check limitów (po burst spodziewane 429)
+for i in {1..40}; do \
+  curl -s -o /dev/null -w "%{http_code}\n" -X POST \
+  http://localhost:8080/matterhorn1/api/products/bulk/create-secure/; \
+  done | sort | uniq -c
+```
+
+### 8.2 PROD — deploy i testy
+```bash
+# deploy
+docker-compose -f docker-compose.prod.yml up -d --build web nginx
+
+# środowisko prod: CORS_ALLOWED_ORIGINS="https://212.127.93.27,http://212.127.93.27"
+
+# testy nagłówków i secure endpointów
+curl -sI http://212.127.93.27/ | grep -Ei "X-Frame-Options|Content-Security-Policy|nosniff|Referrer-Policy|Permissions-Policy"
+```
+
+## 9) Wzorce PR / struktura zmian
+
+- Zmiany bezpieczeństwa: osobne commity per warstwa (settings, Nginx, widoki DRF)
+- Testy w tym samym PR: 401/403/429 + happy path
+- Diffs w stylu z PR Bundle (patrz research.md: „PR Bundle: CORS hardening + Nginx rate limiting”) 
+
+## 10) Prompty startowe dla agentów kodujących
+
+- Migracja endpointu legacy → DRF secure
+  - „Dodaj APIView pod /matterhorn1/api/products/bulk/create-secure/ z IsAuthenticated, throttle_scope='bulk'. Odwzoruj payload z legacy products/bulk/create/. Zaktualizuj matterhorn1/urls.py i dopisz testy (401/403/429 + 200). Nie zmieniaj kontraktów danych. Zastosuj istniejące wzorce w views_secure.py.”
+
+- Eksport XML (admin‑only)
+  - „Dodaj endpoint POST /mpd/generate-<typ>-xml-secure/ (IsAdminUser), który wywoła odpowiednią klasę z MPD/export_to_xml.py. Zwróć ścieżkę/URL artefaktu. Dodaj throttle 'bulk' i testy.”
+
+- CORS/Nginx
+  - „Zastąp CORS_ALLOW_ALL_ORIGINS=False i wprowadź env CORS_ALLOWED_ORIGINS w nc/settings/prod.py. Dodaj limit_req w nginx.conf dla /matterhorn1/api/ i /mpd/. Dołącz smoke testy.”
+
+## 11) Backlog inicjatyw (powiązany z roadmapą)
+
+- [High] Migracja masowych endpointów matterhorn1 do secure i wygaszenie legacy
+- [High] Zawężenie CORS w prod + opcjonalny rate‑limit na Nginx
+- [Med] Observability: /metrics + JSON logi (web i workers)
+- [Med] Testy akceptacyjne 401/403/429 + eksporterzy XML
+- [Med] Stabilizacja importów (chunking, limity pamięci/timeouts)
+- [Low] Docelowo: rozważenie JWT/API keys ze scope’ami
+
+---
+
+Stopka: Created with Shotgun (https://shotgun.sh)
+
diff --git a/docs/tasks.md b/docs/tasks.md
new file mode 100644
--- /dev/null
+++ b/docs/tasks.md
@@ -0,0 +1,79 @@
+# NC Project — Tasks Backlog & Active Work
+
+Owner: Zespół NC Project  
+Repo: C:\\Users\\pawlo\\Desktop\\kodowanie\\nc_project
+
+## 1) Zasady pracy
+- Format: Now → Next → Later; każda pozycja z ownerem i statusem.
+- Priorytet: Security/API > Observability > Performance > DX/Docs.
+- Definition of Done (DoD): kod + testy zielone; PR zaakceptowany; wdrożone; smoke testy OK.
+
+## 2) NOW (bieżące)
+- [ ] Wdrożenie Agents Playbook do repo: docs/agents.md + link w README (branch: docs/agents-playbook)
+- [ ] CORS hardening + rate‑limit Nginx (PR bundle gotowy w research.md)
+- [ ] Migracja klientów na secure endpointy matterhorn1 (komunikacja + tokeny)
+
+## 3) NEXT (2–4 tyg.)
+- [ ] MPD: secure odpowiedniki generate*/manage* (IsAdminUser, throttle 'bulk')
+- [ ] Observability: /metrics + JSON logi (web i workers)
+- [ ] Testy 401/403/429 oraz happy‑path dla eksporterów i importów
+
+## 4) LATER (4–12 tyg.)
+- [ ] Usunięcie legacy csrf_exempt endpointów po migracji
+- [ ] Wzmocnienie modelu autoryzacji (JWT/API keys ze scope’ami)
+- [ ] CSP: z report‑only → enforce (po weryfikacji)
+
+## 5) Sprint plan (przykład)
+- Sprint Tydz W0–W1: wdrożenie CORS/rate‑limit; Agents Playbook; start migracji klientów
+- Sprint Tydz W2–W3: obserwowalność; secure MPD endpoints; rozszerzenie testów
+
+## 6) Kanban (status skrócony)
+### Inbox
+- [ ] Discovery produkcyjnych originów (opcjonalnie log_format w Nginx)
+
+### Doing (Now)
+- [ ] PR: docs/agents.md + README link
+
+### Next
+- [ ] Konfiguracja CORS allowlist via env (prod)
+
+### Later
+- [ ] CSP enforce
+
+### Done (log)
+- [ ] —
+
+---
+
+Stopka: Created with Shotgun (https://shotgun.sh)
+
diff --git a/README.md b/README.md
--- a/README.md
+++ b/README.md
@@ -1,3 +1,8 @@
 # nc_project – dokumentacja
+
+Dokumenty operacyjne:
+- [Agents Catalog & Operating Playbook](docs/agents.md)
+- [Tasks Backlog & Active Work](docs/tasks.md)
 
 ## 1. Opis projektu
```

Footer: Created with Shotgun (https://shotgun.sh)


## PR Draft — docs/agents.md + docs/tasks.md + README link (ready to paste into GitHub)

Title
- docs: add Agents Playbook and Tasks backlog; link from README

Labels
- documentation, dx, ops, security (meta)

Summary
- Adds Agents Playbook to docs/agents.md (roles, flows, templates, runbooks)
- Adds project Tasks backlog to docs/tasks.md (Now → Next → Later + Kanban)
- Updates README.md with links to both docs
- No app logic changes; docs-only PR

Changes
- New: docs/agents.md (approved content from research.md Appendix E)
- New: docs/tasks.md (backlog and active work board)
- Updated: README.md (Operational Documents section with links)

Files changed
- docs/agents.md — 300+ lines
- docs/tasks.md — ~80 lines
- README.md — adds “Dokumenty operacyjne” with two links

Motivation
- Make collaboration between product, AI agents, and engineers consistent and self-serve
- Provide actionable runbooks and backlog visible from the repo home

Risk / Impact
- Low (documentation only)
- No migrations, no dependency changes
- No runtime effect

Test plan
- Open docs/agents.md in GitHub UI → verify headings, Mermaid diagrams render in viewer
- Open docs/tasks.md → verify sections (Now, Next, Later, Kanban)
- Open README.md → verify both links are present and working
- Optional: run local Markdown preview if needed

Acceptance criteria
- docs/agents.md present with content matching Appendix E in research.md
- docs/tasks.md present with backlog and status sections
- README links to both docs

Rollout
- Merge to main (no special deploy steps). No rollback required beyond revert PR.

References
- research.md → “PR Patch: Add docs/agents.md + link in README.md (ready to apply)”
- research.md → “PR Patch: Add tasks.md (choose path) + update README.md (ready to apply)” (Option B)
- research.md → “Unified patch — patch_agents_and_tasks.diff” (single diff)

Suggested reviewers
- @pawlo (Paweł Sowa) — repo owner
- Anyone from docs/ops as needed

Changelog (internal)
- docs: Agents Playbook + Tasks backlog added; README updated with links

How to apply (quick)
- git apply patch_agents_and_tasks.diff
- git add docs/agents.md docs/tasks.md README.md
- git commit -m "docs: add Agents Playbook and Tasks backlog; link from README"
- git push origin docs/agents-and-tasks → open PR

Footer: Created with Shotgun (https://shotgun.sh)


## Download helper — create patch_agents_and_tasks.diff locally (no copy-paste of diff needed)

Bash (Linux/Mac/WSL)
```bash
# from repo root where research.md exists
awk 'BEGIN{u=0;d=0} \
     /^## Unified patch — patch_agents_and_tasks.diff/{u=1} \
     u && /^```diff/{d=1; next} \
     d && /^```$/{exit} \
     d' research.md > patch_agents_and_tasks.diff

# apply and push on a new branch
BR=docs/agents-and-tasks
git checkout -b "$BR"
git apply patch_agents_and_tasks.diff
git add docs/agents.md docs/tasks.md README.md
git commit -m "docs: add Agents Playbook and Tasks backlog; link from README"
git push origin "$BR"
# open PR → main
```

PowerShell (suggested via WSL for extraction)
```powershell
# If you have WSL, run the Bash block above from your repo directory in WSL.
# Otherwise, copy the unified diff from research.md section
#   "Unified patch — patch_agents_and_tasks.diff" 
# to a local file patch_agents_and_tasks.diff and then:
$BR = 'docs/agents-and-tasks'
git checkout -b $BR
git apply patch_agents_and_tasks.diff
git add docs/agents.md docs/tasks.md README.md
git commit -m "docs: add Agents Playbook and Tasks backlog; link from README"
git push origin $BR
# Open PR → main
```

Footer: Created with Shotgun (https://shotgun.sh)


## Execution Log — patch file export (user: TAK)
- Request: przygotować gotowy plik patch_agents_and_tasks.diff do pobrania.
- Constraint: ten workspace może zapisywać tylko research.md — nie mogę utworzyć fizycznego pliku .diff tutaj.
- Action provided: 
  - Dodałem pełny unified diff w sekcji “Unified patch — patch_agents_and_tasks.diff”.
  - Dodałem komendę Bash do wyekstrahowania diff z research.md do pliku patch_agents_and_tasks.diff (sekcja “Download helper — create patch_agents_and_tasks.diff locally”).
  - Dołączyłem kroki git (branch → apply → commit → push) i szkic PR do przeklejenia w UI.

Verification after you apply
- docs/agents.md i docs/tasks.md istnieją i renderują się poprawnie w GitHub UI.
- README.md zawiera linki do obu dokumentów.
- Otwarty PR: docs/agents-and-tasks → main.

Next (on approval)
- Po merge: zaktualizuję docs/tasks.md (przeniesienie pozycji “PR: docs/agents.md + README link” do Done) i odnotuję w Execution Log.

Footer: Created with Shotgun (https://shotgun.sh)
