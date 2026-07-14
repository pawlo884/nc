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

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  if [[ $# -ne 2 ]]; then
    echo "Uzycie: $0 <src.env> <dst.env>"
    exit 1
  fi
  prepare_env_for_k8s_secret "$1" "$2"
fi
