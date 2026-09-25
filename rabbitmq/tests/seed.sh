#!/bin/sh
# One-shot: prime the broker with the static queues, exchanges, and bindings the
# rabbitmq dashboards expect, so per-object metrics have subjects before the first
# scrape. Continuous traffic is the `load` service; this only establishes objects.
#
# Targets RabbitMQ 4.x, whose bundled rabbitmqadmin is v2 (flag syntax). The 3.x
# images ship the incompatible v1 tool, so this fixture pins a 4.x broker.
set -eu

HOST="${RABBITMQ_HOST:-rabbitmq-broker}"
A="rabbitmqadmin --non-interactive -H ${HOST} -u guest -p guest"

log() { echo "seed: $*"; }

log "declaring queues, exchanges, bindings on /"
for name in test1 test5 tralala; do
  $A declare queue --name "$name" --durable true
  $A declare exchange --name "$name" --type topic
  $A declare binding --source "$name" --destination-type queue --destination "$name" --routing-key "$name"
done

log "seed complete"
