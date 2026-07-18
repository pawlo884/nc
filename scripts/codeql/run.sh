#!/usr/bin/env bash
# CodeQL w kontenerze: baza + analiza → .codeql/*.sarif
set -euo pipefail

RESULTS="${CODEQL_RESULTS_DIR:-/opt/results}"
WORKSPACE="${CODEQL_WORKSPACE:-/workspace}"
LANGS="${CODEQL_LANGS:-python}"
SUITE_SUFFIX="${CODEQL_SUITE:-security-and-quality}"

mkdir -p "$RESULTS"

run_one() {
  local lang="$1"
  local source_root="$2"
  local db="$RESULTS/db-${lang}"
  local out="$RESULTS/${lang}.sarif"

  if [[ ! -d "$source_root" ]]; then
    echo "SKIP ${lang}: brak katalogu ${source_root}"
    return 0
  fi

  echo "==> CodeQL database create (${lang}) ← ${source_root}"
  rm -rf "$db"
  codeql database create "$db" \
    --language="$lang" \
    --source-root="$source_root" \
    --overwrite

  echo "==> CodeQL database analyze (${lang}) → ${out}"
  # Precompiled suites w obrazie MCR; fallback z --download
  if ! codeql database analyze "$db" \
      --format=sarif-latest \
      --output="$out" \
      "${lang}-${SUITE_SUFFIX}.qls"; then
    echo "Suite lokalna niedostępna — pobieram packi (--download)…"
    codeql database analyze "$db" \
      --format=sarif-latest \
      --output="$out" \
      --download
  fi

  echo "OK ${lang}: ${out}"
}

IFS=',' read -ra LANG_ARR <<< "$LANGS"
for lang in "${LANG_ARR[@]}"; do
  lang="$(echo "$lang" | tr -d '[:space:]')"
  case "$lang" in
    python)
      run_one python "${WORKSPACE}/src"
      ;;
    javascript|javascript-typescript|js)
      # extractor JS obejmuje też TypeScript
      run_one javascript "${WORKSPACE}/frontend/mpd"
      ;;
    *)
      echo "Nieznany język: ${lang} (obsługiwane: python, javascript)"
      exit 1
      ;;
  esac
done

echo "==> Gotowe. Wyniki w ${RESULTS} (*.sarif)"
ls -la "$RESULTS"/*.sarif 2>/dev/null || true
