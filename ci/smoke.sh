#!/usr/bin/env sh
# End-to-end smoke test against a running stack (`docker compose up -d`).
#
#   ci/smoke.sh                       # http://localhost:7777
#   BASE_URL=http://host:7777 ci/smoke.sh
#
# The core checks are offline-safe: they exercise the app and Postgres only, so
# they pass on a VM with no route to TVMaze. The catalog checks need at least
# one series in the local read model (which means TVMaze was reachable once);
# with an empty read model they report SKIP instead of failing the build.
set -eu

BASE_URL=${BASE_URL:-http://localhost:7777}
VIEWER_ID=${VIEWER_ID:-11111111-1111-4111-8111-111111111111}
READY_TIMEOUT=${READY_TIMEOUT:-120}
MARKER="smoke-$(date +%s)"

BODY=$(mktemp)
trap 'rm -f "$BODY"' EXIT
failures=0

pass() { printf '  PASS  %s\n' "$1"; }
skip() { printf '  SKIP  %s\n' "$1"; }
fail() { printf '  FAIL  %s\n' "$1"; failures=$((failures + 1)); }

# request METHOD PATH [curl args...] -> prints the status code, body in $BODY
request() {
    method=$1 path=$2
    shift 2
    curl -sS --max-time 30 -o "$BODY" -w '%{http_code}' \
        -X "$method" -H "X-Viewer-Id: $VIEWER_ID" "$@" "$BASE_URL$path" 2>/dev/null || true
}

# expect LABEL STATUS PATTERN METHOD PATH [curl args...]  (PATTERN may be empty)
expect() {
    label=$1 expected=$2 pattern=$3
    shift 3
    status=$(request "$@")
    : "${status:=000}"
    if [ "$status" != "$expected" ]; then
        fail "$label — expected HTTP $expected, got $status"
        printf '        body: %s\n' "$(head -c 240 "$BODY")"
        return 0
    fi
    if [ -n "$pattern" ] && ! grep -q "$pattern" "$BODY"; then
        fail "$label — HTTP $expected but no match for '$pattern' in the body"
        printf '        body: %s\n' "$(head -c 240 "$BODY")"
        return 0
    fi
    pass "$label"
}

# first_json_number KEY -> the first "key":<number> value in $BODY
first_json_number() {
    grep -o "\"$1\":[0-9]*" "$BODY" | head -1 | cut -d: -f2
}

printf 'Smoke testing %s\n\n' "$BASE_URL"

printf 'Waiting for the stack to come up (up to %ss)\n' "$READY_TIMEOUT"
deadline=$(($(date +%s) + READY_TIMEOUT))
until [ "$(request GET /api/v1/ready)" = "200" ]; do
    if [ "$(date +%s)" -ge "$deadline" ]; then
        fail "/api/v1/ready never returned 200 within ${READY_TIMEOUT}s"
        exit 1
    fi
    sleep 2
done
pass "/api/v1/ready — app is up, Postgres is reachable, migrations ran"

printf '\nCore (no external dependency)\n'
expect "/api/v1/health"               200 '"status":"ok"'       GET  /api/v1/health
expect "frontend served at /"         200 'id="app"'            GET  /
expect "search (degrades, never 5xx)" 200 '"items"'             GET  "/api/v1/shows/search?q=house"
expect "popular shows"                200 '"items"'             GET  /api/v1/shows/popular
expect "popular reports a total"      200 '"total"'             GET  /api/v1/shows/popular
expect "popular offers a cursor"      200 '"next_cursor"'       GET  "/api/v1/shows/popular?limit=2"
expect "a bogus cursor is a 400"      400 '"code"'              GET  "/api/v1/shows/popular?cursor=nonsense"
expect "genre list"                   200 '"items"'             GET  /api/v1/shows/genres
expect "empty comment is a 400"       400 '"code":"invalid_request"' \
    POST /api/v1/comments -H 'Content-Type: application/json' -d '{"target_type":"show","target_id":1,"body":"   "}'
expect "unknown series is a 404"      404 '"code":"not_found"' \
    POST /api/v1/insights -H 'Content-Type: application/json' -d '{"target_type":"show","target_id":999999999}'
expect "post a comment"               201 "$MARKER" \
    POST /api/v1/comments -H 'Content-Type: application/json' \
    -d "{\"target_type\":\"show\",\"target_id\":1,\"body\":\"$MARKER\"}"
expect "the comment is readable back" 200 "$MARKER" \
    GET "/api/v1/comments?target_type=show&target_id=1"

printf '\nCatalog (needs a series in the read model)\n'
request GET /api/v1/shows/popular >/dev/null
show_id=$(first_json_number id)
if [ -z "${show_id:-}" ]; then
    request GET "/api/v1/shows/search?q=house" >/dev/null
    show_id=$(first_json_number id)
fi

request GET /api/v1/shows/genres >/dev/null
genre=$(sed -n 's/.*"items":\["\([^"]*\)".*/\1/p' "$BODY")

if [ -z "${genre:-}" ]; then
    skip "browse by genre — no genre in the read model"
else
    expect "browse by genre ($genre)" 200 '"items":\[{' \
        GET /api/v1/shows/popular --get --data-urlencode "genre=$genre"
fi

# Infinite scroll asks for page after page, so a second page must neither repeat
# nor skip a series. The client follows the cursor the previous page handed out.
request GET "/api/v1/shows/popular?limit=2" >/dev/null
page1=$(grep -o '"id":[0-9]*' "$BODY" | head -2 | tr '\n' ' ')
cursor=$(sed -n 's/.*"next_cursor":"\([^"]*\)".*/\1/p' "$BODY")
if [ -n "${cursor:-}" ]; then
    request GET /api/v1/shows/popular --get \
        --data-urlencode "limit=2" --data-urlencode "cursor=$cursor" >/dev/null
    page2=$(grep -o '"id":[0-9]*' "$BODY" | head -2 | tr '\n' ' ')
fi
if [ -z "$page1" ] || [ -z "${page2:-}" ]; then
    skip "paged listing — fewer than 4 series in the read model"
elif [ "$page1" = "$page2" ]; then
    fail "paged listing — the cursor returned the same series again ($page1)"
else
    overlap=""
    for id in $page1; do
        case " $page2 " in *" $id "*) overlap="$id";; esac
    done
    if [ -n "$overlap" ]; then
        fail "paged listing — $overlap appears on both pages"
    else
        pass "paged listing — consecutive pages do not overlap"
    fi
