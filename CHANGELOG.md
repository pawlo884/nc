# Zmiany

## <small>1.11.2 (2026-04-26)</small>

* fix(matterhorn1/admin): dodaj miniatury na liście produktów ([e05a482](https://github.com/pawlo884/nc/commit/e05a482))

## <small>1.11.1 (2026-04-26)</small>

* fix(matterhorn1): retry zapisu tej samej strony ITEMS przy błędzie DB ([4496bb2](https://github.com/pawlo884/nc/commit/4496bb2))
* fix(MPD): napraw modele, widoki, serializery i migrację ([17ed8ef](https://github.com/pawlo884/nc/commit/17ed8ef))
* Automatyzacja dodawania produktów Tabu→MPD (web agent) ([5c89863](https://github.com/pawlo884/nc/commit/5c89863))
* Bezpieczniejszy fallback REDIS_PASSWORD w cache (CHANGE_ME_IN_ENV) ([c69ad18](https://github.com/pawlo884/nc/commit/c69ad18))
* CI/Docker: używaj requirements.ci.txt i napraw encoding ([b6825ed](https://github.com/pawlo884/nc/commit/b6825ed))
* Collection, seria z marką, Saga Tabu, czyszczenie mapowania przy usunięciu MPD ([81471f8](https://github.com/pawlo884/nc/commit/81471f8))
* Dodaj serwis code-reviewer z Ruff w docker-compose.dev ([12cf682](https://github.com/pawlo884/nc/commit/12cf682))
* Dopasuj wersje langchain-core do langchain-openai ([f6532e7](https://github.com/pawlo884/nc/commit/f6532e7))
* fix saga matterhorn producer_code i kompensacja mappingu ([e6ab028](https://github.com/pawlo884/nc/commit/e6ab028))
* Kod producenta w product_variants_sources.producer_code + fix migracji 0005 ([9c246fa](https://github.com/pawlo884/nc/commit/9c246fa))
* Linkowanie wariantów po EAN: adaptery źródeł, Celery task, dopinanie w create_mpd_variants ([290569c](https://github.com/pawlo884/nc/commit/290569c))
* Linkowanie wariantów po EAN: sygnał na Products, task po commicie; routing MPD w settings ([0173124](https://github.com/pawlo884/nc/commit/0173124))
* matterhorn1/admin: usuń iai_product_id z insertów product_variants ([57580e4](https://github.com/pawlo884/nc/commit/57580e4))
* Merge branch 'main' into feature/automation-add-products-web-agent ([e197e16](https://github.com/pawlo884/nc/commit/e197e16))
* Merge pull request #27 from pawlo884/feature/mpd-models ([3acda68](https://github.com/pawlo884/nc/commit/3acda68)), closes [#27](https://github.com/pawlo884/nc/issues/27)
* Merge pull request #28 from pawlo884/feature/tabu-integrator ([7861f32](https://github.com/pawlo884/nc/commit/7861f32)), closes [#28](https://github.com/pawlo884/nc/issues/28)
* Merge pull request #29 from pawlo884/feature/variant-linking-by-ean ([51ded62](https://github.com/pawlo884/nc/commit/51ded62)), closes [#29](https://github.com/pawlo884/nc/issues/29)
* Merge pull request #32 from pawlo884/feature/automation-add-products-web-agent ([e7245ea](https://github.com/pawlo884/nc/commit/e7245ea)), closes [#32](https://github.com/pawlo884/nc/issues/32)
* Merge pull request #33 from pawlo884/tabu-mapping ([26ad86b](https://github.com/pawlo884/nc/commit/26ad86b)), closes [#33](https://github.com/pawlo884/nc/issues/33)
* Merge pull request #34 from pawlo884/feature/collection-and-series-brand ([3185cdc](https://github.com/pawlo884/nc/commit/3185cdc)), closes [#34](https://github.com/pawlo884/nc/issues/34)
* Merge pull request #35 from pawlo884/feature/api-mpd-rest-v2 ([f411d61](https://github.com/pawlo884/nc/commit/f411d61)), closes [#35](https://github.com/pawlo884/nc/issues/35)
* Merge pull request #36 from pawlo884/docs/project-readme-v2 ([36d3b33](https://github.com/pawlo884/nc/commit/36d3b33)), closes [#36](https://github.com/pawlo884/nc/issues/36)
* Merge pull request #37 from pawlo884/security/redis-password-fallback ([ca637eb](https://github.com/pawlo884/nc/commit/ca637eb)), closes [#37](https://github.com/pawlo884/nc/issues/37)
* Merge pull request #38 from pawlo884/feature/mpd-products-api ([87ecd62](https://github.com/pawlo884/nc/commit/87ecd62)), closes [#38](https://github.com/pawlo884/nc/issues/38)
* Merge pull request #39 from pawlo884/chore/code-reviewer-ruff ([5637d04](https://github.com/pawlo884/nc/commit/5637d04)), closes [#39](https://github.com/pawlo884/nc/issues/39)
* Merge pull request #40 from pawlo884/chore/fix-ruff-lints ([5a88cae](https://github.com/pawlo884/nc/commit/5a88cae)), closes [#40](https://github.com/pawlo884/nc/issues/40)
* Merge pull request #42 from pawlo884/feature/automation-add-products-web-agent ([e81aa17](https://github.com/pawlo884/nc/commit/e81aa17)), closes [#42](https://github.com/pawlo884/nc/issues/42)
* MPD admin delete async + przyciski na górze ([4d85a90](https://github.com/pawlo884/nc/commit/4d85a90))
* MPD API: lista produktów i drobne ulepszenia widoku ([470d594](https://github.com/pawlo884/nc/commit/470d594))
* MPD/views: usuń użycie pola iai_product_id ([e76b133](https://github.com/pawlo884/nc/commit/e76b133))
* Napraw kodowanie requirements.txt (UTF-8) ([1dc7641](https://github.com/pawlo884/nc/commit/1dc7641))
* Popraw wyszukiwanie sugestii po kodzie producenta ([dfe426e](https://github.com/pawlo884/nc/commit/dfe426e))
* producer_code tylko w product_variants_sources, linking, admin, nc→core ([192084b](https://github.com/pawlo884/nc/commit/192084b))
* Przepisz src/requirements.txt jako czysty UTF-8 ([bc83882](https://github.com/pawlo884/nc/commit/bc83882))
* Przyspiesz import ITEMS przez prefetch kolejnej strony API. ([347f1f2](https://github.com/pawlo884/nc/commit/347f1f2))
* Reapply "Dodaj REST API MPD i testy API" ([b0231d3](https://github.com/pawlo884/nc/commit/b0231d3))
* Rozszerz README o opis aplikacji i struktury ([4af7c56](https://github.com/pawlo884/nc/commit/4af7c56))
* Ścieżka XML: xml/matterhorn → xml (piętro wyżej) ([11c20a4](https://github.com/pawlo884/nc/commit/11c20a4))
* Tabu integrator: podzielony widok produktu + formularz MPD jak Matterhorn ([78d33ab](https://github.com/pawlo884/nc/commit/78d33ab))
* Tabu→MPD: cena netto w StockAndPrices, BigAutoField dla id, sygnał przy usuwaniu ([0e3d481](https://github.com/pawlo884/nc/commit/0e3d481))
* Tabu→MPD: zapisywanie zdjęć (upload do bucketa + ProductImage) ([664f4b3](https://github.com/pawlo884/nc/commit/664f4b3))
* Testy jednostkowe i integracyjne, sygnały MPD z aliasami dev, raw SQL analiza ([7f7f406](https://github.com/pawlo884/nc/commit/7f7f406))
* Ustaw poprawne kodowanie UTF-16 dla src/requirements.txt ([ce577cb](https://github.com/pawlo884/nc/commit/ce577cb))
* Usuń IAI counter i pola iai_product_id z MPD/tabu/matterhorn1 ([0382195](https://github.com/pawlo884/nc/commit/0382195))
* Usuń pola iai_product_id z MPD i dostosuj sagę ([6fe6aab](https://github.com/pawlo884/nc/commit/6fe6aab))
* Wzorzec mapowania produktu hurtownia→MPD (wyznacznik dla kolejnych hurtowni) ([bdc4eef](https://github.com/pawlo884/nc/commit/bdc4eef))
* test(MPD): dodaj testy rozszerzone i napraw migrację 0014 ([af5b403](https://github.com/pawlo884/nc/commit/af5b403))
* tabu: usuń przekazywanie iai_product_id ([df95713](https://github.com/pawlo884/nc/commit/df95713))
* MPD: 0010_and_more - RunSQL IF EXISTS (komentarze) ([96c73ef](https://github.com/pawlo884/nc/commit/96c73ef))
* MPD: grupowanie wariantów po EAN zamiast producer_code, wyrównanie pionowe do środka ([926e9f8](https://github.com/pawlo884/nc/commit/926e9f8))
* MPD: merge migracji 0010, fix 0010_and_more - RunSQL IF EXISTS ([01e1e16](https://github.com/pawlo884/nc/commit/01e1e16))
* MPD: model Seasons (sezon) + pole season w Products ([ee825b1](https://github.com/pawlo884/nc/commit/ee825b1))
* chore: fix ruff lints in core, MPD and matterhorn1 ([b4bc964](https://github.com/pawlo884/nc/commit/b4bc964))
* CI: instaluj zaleznosci z przekonwertowanego requirements (UTF-8) ([6795591](https://github.com/pawlo884/nc/commit/6795591))
* Tabu: mapped_variant_uid + wzorzec adaptera hurtowni w dokumentacji ([621f199](https://github.com/pawlo884/nc/commit/621f199))
* Tabu: polecenie find_common_eans - EANy w obu bazach (Tabu i Matterhorn) ([1c38a8f](https://github.com/pawlo884/nc/commit/1c38a8f))
* Tabu: Przypisz jak Matterhorn1 – warianty, zdjęcia, kolor z formularza ([259ff7f](https://github.com/pawlo884/nc/commit/259ff7f))
* Tabu: ustawianie mapped_variant_uid przy tworzeniu produktu MPD z Tabu (mpd_create) ([b12027b](https://github.com/pawlo884/nc/commit/b12027b))
* linkowanie: uzupełnianie mapped_variant_uid w productvariant (Matterhorn) ([66138d5](https://github.com/pawlo884/nc/commit/66138d5))
* Linking: EAN + pozostałe warianty, adaptery uniwersalne, variant_uid/other Tabu ([7099505](https://github.com/pawlo884/nc/commit/7099505))
* docs: aktualizacja README, agents.md, IDOSELL_API; usunięcie starych plików testowych; .python-versi ([c28e6f8](https://github.com/pawlo884/nc/commit/c28e6f8))

## 1.11.0 (2026-02-14)

* Merge main into feature/tabu - resolve conflicts ([c51f403](https://github.com/pawlo884/nc/commit/c51f403))
* Merge pull request #26 from pawlo884/feature/tabu ([df5d34a](https://github.com/pawlo884/nc/commit/df5d34a)), closes [#26](https://github.com/pawlo884/nc/issues/26)
* Tabu: import, sync, periodic tasks, Docker restart resilience ([6e540ba](https://github.com/pawlo884/nc/commit/6e540ba))
* feat(tabu): add new tabu application with models, admin, serializers and database routing ([d8ef8af](https://github.com/pawlo884/nc/commit/d8ef8af))
* feat(tabu): import API, sync task, komendy, docs ([c6e7da7](https://github.com/pawlo884/nc/commit/c6e7da7))
* fix: BASE_DIR dla Docker - poprawne ścieżki plików statycznych ([f1fab87](https://github.com/pawlo884/nc/commit/f1fab87))
* docs(tabu): baza zzz_tabu, migracje i reguła w django.mdc ([b992a63](https://github.com/pawlo884/nc/commit/b992a63))
* tabu: komenda test_tabu_connection, ładowanie .env z BASE_DIR, modele i migracje ([8749ebd](https://github.com/pawlo884/nc/commit/8749ebd))
* style(settings): fix code formatting in base.py ([98d5501](https://github.com/pawlo884/nc/commit/98d5501))

## <small>1.10.6 (2026-02-03)</small>

* fix(celery): depends_on bez condition: service_healthy – nie blokują w created; doc 502 + cert SSL ([6d2a581](https://github.com/pawlo884/nc/commit/6d2a581))

## <small>1.10.5 (2026-02-03)</small>

* fix(nginx-router): depends_on tylko redis – nie wymaga obu web (po deployu jeden stopped) ([2bd34eb](https://github.com/pawlo884/nc/commit/2bd34eb))

## <small>1.10.4 (2026-02-03)</small>

* fix(502): BotBlocker pomija też requesty z X-Forwarded-For (proxy chain) ([4ebdfb1](https://github.com/pawlo884/nc/commit/4ebdfb1))

## <small>1.10.3 (2026-02-03)</small>

* fix(502): BotBlocker pomija requesty z proxy (172.x), ALLOWED_HOSTS web-blue/green, doc TROUBLESHOOT ([81bf102](https://github.com/pawlo884/nc/commit/81bf102))
* chore(deploy): COMPOSE_PROJECT_NAME=docker-compose + migracja Redis ze stacku nc ([fcedf4c](https://github.com/pawlo884/nc/commit/fcedf4c))

## <small>1.10.2 (2026-02-03)</small>

* fix: dodanie nc_dbnet do web-blue i web-green dla połączenia z postgres ([ccd961c](https://github.com/pawlo884/nc/commit/ccd961c))

## <small>1.10.1 (2026-02-03)</small>

* fix(blue-green): usunięcie depends_on postgres (no such service przy profile shared) ([c5dc02b](https://github.com/pawlo884/nc/commit/c5dc02b))

## 1.10.0 (2026-02-03)

* feat(blue-green): wszystko w jednym stacku oprócz postgresów (redis w głównym stacku) ([fdae767](https://github.com/pawlo884/nc/commit/fdae767))

## <small>1.9.16 (2026-02-03)</small>

* fix(blue-green): profile shared dla postgres/redis, --no-deps przy nginx-router, domyślne FLOWER ([47f7243](https://github.com/pawlo884/nc/commit/47f7243))
* Naprawa konfiguracji blue-green deployment i Celery ([585c17a](https://github.com/pawlo884/nc/commit/585c17a))

## <small>1.9.15 (2026-01-19)</small>

* fix: naprawa automatycznego restartu SSH tunnel w postgres-ssh-tunnel ([3b5e0d8](https://github.com/pawlo884/nc/commit/3b5e0d8))
* Formatowanie kodu - poprawa spacji w komentarzach w settings/base.py ([fc1b26b](https://github.com/pawlo884/nc/commit/fc1b26b))
* Naprawa konfiguracji nginx dla plików statycznych - dodano nagłówki CORS i poprawiono typy MIME ([0f84c51](https://github.com/pawlo884/nc/commit/0f84c51))
* Naprawa plików statycznych - konfiguracja dla Cloudflare i NPM ([252e3e3](https://github.com/pawlo884/nc/commit/252e3e3))

## <small>1.9.14 (2026-01-12)</small>

* fix(deploy): zmieniono nazwy upstream w nginx z web-blue/web-green na nc-web-blue/nc-web-green ([a84fa65](https://github.com/pawlo884/nc/commit/a84fa65))

## <small>1.9.13 (2026-01-12)</small>

* fix(deploy): dodano brakujący plik nginx-blue-green.conf i naprawiono sieć Docker ([62765bb](https://github.com/pawlo884/nc/commit/62765bb))

## <small>1.9.12 (2026-01-12)</small>

* fix: zmiana health check z /admin/ na /health/ również w funkcji status() ([245d58c](https://github.com/pawlo884/nc/commit/245d58c))
* fix: zmiana health check z /admin/ na /health/ w blue-green deploy ([1f81821](https://github.com/pawlo884/nc/commit/1f81821))

## <small>1.9.11 (2026-01-12)</small>

* fix: poprawka ścieżki volume mount w docker-compose.blue-green.yml ([dbdab69](https://github.com/pawlo884/nc/commit/dbdab69))
* fix: poprawka wszystkich ścieżek volume mount w docker-compose.blue-green.yml ([01e9aae](https://github.com/pawlo884/nc/commit/01e9aae))

## <small>1.9.10 (2026-01-12)</small>

* fix: użycie docker rm -f zamiast docker-compose rm dla usuwania kontenera ([47c3f33](https://github.com/pawlo884/nc/commit/47c3f33))

## <small>1.9.9 (2026-01-11)</small>

* fix: usuwanie starego kontenera przed uruchomieniem nowego w blue-green deploy ([9a0f9bc](https://github.com/pawlo884/nc/commit/9a0f9bc))

## <small>1.9.8 (2026-01-11)</small>

* fix: dodanie --no-deps również w funkcji rollback ([d692ac4](https://github.com/pawlo884/nc/commit/d692ac4))

## <small>1.9.7 (2026-01-11)</small>

* fix: dodanie --no-deps przy uruchamianiu web-${TARGET} w blue-green deploy ([aa54078](https://github.com/pawlo884/nc/commit/aa54078))

## <small>1.9.6 (2026-01-11)</small>

* fix: usunięcie COPY tabu/ z Dockerfile.prod ([0a51763](https://github.com/pawlo884/nc/commit/0a51763))

## <small>1.9.5 (2026-01-11)</small>

* fix: usunięcie nieprawidłowej składni shell z komend COPY w Dockerfile ([5aa8d15](https://github.com/pawlo884/nc/commit/5aa8d15))

## <small>1.9.4 (2026-01-11)</small>

* fix: poprawa build context w docker-compose.blue-green.yml ([6e69fc3](https://github.com/pawlo884/nc/commit/6e69fc3))

## <small>1.9.3 (2026-01-11)</small>

* fix: poprawa ścieżek env_file w docker-compose.blue-green.yml ([c4a506e](https://github.com/pawlo884/nc/commit/c4a506e))

## <small>1.9.2 (2026-01-11)</small>

* Merge pull request #25 from pawlo884/refactor/project-structure ([d163eb6](https://github.com/pawlo884/nc/commit/d163eb6)), closes [#25](https://github.com/pawlo884/nc/issues/25)
* fix: aktualizacja ścieżek w GitHub Actions workflows ([77e4328](https://github.com/pawlo884/nc/commit/77e4328))
* fix: aktualizacja wersji Pythona w GitHub Actions do 3.13 ([5f8211d](https://github.com/pawlo884/nc/commit/5f8211d))
* fix: naprawa błędów i aktualizacja konfiguracji MinIO ([bc2c207](https://github.com/pawlo884/nc/commit/bc2c207))
* fix: naprawa konfiguracji docker-compose i SSH tunnel ([31c602c](https://github.com/pawlo884/nc/commit/31c602c))
* fix: poprawa obsługi braku plików w Prettier workflow ([7d1e289](https://github.com/pawlo884/nc/commit/7d1e289))
* refactor: reorganize project structure - move docker and misc folders ([a55e3dc](https://github.com/pawlo884/nc/commit/a55e3dc))
* docs: dodaj dokumentację reorganizacji struktury projektu ([eb70aac](https://github.com/pawlo884/nc/commit/eb70aac))
