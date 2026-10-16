#!/bin/sh
# Drives couch-full so the couch check reports the request, method, status-code,
# read/write, bulk and auth-cache metrics of both dashboards with non-zero values
# (an idle CouchDB leaves them at 0, and 1.x omits a counter until it first
# moves). Runs the same workload against the 3.x server (DB_HOST/DB_PORT, as
# DB_USERNAME) and the 1.x server (DB_V1_HOST/DB_V1_PORT, admin party).
set -eu

V3="http://${DB_HOST}:${DB_PORT:-5984}"
V1="http://${DB_V1_HOST}:${DB_V1_PORT:-5984}"
ADMIN="${DB_USERNAME}:${DB_PASSWORD}"
# Non-admin _users account created by the seed; authenticating as it goes
# through the auth cache (server admins bypass it).
READER="ddreader:ddreader"
DURATION="${ACTIVITY_DURATION:-0}"   # 0 = run forever
J='Content-Type: application/json'

log() { echo "activity-gen: $*"; }

# Opt out of the workload for a quiescent couch-full: ACTIVITY_GEN=0 keeps the
# container running (so dependents still start) but generates no traffic.
if [ "${ACTIVITY_GEN:-1}" = "0" ]; then
  log "disabled via ACTIVITY_GEN=0; idling"
  exec sleep infinity
fi

# body <auth or empty> <curl args...>: print the response body, never fail.
body() {
  if [ -n "$1" ]; then auth=$1; shift; curl -s -u "$auth" "$@" || true
  else shift; curl -s "$@" || true; fi
}

# drive <base url> <admin auth, empty for admin party> <iteration>
drive() {
  b=$1 a=$2 i=$3
  c() { body "$a" -o /dev/null "$@"; }

  # GET 200 + database_reads; 404 for a document that is not there yet.
  c "$b/"
  c "$b/kennel/seed-$(( i % 50 + 1 ))"
  c "$b/activity/doc-$i"
  # PUT 201 + database_writes, then a 409 conflict re-PUT without the rev.
  rev=$(body "$a" -X PUT -H "$J" "$b/activity/doc-$i" -d "{\"data\":$i}" \
        | sed -n 's/.*"rev":"\([^"]*\)".*/\1/p')
  c "$b/activity/doc-$i"
  c -X PUT -H "$J" "$b/activity/doc-$i" -d "{\"data\":$i}"
  # POST 201 and a _bulk_docs request (httpd.bulk_requests).
  c -X POST -H "$J" "$b/activity" -d "{\"data\":$i}"
  c -X POST -H "$J" "$b/activity/_bulk_docs" -d "{\"docs\":[{\"n\":1},{\"n\":2},{\"n\":3}]}"
  # DELETE 200.
  [ -n "$rev" ] && c -X DELETE "$b/activity/doc-$i?rev=$rev"
  # Error paths: 400 bad JSON, 403 validate_doc_update, 405 bad method,
  # 412 database already exists.
  c -X POST -H "$J" "$b/activity" -d "notjson"
  c -X PUT -H "$J" "$b/kennel/forbidden-$i" -d '{"forbidden":true}'
  c -X DELETE "$b/_all_dbs"
  c -X PUT "$b/kennel"
  # View read.
  c "$b/kennel/_design/dummy/_view/all?limit=5"

  # Auth: 401 and an auth cache miss for an unknown user, then repeated
  # requests as the _users account that hit the auth cache. 3.x locks a user
  # out (403) after a few failed logins from one client, so each failed login
  # uses a fresh name and never touches the admin account.
  h=${b#http://}
  curl -s -o /dev/null -u "ghost-$i:x" "http://$h/" || true
  for _ in 1 2 3; do curl -s -o /dev/null -u "$READER" "http://$h/_session" || true; done

  # Keep the activity database bounded on a long run: recreating it also
  # exercises DELETE on a database.
  if [ $(( i % 1000 )) -eq 0 ]; then
    c -X DELETE "$b/activity"
    c -X PUT "$b/activity"
  fi
}

end=0
[ "$DURATION" -gt 0 ] && end=$(( $(date +%s) + DURATION ))
i=0

log "driving $V3 and $V1"
while :; do
  i=$(( i + 1 ))
  drive "$V3" "$ADMIN" "$i"
  drive "$V1" "" "$i"

  if [ $(( i % 30 )) -eq 0 ]; then
    log "iteration $i:" \
        "3.x requests=$(curl -s -u "$ADMIN" "$V3/_node/_local/_stats/couchdb/httpd/requests" | sed -n 's/.*"value":\([0-9]*\).*/\1/p')" \
        "1.x requests=$(curl -s "$V1/_stats/httpd/requests" | sed -n 's/.*"current":\([0-9.]*\).*/\1/p')"
  fi

  [ "$end" -gt 0 ] && [ "$(date +%s)" -ge "$end" ] && break
  sleep 1
done

log "PASS: activity workload complete after $i iterations"