fi

if [ -z "${show_id:-}" ]; then
    skip "series details, watched marks and insight — the read model is empty (no route to TVMaze?)"
else
    expect "series details with seasons" 200 '"seasons"' GET "/api/v1/shows/$show_id"
    episode_id=$(grep -o '"episodes":\[{"id":[0-9]*' "$BODY" | head -1 | grep -o '[0-9]*$')
    expect "AI insight (fallback needs no key)" 200 '"text"' \
        POST /api/v1/insights -H 'Content-Type: application/json' \
        -d "{\"target_type\":\"show\",\"target_id\":$show_id}"
    if [ -z "${episode_id:-}" ]; then
        skip "watched marks — series $show_id has no episodes yet"
    else
        expect "mark an episode watched"   204 '' PUT "/api/v1/viewers/me/watched/$episode_id"
        expect "the mark is readable back" 200 "\"episode_ids\":\\[$episode_id" \
            GET "/api/v1/viewers/me/watched?show_id=$show_id"
        expect "unmark the episode"        204 '' DELETE "/api/v1/viewers/me/watched/$episode_id"
    fi
fi

printf '\n'
if [ "$failures" -eq 0 ]; then
    echo "Smoke test passed."
else
    echo "Smoke test FAILED — $failures check(s) failed."
fi
exit "$failures"
