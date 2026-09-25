# rabbitmq test fixtures

The pytest suite plus the Compose environments used by the tests and by the evalya
fixture in `evalya.yaml`.

## Compose environments

| File | What it is |
|---|---|
| `compose/docker-compose.yaml` | Single `-management` broker used by the pytest suite. |
| `compose/full-coverage.compose` | Full metric-coverage environment (see below). |

`full-coverage.compose` is published as the reusable evalya fixture `rabbitmq-full`.

## The full-coverage fixture

`rabbitmq-full` drives the rabbitmq check to emit the metrics users are shown: everything
referenced by the OOTB dashboards (`assets/dashboards/`) and the recommended monitors
(`assets/monitors/`). That union is 61 metrics, of which 58 belong to this check;
`data_streams.latency`, `data_streams.payload_size`, and `system.mem.total` come from other
sources and are out of scope. Six services:

- **rabbitmq-broker** — a `-management` broker. This image exposes both the management API
  (15672) and the Prometheus/OpenMetrics plugin (15692) on one broker.
- **seed** — one-shot: declares the static queues, exchanges, and bindings so per-object
  metrics have subjects before the first scrape (`seed.sh`).
- **load** — `pivotalrabbitmq/perf-test`, a continuous AMQP workload. A real AMQP client
  is required: `rabbitmqadmin` (HTTP) cannot populate channel, connection, or delivery
  counters. perf-test's publishers and acking consumers keep those counters and the
  queue-depth gauges moving across scrapes. Publishers outpace consumers, and `--qos 50`
  keeps that backlog ready rather than unacked, so both `messages_ready` and
  `messages_unacknowledged` are non-zero; `x-max-length=2000` bounds it.
- **activity-gen** — periodic queue declare/delete churn (`activity-gen.sh`) so the
  node-wide `rabbitmq.queues.created/declared/deleted.count` counters keep advancing;
  perf-test's long-lived queues do not produce churn. Set `ACTIVITY_GEN=0` (host env) to
  idle it.
- **unroutable** — a producer-only perf-test publishing to a routing key nothing is bound
  to, so the unroutable-dropped counters advance.
- **rabbitmq-full** — the entrypoint the evalya task targets: a `socat` forwarder for 5672,
  15672, and 15692, gated on the broker being healthy, `seed` completing, and `load`,
  `activity-gen`, and `unroutable` starting. evalya only starts a task's target and its
  `depends_on` chain, so targeting the broker directly would run it with no workload.

No ports are published to the host, so the fixture cannot clash with a local broker or a
concurrent run. To inspect it by hand, add a Compose override publishing the ports on
`rabbitmq-broker`.

### Two check instances are required

The dashboards and monitors reference metrics from **both** check backends:

- the **management API** produces `rabbitmq.queue.messages_ready`, `rabbitmq.queue.memory`,
  and the per-queue `rabbitmq.queue.messages.*.rate` metrics;
- the **OpenMetrics plugin** produces `rabbitmq.erlang.*`, the `*.count` counters, and
  `rabbitmq.queues.*.count`.

Neither backend emits the other's metric names, so a consumer of `rabbitmq-full` runs two
instances against the one broker:

```yaml
instances:
  # OpenMetrics backend (erlang.*, *.count counters, node/process metrics)
  - prometheus_plugin:
      url: http://<RABBITMQ_HOST>:15692
      include_aggregated_endpoint: true
  # Management backend (messages_ready, memory, per-queue rates)
  - rabbitmq_api_url: http://<RABBITMQ_HOST>:15672/api/
    rabbitmq_user: guest
    rabbitmq_pass: guest
    queues_regexes: ['.*']
    exchanges_regexes: ['.*']
    collect_node_metrics: true
```

`queues_regexes: ['.*']` matters: pointing the management instance at a fixed queue list
that excludes the active perf-test queues leaves the per-queue rate metrics at zero.

### Verifying coverage

Run the check **at least twice** (`-t 2`). A single `agent check` scrape emits no
OpenMetrics counters — the OpenMetrics v2 base check needs a prior sample to submit a
`.count` metric, so one scrape drops every counter regardless of traffic:

```shell
ddev env agent rabbitmq <env> check rabbitmq -t 2 --json
```

Measured result on broker 4.0.9 with both instances above: **56 of the 58 in-scope metrics
emitted live**, the two exceptions being the RabbitMQ 4.x removals below. When a whole class
of metrics (everything ending `.count`) is missing while the matching gauges are present,
suspect a single-scrape run before touching the workload.

### Metrics not reachable on RabbitMQ 4.x

`rabbitmq.process.max_tcp_sockets` and `rabbitmq.process.open_tcp_sockets` were removed in
RabbitMQ 4.0, which tracks file descriptors instead; the check's own suite records this in
`metrics.py` as `RABBITMQ_4_0_REMOVED`. A 4.0.9 broker emits neither on `/metrics` nor on
`/metrics/per-object`, so no workload can cover them here.

The fixture pins 4.x deliberately: `RABBITMQ_4_0_QUEUE_DELIVERY_METRICS`
(`rabbitmq.queue.messages.acked.count`, `.delivered.count`, `.redelivered.count`, and
`.delivered.ack.count`) exist only on 4.x and are all in the coverage target, so downgrading
to 3.x to recover the two socket gauges would lose more target metrics than it gains. The
3.x images also ship the incompatible v1 `rabbitmqadmin`, which `seed.sh` does not support.

Recorded 3.x payloads containing both metrics do exist under `fixtures/` (`metrics.txt`,
`per-object.txt`). They are deliberately not served as an extra scrape target: doing so would
add ~200 frozen 3.x series next to the live ones for the sake of two gauges.
