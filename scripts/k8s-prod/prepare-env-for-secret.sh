#!/usr/bin/env bash
# Przygotowuje plik env pod kubectl create secret --from-env-file
# (kubectl nie akceptuje zduplikowanych kluczy — bierze ostatnia wartosc)
set -euo pipefail

prepare_env_for_k8s_secret() {
  local src="$1"
  local dst="$2"

  awk '
    BEGIN { dup = 0 }
    /^[[:space:]]*#/ { next }
    /^[[:space:]]*$/ { next }
    {
      line = $0
      sub(/^export[[:space:]]+/, "", line)
      eq = index(line, "=")
      if (eq == 0) next
      key = substr(line, 1, eq - 1)
      val = substr(line, eq + 1)
      if (key in env) {
        if (env[key] != val) {
          print "  - " key > "/dev/stderr"
          dup = 1
        }
      }
      env[key] = val
    }
    END {
      if (dup) {
        print "UWAGA: zduplikowane klucze w pliku env (uzyto ostatniej wartosci):" > "/dev/stderr"
      }
      for (k in env) {
        print k "=" env[k]
      }
    }
  ' "$src" > "$dst"
}

# Zamienia hosty docker-compose (postgres) na IP bramki hosta dla podow k3s
remap_k8s_db_hosts() {
  local file="$1"
  local gateway="${K8S_HOST_GATEWAY:-172.17.0.1}"
  local tmp
  tmp="$(mktemp)"

  awk -v gw="$gateway" '
    /^[A-Za-z_][A-Za-z0-9_]*=/ {
      eq = index($0, "=")
      key = substr($0, 1, eq - 1)
      val = substr($0, eq + 1)
      if (key ~ /_DB_HOST$/ && (val == "postgres" || val == "nc-postgres-1")) {
        print key "=" gw
        next
      }
    }
    { print }
  ' "$file" > "$tmp"
  mv "$tmp" "$file"
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  if [[ $# -ne 2 ]]; then
    echo "Uzycie: $0 <src.env> <dst.env>"
    exit 1
  fi
  prepare_env_for_k8s_secret "$1" "$2"
fi
