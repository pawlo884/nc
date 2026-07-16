#!/usr/bin/env bash
# Stres + failover na nc-prod (uruchamiaj na VPS).
# Uzycie: ./scripts/k8s-prod/stress-test.sh
set -euo pipefail

K="sudo k3s kubectl"
NS=nc-prod
HOST_HDR="Host: nc.sowa.ch"
URL="http://127.0.0.1:30080/health/"
STRESS_N="${STRESS_N:-200}"
STRESS_PARALLEL="${STRESS_PARALLEL:-20}"

echo "=== 1. Stan przed ==="
$K get pods -l app=nc-web -n "$NS" -o wide
echo ""

echo "=== 2. Load balancing (10x health) ==="
for i in $(seq 1 10); do
  curl -sf -H "$HOST_HDR" "$URL" || echo "FAIL"
  echo
done
echo ""

echo "=== 3. Failover: usuwam 1 pod, health co 0.4s ==="
POD=$($K get pods -l app=nc-web -n "$NS" -o jsonpath='{.items[0].metadata.name}')
echo "Usuwam: $POD"
$K delete pod "$POD" -n "$NS" --wait=false

ok=0
fail=0
for i in $(seq 1 20); do
  code=$(curl -s -o /tmp/nc-health.txt -w '%{http_code}' -H "$HOST_HDR" --max-time 3 "$URL" || echo "000")
  body=$(cat /tmp/nc-health.txt 2>/dev/null || true)
  if [ "$code" = "200" ]; then
    ok=$((ok + 1))
    echo "$i HTTP=$code body=$body"
  else
    fail=$((fail + 1))
    echo "$i HTTP=$code body=$body  <-- FAIL"
  fi
  sleep 0.4
done
echo "Failover: OK=$ok FAIL=$fail"
echo ""

echo "=== 4. Czekam az Deployment wraca do 3/3 ==="
$K rollout status deployment/nc-web -n "$NS" --timeout=120s
$K get pods -l app=nc-web -n "$NS"
echo ""

echo "=== 5. Stres: $STRESS_N requestow, rownolegle $STRESS_PARALLEL ==="
tmp=$(mktemp -d)
seq 1 "$STRESS_N" | xargs -P "$STRESS_PARALLEL" -I{} bash -c \
  "curl -s -o /dev/null -w '%{http_code}\n' -H '$HOST_HDR' --max-time 5 '$URL' >> '$tmp/codes.txt' || echo 000 >> '$tmp/codes.txt'"

echo "Kody HTTP:"
sort "$tmp/codes.txt" | uniq -c | sort -rn
total=$(wc -l < "$tmp/codes.txt")
ok_n=$(grep -c '^200$' "$tmp/codes.txt" || true)
fail_n=$((total - ok_n))
echo "Suma: total=$total OK=$ok_n FAIL=$fail_n"
rm -rf "$tmp"
echo ""

echo "=== 6. Restarty / eventy po stresie ==="
$K get pods -l app=nc-web -n "$NS"
echo ""
$K get events -n "$NS" --field-selector involvedObject.kind=Pod --sort-by='.lastTimestamp' | tail -20
echo ""
echo "Gotowe."
