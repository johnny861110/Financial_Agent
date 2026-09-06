#!/usr/bin/env bash
#
# Smoke-test the built image, not the source tree.
#
# Every pytest run imports from the working copy, so a dependency that is
# missing from the *image* is invisible to all of them. That is not
# hypothetical: the producer shipped an image without its pdf extra and the
# failure surfaced as silently empty extraction, and this repo shipped a
# compose default of LLM_TEMPERATURE=1.0 that no test could see because tests
# never read compose.
#
# So this asserts on a running container: the environment it actually got, the
# imports it can actually resolve, and one numeric and one narrative query
# answered end to end against the real producer.
#
# Usage:  ./scripts/container_smoke.sh [api_base_url]
set -euo pipefail

API="${1:-http://localhost:8000}"
CONTAINER="${SMOKE_CONTAINER:-financial-agent-api}"
failures=0

pass() { printf '  \033[32mok\033[0m   %s\n' "$1"; }
fail() { printf '  \033[31mFAIL\033[0m %s\n' "$1"; failures=$((failures + 1)); }

echo "Container smoke test: $CONTAINER via $API"
echo

# --- the container is actually up -------------------------------------------
echo "Runtime"
if ! docker inspect "$CONTAINER" >/dev/null 2>&1; then
  fail "$CONTAINER does not exist -- start it with: docker compose up -d"
  echo; echo "1 failure"; exit 1
fi
status=$(docker inspect -f '{{.State.Health.Status}}' "$CONTAINER" 2>/dev/null || echo unknown)
[ "$status" = "healthy" ] && pass "health status: healthy" || fail "health status: $status"

# --- the environment the container actually got ------------------------------
# Not what compose says: compose substitutes from .env, so the file and the
# process can disagree. Read it from inside.
temp=$(docker exec "$CONTAINER" printenv LLM_TEMPERATURE 2>/dev/null || echo unset)
if [ "$temp" = "0.0" ] || [ "$temp" = "0" ]; then
  pass "LLM_TEMPERATURE=$temp"
else
  fail "LLM_TEMPERATURE=$temp -- the composer restates exact figures; 1.0 flipped a digit"
fi

provider=$(docker exec "$CONTAINER" printenv DATA_PROVIDER 2>/dev/null || echo unset)
[ "$provider" = "financial_reports" ] \
  && pass "DATA_PROVIDER=$provider" \
  || fail "DATA_PROVIDER=$provider -- expected financial_reports"

# --- imports resolve inside the image ---------------------------------------
# The check that no pytest run can make, because pytest imports the source
# tree and this imports what was installed into the image.
echo
echo "Imports in the image"
for mod in langgraph langchain_openai httpx pydantic; do
  if docker exec "$CONTAINER" python -c "import $mod" 2>/dev/null; then
    pass "import $mod"
  else
    fail "import $mod -- missing from the image, invisible to the test suite"
  fi
done

# --- the seam ----------------------------------------------------------------
echo
echo "Live queries"
ready=$(curl -sf -m 15 "$API/health/ready" 2>/dev/null || echo '')
if echo "$ready" | grep -q '"status":"ready"'; then
  pass "readiness reports the provider is serving"
else
  fail "readiness: ${ready:-no response}"
fi

# A numeric question must be answered from the canonical fields. The figures
# are read from the API rather than hardcoded, so this does not rot when the
# corpus is re-ingested.
snapshot=$(curl -sf -m 30 "$API/api/financials/3661/2025Q1" 2>/dev/null || echo '{}')
revenue=$(printf '%s' "$snapshot" | python3 -c \
  'import sys,json; print(json.load(sys.stdin).get("income_statement",{}).get("net_revenue") or "")' 2>/dev/null || echo '')

if [ -z "$revenue" ]; then
  fail "no net_revenue for 3661/2025Q1 -- cannot check the numeric path"
else
  # Two acceptable renderings of the same figure: the raw thousands, and the
  # 萬/億/兆 form the answer composer now uses -- 10,484,855 千元 IS 104.85 億元.
  # Both are derived from the API's own value, so a wrong number still fails.
  formatted=$(printf '%s' "$revenue" | python3 -c \
    'import sys; print(f"{float(sys.stdin.read().strip()):,.0f}")')
  scaled=$(printf '%s' "$revenue" | python3 -c '
import sys
t = float(sys.stdin.read().strip())
for scale, suffix in ((1e9, "兆"), (1e5, "億"), (1e1, "萬")):
    if abs(t) >= scale:
        print(f"{t / scale:,.2f} {suffix}"); break
else:
    print(f"{t:,.0f} 千")')
  answer=$(curl -sf -m 180 -X POST "$API/api/agent/query" \
    -H 'Content-Type: application/json' \
    -d '{"query":"2025Q1 的營業收入是多少？","stock_code":"3661","period":"2025Q1","mode":"quick"}' \
    2>/dev/null | python3 -c \
    'import sys,json; d=json.load(sys.stdin); print(d.get("answer") or d.get("detail") or "")' \
    2>/dev/null || echo '')

  if [ -z "$answer" ]; then
    fail "numeric query returned nothing"
  elif printf '%s' "$answer" | grep -qF "$formatted"; then
    pass "numeric query reports $formatted, matching the snapshot"
  elif printf '%s' "$answer" | grep -qF "${scaled% *}"; then
    pass "numeric query reports $scaled元, matching the snapshot"
  else
    fail "numeric query reported neither $formatted nor $scaled元 -- got: $(printf '%s' "$answer" | head -c 160)"
  fi
fi

# A narrative question must reach the model with filing passages attached.
research=$(curl -sf -m 200 -X POST "$API/api/agent/research" \
  -H 'Content-Type: application/json' \
  -d '{"query":"公司的信用減損損失如何認定？","stock_code":"3661","period":"2025Q1"}' \
  2>/dev/null || echo '{}')
chunks=$(printf '%s' "$research" | python3 -c \
  'import sys,json; d=json.load(sys.stdin); print(sum(1 for e in (d.get("evidence") or []) if e.get("source_type")=="filing_text"))' \
  2>/dev/null || echo 0)

if [ "$chunks" -gt 0 ]; then
  pass "narrative query reached the model with $chunks filing passages"
else
  detail=$(printf '%s' "$research" | python3 -c \
    'import sys,json; print(json.load(sys.stdin).get("detail",""))' 2>/dev/null || echo '')
  fail "narrative query produced no filing passages${detail:+ -- $detail}"
fi

echo
if [ "$failures" -eq 0 ]; then
  echo "All checks passed."
else
  echo "$failures failure(s)."
fi
exit "$((failures > 0))"
