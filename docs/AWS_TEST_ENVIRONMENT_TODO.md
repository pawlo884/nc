# AWS Test Environment — TODO (ćwiczenie nauki architektury AWS)

Ten dokument to checklista krok-po-kroku do postawienia **testowej kopii** projektu `nc_project` na AWS. Celem jest **nauka architektury AWS**, nie zbudowanie kolejnego środowiska produkcyjnego — masz już produkcję na bare-metal/k3s (`deployments/k8s/nc-prod/`) i tam nic się nie zmienia.

**Wykonawca kroków: Ty.** Ja (Claude) nie klikam w konsoli AWS ani nie odpalam `terraform apply` za Ciebie — to jest ćwiczenie, chodzi o to żebyś sam przeszedł przez każdy krok i zrozumiał po co on jest. Wracaj do mnie w dowolnym momencie z błędem, outputem terminala albo pytaniem "co to znaczy" — pomogę zdiagnozować i wytłumaczę, ale kroki wykonujesz Ty.

## Założenia (ustalone wspólnie)

| Decyzja | Wybór | Dlaczego |
|---|---|---|
| Architektura | ECS Fargate + RDS Postgres + ElastiCache Redis + S3 + ALB | "natywna AWS" zamiast lift-and-shift — to ma nauczyć usług zarządzanych |
| IaC | Terraform | najpopularniejsze narzędzie, przenośne, dużo materiałów |
| Region | `eu-north-1` (Sztokholm) | wybór użytkownika |
| Sieć | **bez NAT Gateway** — Fargate w podsieciach publicznych z publicznym IP + restrykcyjne Security Groups | NAT Gateway (~$32/mies) sam zjadłby większość budżetu $20-50/mies. To świadomy kompromis dev/test — **nie rób tak na produkcji** |
| Domena/TLS | `aws-test.sowa.ch` + certyfikat ACM | masz już domenę sowa.ch używaną do produkcji, dodajemy poddomenę |
| Budżet | ~$20-50/mies | patrz tabela kosztów na końcu — jest ciasno |

## Zanim zaczniesz — fakty o kodzie, które musisz znać

