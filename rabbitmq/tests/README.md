# rabbitmq test fixtures

The pytest suite plus the Compose environments used by the tests and by the
evalya fixtures in `evalya.yaml`.

## Compose environments

| File | What it is |
|---|---|
| `compose/docker-compose.yaml` | Single management-enabled broker (the pytest default). |
| `compose/full-coverage.compose` | Full metric-coverage environment (see below). |

Two are published as reusable evalya fixtures: `rabbitmq-standalone` (the plain
broker) and `rabbitmq-full` (the full-coverage environment). Both present the
management HTTP API on `:15672` with the `guest`/`guest` credentials.

## The full-coverage fixture

`rabbitmq-full` makes a single fixture emit non-trivial values for the entire
metric surface the rabbitmq check and the OTel `rabbitmqreceiver` collect from a
real broker. An idle broker reports zero for most rate/counter metrics, so two
workloads run against it. Four services:

- **rabbitmq** — real `rabbitmq:<ver>-management` broker, the fixture entrypoint
  (published as `rabbitmq-full`). A small `rabbitmq.conf` lifts the loopback-only
  restriction on `guest` so the workload containers and the scrapers can connect
  over the Compose network.
- **perf-test** — the official RabbitMQ load tool (`pivotalrabbitmq/perf-test`),
  running continuous publish/consume/ack with manual acks, so
  `message.published` / `message.acknowledged` / `message.delivered`,
  `consumer.count` and the `queue.*` rate/count metrics keep moving.
- **activity-gen** — a `pika` sidecar (`activity-gen.py`) for what perf-test does
  not exercise: durable queues + persistent messages (`node.msg_store_*`,
  `node.queue_index_*`), queue/exchange declare+delete churn
  (`node.queue_created/declared/deleted`), connection/channel open+close churn
  (`node.connection_*`, `node.channel_*`), unroutable publishes
  (`message.dropped`), and messages left both ready and unacknowledged
  (`message.current` with the `ready` / `unacknowledged` states).

The `node.*` and `erlang.*` gauges come naturally from the running broker.

No host port is published, to avoid clashing with a local broker; reach it over
the Compose network via the `DB_HOST` label, or add `--publish 15672:15672` to
inspect by hand. Set `ACTIVITY_GEN=0` (host env) for a quiescent `rabbitmq-full`:
the sidecar container stays up but generates no traffic.

## Enabling the OTel node.* metrics

> **Important:** the OTel `rabbitmqreceiver` ships with **every `rabbitmq.node.*`
> metric disabled by default** — only the six message/consumer metrics
> (`rabbitmq.message.*`, `rabbitmq.consumer.count`) are on out of the box. This
> fixture makes the broker *emit* the underlying data, but a collector scraping
> `rabbitmq-full` will not report the `node.*` series (roughly half of the
> semantic-core mappings) unless they are explicitly enabled in the receiver
> config:

```yaml
receivers:
  rabbitmq:
    endpoint: http://<DB_HOST>:15672
    username: guest
    password: guest
    collection_interval: 10s
    metrics:
      rabbitmq.node.disk_free: {enabled: true}
      rabbitmq.node.mem_used: {enabled: true}
      rabbitmq.node.fd_used: {enabled: true}
      # ... enable the remaining rabbitmq.node.* metrics the mappings need
```
