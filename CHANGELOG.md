# Zmiany

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