- Projekt ma **6 logicznych baz danych w jednym Postgresie** (`default`, `MPD`, `matterhorn1`, `web_agent`, `tabu`, `mada`), routowanych przez [`src/core/db_routers.py`](src/core/db_routers.py). Nie potrzebujesz 6 instancji RDS — **jedna instancja RDS**, na niej 6 baz (`CREATE DATABASE`), każda para env vars (`MPD_DB_HOST`, `TABU_DB_HOST`, itd.) wskazuje ten sam host/port, różni się tylko `*_DB_NAME`.
- Redis jest **jeden**, obsługuje i cache (`base.py:443-451`), i broker Celery (`base.py:407-408`, `prod.py:234-266`) na różnych numerach bazy (`/0`, `/1`). Wystarczy **jeden node ElastiCache**.
- Kod **już obsługuje czyste S3** bez MinIO — zobacz [`src/core/settings/base.py:568-615`](src/core/settings/base.py#L568-L615). Zmienne `MINIO_*` mają priorytet nad `AWS_*`, więc na AWS **po prostu nie ustawiaj `MINIO_*`**. I nie ustawiaj też `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY` — jeśli je pominiesz, boto3 sam użyje uprawnień z ECS task role (bez statycznych kluczy w env — bezpieczniejsze i to jest "ta" nauka o IAM rolach).
- Jest gotowy health-check endpoint `/health/` ([`src/core/urls.py:38`](src/core/urls.py#L38)) — użyjesz go jako ALB target group health check.
- Do budowania obrazu używasz **istniejącego** [`deployments/docker/Dockerfile.prod`](deployments/docker/Dockerfile.prod) — nie twórz nowego.
- ✅ **Naprawione**: `Dockerfile.prod` wcześniej nie kopiował appki `mada`, mimo że jest w `INSTALLED_APPS` — dodano brakującą linię `COPY src/apps/mada/ ./mada/`. Sam fakt, że ten bug istniał niezauważony, to argument by w Fazie 5 i tak zrobić `python manage.py check` na świeżo zbudowanym obrazie, zanim wjedzie na AWS.
- Istniejące CI/CD (`.github/workflows/deploy-vps.yml`, `deploy-test.yml`) dotyczą k3s/VPS — **nie ruszaj ich**. Nowy workflow dla AWS to osobny plik.

---

## Faza 0 — Konto AWS i podstawy bezpieczeństwa

**Cel:** mieć konto z którego bezpiecznie korzystasz i alarm, który Cię ostrzeże zanim przepalisz budżet.

- [ ] Załóż/zaloguj się na konto AWS (jeśli nowe konto — sprawdź, czy kwalifikuje się do Free Tier, to obniży koszty RDS/ElastiCache w pierwszym roku)
- [ ] Włącz MFA na koncie **root** (Account → Security credentials → MFA)
- [ ] Utwórz użytkownika IAM do codziennej pracy (np. `terraform-admin`) z grupą uprawnień — **nie pracuj na roocie na co dzień**
- [ ] Zainstaluj AWS CLI v2 lokalnie i skonfiguruj profil: `aws configure --profile nc-aws-test`
- [ ] Zweryfikuj dostęp: `aws sts get-caller-identity --profile nc-aws-test`
- [ ] **Ustaw AWS Budgets billing alarm** ZANIM zrobisz cokolwiek dalej: AWS Billing → Budgets → utwórz budżet miesięczny np. $40 z alertem e-mail przy 80% i 100%
- [ ] Zainstaluj Terraform lokalnie (`terraform -version`)

**Punkt kontrolny:** zgłoś się z outputem `aws sts get-caller-identity` zanim przejdziesz dalej.

**Do nauki:** root account vs IAM users to fundament modelu bezpieczeństwa AWS — root ma pełne uprawnienia i nie powinien być używany do pracy dnia codziennego. Budget alerts to pierwsza linia obrony przed niespodziewanym rachunkiem, szczególnie ważne przy nauce, gdzie łatwo zostawić coś włączonego.

---

## Faza 1 — Terraform bootstrap (backend na stan)

**Cel:** mieć miejsce, gdzie Terraform bezpiecznie trzyma swój stan (nie lokalnie na dysku).

- [ ] Utwórz w repo katalog `infra/aws-test/` (osobno od `deployments/k8s/`, `docker-compose/`)
- [ ] Ręcznie (albo osobnym mini-Terraformem "bootstrap") utwórz: S3 bucket na state (np. `nc-project-tfstate-aws-test`, z versioning i encryption włączonym) + DynamoDB table na state lock (np. `nc-project-tfstate-lock`, partition key `LockID`)
- [ ] Utwórz `infra/aws-test/backend.tf` wskazujący ten bucket/tabelę
- [ ] Utwórz `infra/aws-test/providers.tf` z `provider "aws" { region = "eu-north-1" }`
- [ ] Utwórz `infra/aws-test/variables.tf` z podstawowymi zmiennymi (region, project_name, environment)
- [ ] `terraform init` w `infra/aws-test/`

**Punkt kontrolny:** zgłoś się z outputem `terraform init` i strukturą katalogu.

**Do nauki:** Terraform state to "prawda" o tym co istnieje — trzymanie go w S3 z DynamoDB lock pozwala bezpiecznie pracować zespołowo (i nie zgubić stanu gdy dysk padnie). To standardowy wzorzec w każdej realnej firmie używającej Terraform.

---

## Faza 2 — Sieć (VPC)

**Cel:** własna sieć izolowana od innych klientów AWS, z podsieciami publicznymi w 2 strefach dostępności (do wysokiej dostępności ALB/RDS).

- [ ] Zdefiniuj w Terraform: VPC (np. `10.0.0.0/16`)
- [ ] 2 podsieci publiczne w różnych AZ (np. `eu-north-1a`, `eu-north-1b`), np. `10.0.1.0/24` i `10.0.2.0/24`
- [ ] Internet Gateway + route table kierująca `0.0.0.0/0` na IGW, przypisana do obu podsieci publicznych
- [ ] Security Groups (osobne resource per warstwa, minimalny dostęp):
  - `alb_sg` — inbound 80/443 z `0.0.0.0/0`
  - `ecs_tasks_sg` — inbound tylko z `alb_sg` na porcie gunicorn (8000)
  - `rds_sg` — inbound tylko z `ecs_tasks_sg` na 5432
  - `elasticache_sg` — inbound tylko z `ecs_tasks_sg` na 6379
- [ ] `terraform plan` i przejrzyj co się utworzy, potem `terraform apply`

**Punkt kontrolny:** zgłoś się z outputem `terraform plan` PRZED apply, żeby przejrzeć razem czy security groups są wystarczająco restrykcyjne.

**Do nauki:** brak NAT Gateway oznacza, że Twoje zadania Fargate mają publiczne IP i wychodzą do internetu bezpośrednio przez IGW — to obniża izolację względem architektury z prywatnymi podsieciami + NAT, dlatego Security Groups tutaj są jedyną linią obrony na poziomie sieci. Zrozum różnicę między "publiczna podsieć" (ma trasę do IGW) a "publiczny zasób" (ma publiczny IP) — to częste źródło nieporozumień.

---

## Faza 3 — Dane: RDS Postgres + ElastiCache Redis

**Cel:** postawić bazę i cache/broker.

- [ ] RDS: `db.t3.micro`, silnik Postgres (dopasuj wersję do tego czego używasz teraz), `multi_az = false`, 20GB storage, w `rds_sg`, subnet group obejmujący obie podsieci
- [ ] Hasło administratora RDS → wygeneruj losowo, zapisz w **AWS Secrets Manager** (nie w `.tf` w plaintext, nie w repo!)
- [ ] Po utworzeniu instancji: połącz się (`psql`) i utwórz 6 baz: `default`, `MPD`, `matterhorn1`, `web_agent`, `tabu`, `mada` (dopasuj nazwy do realnych `*_DB_NAME` z Waszego `.env.dev`/`.env.prod`)
- [ ] ElastiCache: Redis, `cache.t3.micro`, `elasticache_sg`, `transit_encryption_enabled = true`, auth token → też do Secrets Manager
- [ ] Zapisz w Secrets Manager (osobne secrety albo jeden JSON): hasła 6 baz (mogą być wspólne dla jednego usera albo per-baza — Twój wybór), Redis auth token, `DJANGO_SECRET_KEY` (wygeneruj nowy, nie kopiuj z prod!)

**Punkt kontrolny:** zgłoś się z endpointem RDS i ElastiCache (bez haseł) — sprawdzimy razem że env vars w Fazie 6 będą się zgadzać z tym co ustawiłeś tutaj.

**Do nauki:** Secrets Manager (lub tańszy SSM Parameter Store SecureString) to standard trzymania sekretów w AWS — ECS task definition odwołuje się do nich przez ARN, sekret nigdy nie trafia do obrazu Docker ani do logów Terraform state w plaintext (choć state i tak trzeba traktować jako wrażliwy).

---

## Faza 4 — Storage (S3)

**Cel:** bucket na media, zamiennik obecnego MinIO.

- [ ] S3 bucket (np. `nc-project-aws-test-media`), region `eu-north-1`, block public access **włączony** (dostęp tylko przez aplikację/presigned URLs, nie publiczny bucket)
- [ ] IAM policy ograniczona TYLKO do tego bucketu (get/put/delete/list) — to będzie policy przypięta do ECS task role w Fazie 6
- [ ] Sprawdź w [`src/core/settings/base.py:568-615`](src/core/settings/base.py#L568-L615) jakie dokładnie zmienne env musisz ustawić: `AWS_STORAGE_BUCKET_NAME` = nazwa bucketu. **Nie ustawiaj** `MINIO_*`, **nie ustawiaj** `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`

**Punkt kontrolny:** zgłoś się z nazwą bucketu i treścią IAM policy przed przejściem dalej.

**Do nauki:** to jest właśnie różnica między statycznymi kluczami dostępu a IAM rolami przypiętymi do zasobu compute (tu: ECS task) — rola dostarcza tymczasowe, automatycznie rotowane poświadczenia, więc nic nie wycieknie nawet jeśli ktoś zobaczy zmienne środowiskowe kontenera.

---

## Faza 5 — Obraz Docker i ECR

**Cel:** zbudować obraz produkcyjny i wypchnąć go do rejestru AWS.

- [ ] Zbuduj obraz lokalnie i sprawdź czy `python manage.py check` przechodzi bez błędów importu (fix dla `mada` już wgrany w `Dockerfile.prod`, patrz sekcja "Zanim zaczniesz")
- [ ] Utwórz ECR repository (np. `nc-project-aws-test`)
- [ ] Zaloguj Docker do ECR: `aws ecr get-login-password --region eu-north-1 --profile nc-aws-test | docker login --username AWS --password-stdin <account-id>.dkr.ecr.eu-north-1.amazonaws.com`
- [ ] Zbuduj obraz: `docker build -f deployments/docker/Dockerfile.prod -t nc-project-aws-test:manual-test .` (kontekst budowania to root repo — tak jak w obecnym CI)
- [ ] Otaguj i wypchnij do ECR
- [ ] Zweryfikuj lokalnie: uruchom kontener podając zmienne env wskazujące na RDS/ElastiCache z Faz 3-4 (z Twojego lokalnego IP musisz dodać tymczasowo regułę w `rds_sg`/`elasticache_sg` albo tunelować — pamiętaj usunąć tę regułę po teście!) i sprawdź `/health/`

**Punkt kontrolny:** zgłoś się jeśli build się nie powiedzie albo health-check nie odpowiada — to najczęstsze miejsce na błędy konfiguracji.

**Do nauki:** ECR to prywatny rejestr obrazów w AWS, analogiczny do Docker Hub, ale zintegrowany z IAM (dostęp kontrolowany rolami, nie osobnym loginem) — ECS/Fargate pobiera stąd obraz bez dodatkowej konfiguracji uwierzytelniania, jeśli task/execution role ma odpowiednie uprawnienia.

---

## Faza 6 — ECS Fargate

**Cel:** uruchomić aplikację jako zestaw serwisów bez zarządzania serwerami.

- [ ] ECS cluster (Fargate)
- [ ] Task execution role (pull z ECR, zapis logów CloudWatch, odczyt sekretów z Secrets Manager) — rola **inna** niż task role
- [ ] Task role (dostęp do S3 bucketu z Fazy 4) — to jest rola aplikacji, nie infrastruktury
- [ ] Task definition `web`: image z ECR, port 8000, komenda gunicorn, `secrets` blok wskazujący ARNs z Secrets Manager dla wszystkich `*_DB_PASSWORD`, `DJANGO_SECRET_KEY`, Redis auth token; `environment` blok dla nie-sekretnych wartości (hosty RDS/ElastiCache, nazwy baz, `DJANGO_SETTINGS_MODULE=core.settings.prod`, `AWS_STORAGE_BUCKET_NAME`, `DJANGO_ALLOWED_HOSTS=aws-test.sowa.ch`)
- [ ] Task definitions dla `celery-default`, `celery-import`, `celery-beat` (ten sam obraz, inna komenda — jak w obecnym `docker-compose.dev.yml`)
- [ ] Target group + Application Load Balancer w `alb_sg`, listener HTTP na 80 (na razie, HTTPS dochodzi w Fazie 7), health check `/health/`
- [ ] ECS service `web` (desired count 1, `assign_public_ip = true` bo jesteśmy w podsieci publicznej bez NAT), podłączony do target group
- [ ] ECS services dla workerów Celery (bez target group, po prostu `desired_count = 1`)
- [ ] **Migracje jako jednorazowy task, PRZED pierwszym `desired_count > 0` serwisu web**: `aws ecs run-task` z override komendy `python manage.py migrate --database=default` (powtórz per baza: `MPD`, `matterhorn1`, `web_agent`, `tabu` — sprawdź czy chcesz też `mada`), obserwuj `aws ecs describe-tasks` do zakończenia
- [ ] Dopiero teraz ustaw `desired_count` serwisu web na 1 i sprawdź w konsoli ECS/CloudWatch Logs czy kontener wstaje poprawnie

**Punkt kontrolny:** zgłoś się z outputem `aws ecs describe-services` i logami CloudWatch pierwszego uruchomienia — to najbardziej prawdopodobne miejsce na iterację.

**Do nauki:** rozdział execution role / task role to częste źródło pomyłek u początkujących — execution role to "AWS zarządzający kontenerem", task role to "Twoja aplikacja wewnątrz kontenera". Fargate = nie zarządzasz EC2 instancjami, AWS sam alokuje compute pod zadanie.

---

## Faza 7 — ALB HTTPS + domena aws-test.sowa.ch

**Cel:** działający HTTPS pod własną (pod)domeną.

- [ ] Zamów certyfikat ACM dla `aws-test.sowa.ch` w regionie `eu-north-1` (walidacja DNS)
- [ ] Dodaj rekord CNAME walidacyjny podany przez ACM u obecnego dostawcy DNS dla `sowa.ch`
- [ ] Poczekaj aż status certyfikatu = Issued
- [ ] Dodaj listener HTTPS (443) na ALB używający tego certyfikatu, forward do target group `web`
- [ ] Zmień listener HTTP (80) na redirect → HTTPS
- [ ] Dodaj rekord CNAME `aws-test.sowa.ch` → DNS name ALB u dostawcy DNS
- [ ] Zaktualizuj `DJANGO_ALLOWED_HOSTS` w task definition na `aws-test.sowa.ch` (jeśli jeszcze nie zrobione w Fazie 6)
- [ ] Sprawdź `https://aws-test.sowa.ch/health/`

**Punkt kontrolny:** zgłoś się jeśli certyfikat nie waliduje się po >30 min albo health-check nie odpowiada po podpięciu domeny.

**Do nauki:** ACM z walidacją DNS to darmowy, automatycznie odnawiany certyfikat TLS — częsty wzorzec produkcyjny w AWS, dużo prostszy niż ręczne Let's Encrypt.

---

## Faza 8 — CI/CD (GitHub Actions → AWS)

**Cel:** automatyczny deploy przy pushu, bez naruszania istniejących pipeline'ów k3s.

- [ ] Skonfiguruj OIDC federation GitHub Actions ↔ AWS IAM (rola z zaufaniem do repo, **nie** długożyjące klucze AWS w GitHub Secrets)
- [ ] IAM policy dla tej roli: push do ECR, `ecs update-service`/`run-task` na tym konkretnym klastrze/service, `iam:PassRole` dla task/execution role
- [ ] Nowy plik `.github/workflows/deploy-aws-test.yml` (osobny od `deploy-vps.yml`/`deploy-test.yml`!), trigger np. na branch `aws-test` albo `workflow_dispatch`
- [ ] Kroki workflow: build obrazu z `Dockerfile.prod` → push do ECR z tagiem `${{ github.sha }}` → (jeśli są nowe migracje) `run-task` migracji → `ecs update-service --force-new-deployment` dla `web` i workerów → poczekaj na `services-stable` → curl `/health/`
- [ ] Przetestuj cały pipeline pushując pusty commit na branch `aws-test`

**Punkt kontrolny:** zgłoś się z linkiem do run'a GitHub Actions jeśli coś czerwone.

**Do nauki:** OIDC federation eliminuje najczęstszą lukę bezpieczeństwa w CI/CD do chmury — długożyjące access keys w sekretach repo. GitHub wystawia krótkotrwały token, AWS wymienia go na tymczasowe poświadczenia roli.

---

## Faza 9 — Weryfikacja końcowa i sprzątanie

- [ ] Smoke-test: `/health/`, logowanie do `/admin/`, upload pliku (sprawdź czy ląduje w S3), uruchomienie jakiegoś taska Celery i sprawdzenie że worker go odebrał (CloudWatch Logs)
- [ ] Po tygodniu: przejrzyj **Cost Explorer** — porównaj rzeczywisty koszt z tabelą szacunkową poniżej
- [ ] Jeśli chcesz oszczędzać między sesjami nauki: `aws ecs update-service --desired-count 0` dla web i workerów (RDS/ElastiCache/ALB nadal kosztują, ale Fargate przestaje)
- [ ] **Na koniec ćwiczenia**: `terraform destroy` w `infra/aws-test/` + ręczne usunięcie S3 bucketu state/DynamoDB lock table (Terraform ich nie usunie, bo to backend, nie resource) + usunięcie ECR repo (jeśli ma obrazy, trzeba najpierw je wyczyścić albo dodać `force_delete = true`)

**Do nauki:** to jest krok, który najczęściej ginie w tutorialach — w prawdziwej pracy z chmurą "posprzątaj po sobie" jest tak samo ważne jak "postaw to".

---

## Szacunkowy koszt miesięczny (eu-north-1, bez Free Tier)

| Usługa | Konfiguracja | ~USD/mies |
|---|---|---|
| ALB | 1 ALB + niski ruch | ~$16 |
| RDS | db.t3.micro, single-AZ, 20GB | ~$13 |
| ElastiCache | cache.t3.micro | ~$11 |
| ECS Fargate | 3 małe taski (web + 2× celery + beat), 0.25 vCPU/0.5GB, 24/7 | ~$15-20 |
| S3 + ECR + Secrets Manager | ruch testowy | ~$1-3 |
| **Suma** | | **~$56-63** |

To jest **powyżej** górnej granicy $50/mies przy pracy 24/7. Żeby zmieścić się w budżecie:
- z nowym kontem AWS część kosztów RDS/ElastiCache pokryje Free Tier przez pierwsze 12 miesięcy (sprawdź w Fazie 0, czy się kwalifikujesz) — to może zejść do ~$30-35/mies,
- albo zatrzymuj `desired_count` na Fargate poza godzinami nauki (Faza 9) — Fargate to jedyny komponent, który realnie skaluje się do zera bez utraty danych,
- ALB i RDS/ElastiCache kosztują nawet gdy nic ich nie używa (to "koszt zarezerwowanego zasobu", nie "koszt ruchu") — jedyny sposób by ich koszt spadł do zera to je usunąć (`terraform destroy`) i postawić od nowa następnym razem, co też jest dobrym ćwiczeniem powtarzalności Twojego Terraforma.

---

## Jak wracać do mnie w trakcie

Na każdym kroku możesz wkleić mi: błąd z terminala, output `terraform plan`/`apply`, logi z CloudWatch, albo po prostu powiedzieć na którym checkboxie utknąłeś. Nie musisz przechodzić faz w jednej sesji — ten plik jest zapisany w repo i możemy do niego wracać.
