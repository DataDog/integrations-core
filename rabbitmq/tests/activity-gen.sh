#!/bin/sh
# Periodic queue create/delete churn so the node-wide counters
# rabbitmq.queues.created.count / declared.count / deleted.count keep advancing.
# The heavy AMQP workload (channels, connections, publish/deliver/ack counters,
# queue depth) is the `load` (perf-test) service; this only drives queue churn,
# which perf-test's long-lived queues do not.
set -eu

HOST="${RABBITMQ_HOST:-rabbitmq-broker}"
A="rabbitmqadmin --non-interactive -H ${HOST} -u guest -p guest"

log() { echo "activity-gen: $*"; }

# Opt out for a quiescent full-coverage env: the container stays up (so
# dependents keep running) but generates no churn.
if [ "${ACTIVITY_GEN:-1}" = "0" ]; then
  log "disabled via ACTIVITY_GEN=0; idling"
  exec sleep infinity
fi

i=0
while :; do
  i=$((i + 1))
  q="churn_$((i % 20))"
  $A declare queue --name "$q"               >/dev/null 2>&1 || true
  $A delete queue --name "$q" --idempotently >/dev/null 2>&1 || true
  [ $((i % 20)) -eq 0 ] && log "iteration $i"
  sleep 3
done
