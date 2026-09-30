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
sources and are out of scope. Thirteen services:

- **rabbitmq-broker** — a `-management` broker, RabbitMQ 4.0 by default. This image exposes
  both the management API (15672) and the Prometheus/OpenMetrics plugin (15692) on one
  broker. It is the primary broker: every `RABBITMQ_*` provide points at it. It also runs
  the alarm drill (`alarm-drill.sh`, below) in the background.
- **seed** — one-shot: declares the static queues, exchanges, and bindings so per-object
  metrics have subjects before the first scrape (`seed.sh`).
- **load** — `pivotalrabbitmq/perf-test`, a continuous AMQP workload. A real AMQP client
  is required: `rabbitmqadmin` (HTTP) cannot populate channel, connection, or delivery
  counters. perf-test's publishers and acking consumers keep those counters and the
  queue-depth gauges moving across scrapes. The publish rate alternates every 60s between
  below and above the consumer rate (`--variable-rate`), so rates and queue depth rise
  and fall instead of plateauing. The high phase builds a backlog that the low phase only
  partly drains, and `--qos 50` keeps it ready rather than unacked, so both
  `messages_ready` and `messages_unacknowledged` stay non-zero; `x-max-length=2000`
  bounds it.
- **activity-gen** — periodic queue declare/delete churn (`activity-gen.sh`) so the
  node-wide `rabbitmq.queues.created/declared/deleted.count` counters keep advancing;
  perf-test's long-lived queues do not produce churn. Set `ACTIVITY_GEN=0` (host env) to
  idle it; the same switch idles `autoack`, `redeliver`, `unacked-swing`, `slow-reader`,
  and `load3`, and turns off the alarm drill (the containers stay up).
- **unroutable** — a producer-only perf-test publishing to a routing key nothing is bound
  to, so the unroutable-dropped counters advance.
- **conn-churn** — a looping short-lived perf-test (one producer, one consumer, 20s per
  cycle). `load`'s connections live for the whole run, so without it the
  connection/channel opened/closed counters and the consumer count stay flat. Its
  consumer is not rate-capped, so the queue stays near empty. A capped consumer here would
  build a backlog that is requeued on every close; that 30s sawtooth aliases against the
  scrape intervals, and different scrapers then report different averages for the same
  queue.
- **unacked-swing**: a long-lived perf-test on the durable `unacked-swing` queue, for
  `rabbitmq.queue.messages_unacknowledged.rate` (`load`'s unacked count is pinned at its
  `--qos`, and `conn-churn`'s stays near 0, so neither moves it). A constant 4 msg/s
  publisher feeds a consumer whose per-message latency alternates every 120s
  (`--variable-latency`) between 2 msg/s and 8 msg/s of capacity. Unacked climbs to about
  240, drains, and idles near 0 on a 240s cycle; `--qos 300` sits above that peak, so the
  backlog is unacked rather than ready. The cycle is slow on purpose, so every scraper's
  average stays close.
- **autoack**: a long-lived perf-test whose consumer uses automatic acknowledgement
  (`--autoack`). `rabbitmq.channel.messages.delivered.count` and
  `rabbitmq.queue.messages.delivered.count` count only auto-ack deliveries; every other
  consumer acks manually.
- **redeliver**: a long-lived perf-test whose consumer nacks with requeue (`--nack`), so
  every message is redelivered: drives `rabbitmq.queue.messages.redeliver.count`
  (management) and `rabbitmq.queue.messages.redelivered.count` (OpenMetrics). With
  `--flag persistent`, perf-test declares the queue durable and publishes persistent
  messages; nacked messages never leave, so the queue always holds persistent messages for
  `rabbitmq.queue.messages.persistent`. `x-max-length=200` bounds it.
- **slow-reader**: bespoke traffic (`slow_reader.py`, stdlib-only Python in
  `python:3.13-alpine`) for `rabbitmq.connection.pending_packets`, which counts bytes the
  broker has queued on a socket but not yet handed to the kernel. Every off-the-shelf client
  drains its socket as fast as it can, so this one implements just enough AMQP 0-9-1 to
  run an auto-ack consumer that reads its socket at about 32 KiB/s through a 4 KiB receive
  buffer, while a second connection publishes about 100 KiB/s to the same queue. The kernel
  buffers stay full and the broker always has a few KiB pending on that connection. It
  throttles instead of stopping: RabbitMQ closes a connection whose socket send blocks for
  30s, so a client that never reads shows pending bytes for about 30s per connection.
  Bounded: auto-ack leaves nothing unacked, `x-max-length=1000` caps the `slow-reader`
  queue (the publisher outpaces the reader, so it stays full and drops from the head, about
  1 MiB), both rates are fixed, and the consumer reconnects every 600s. The first ~30s after
  each connect fill the kernel buffers, so the gauge reads 0 then. Idles with
  `ACTIVITY_GEN=0`.
- **rabbitmq3-broker**: a second `-management` broker on RabbitMQ 3.13
  (`RABBITMQ3_VERSION`), for the three socket metrics 4.x no longer reports (see "The
  RabbitMQ 3.13 broker" below).
- **load3**: one perf-test producer and one consumer at 2 msg/s on the 3.13 broker, so its
  socket gauges count live connections. Idles with `ACTIVITY_GEN=0`.
- **rabbitmq-full** — the entrypoint the evalya task targets: a `socat` forwarder for 5672,
  15672, and 15692 to the primary broker, and for 5673, 15673, and 15693 to the 3.13
  broker's 5672, 15672, and 15692. It is gated on both brokers being healthy, `seed`
  completing, and every workload service starting. evalya only starts a task's target and its `depends_on` chain, so targeting the
  broker directly would run it with no workload.

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

### Configurable inputs

All are read from the host environment and have working defaults.

| Variable | Default | Effect |
|---|---|---|
| `RABBITMQ_VERSION` | `4.0` | Primary broker image tag (`rabbitmq:<v>-management`), shared by `seed` and `activity-gen`. |
| `RABBITMQ3_VERSION` | `3.13` | Second broker image tag. Keep it on 3.x: the socket metrics it exists for are gone on 4.x. |
| `ACTIVITY_GEN` | `1` | `0` idles every workload service, including the alarm drill. |
| `ALARM_DRILL` | `1` | `0` turns off only the alarm drill. |

### The alarm drill

`rabbitmq.node.mem_alarm`, `rabbitmq.node.disk_alarm` (management) and
`rabbitmq.alarms.free_disk_space.watermark` (OpenMetrics) are 0 on a healthy broker. The
primary broker runs `alarm-drill.sh` in the background of its own container, so
`rabbitmqctl` reaches the node with the node's cookie and name; a sidecar would need a
shared cookie file and a pinned broker hostname (the node name follows it). 60s after
the broker starts, and then every 180s, it sets `vm_memory_high_watermark` to 0.0001 and
`disk_free_limit` to 100000GB, which raises both alarms, holds them for 25s, and restores the
values it read at startup (0.6 and 50000000 on the 4.0 image). The restore runs on exit
and retries on failure; the settings are runtime-only, so a broker restart also clears them.

The window is sized against the scrapers: the DD check and the OTel `rabbitmqreceiver`
both default to 15s, and `/api/nodes` reports the alarm about 8s late at both ends, so a
25s window always holds at least one scrape per collector. It stays under perf-test's 30s
confirm timeout: evalya ignores `restart:` policies, so a perf-test that exited would stay
down.

Side effects, measured on 4.0.9 (ten `-t 2` runs 21s apart; one landed in a window):

- Every publishing connection blocks for the 25s, about 14% of the time. `load` drops
  from ~120 msg/s to 0, then bursts (~360 msg/s) when the alarm clears.
- In the run inside the window, `rabbitmq.queue.messages.publish.rate` read 0 on every
  queue. The other target metrics stayed non-zero, and all of them were non-zero in the
  runs outside the window. No workload container exited.
- Gauges and rates sampled by two scrapers at different instants disagree more around
  a window edge, so pairwise comparisons of publish rates are noisier.

Set `ALARM_DRILL=0` when a consumer needs uninterrupted publish traffic more than the
alarm metrics.

### The RabbitMQ 3.13 broker

`rabbitmq.node.sockets_used`, `rabbitmq.process.max_tcp_sockets`, and
`rabbitmq.process.open_tcp_sockets` are unreachable on 4.x: 4.0 stopped tracking TCP
sockets, so `/api/nodes` reports `sockets_used: 0` and the Prometheus plugin no longer
exposes the two process gauges (the check's own suite lists them as
`RABBITMQ_4_0_REMOVED` in `metrics.py`). Downgrading the primary broker is not an option:
the 4.x-only `rabbitmq.queue.messages.acked.count`, `.delivered.count`,
`.redelivered.count`, and `.delivered.ack.count` are also in the target, and `seed.sh`
needs the v2 `rabbitmqadmin` that ships with 4.x. So the fixture runs a second broker,
`rabbitmq3-broker`, on 3.13, with `load3` holding two connections open on it.

It is published through the same entrypoint on ports shifted by one, with the primary's
`guest`/`guest` credentials:

| Provide | Value |
|---|---|
| `RABBITMQ3_HOST` | the entrypoint's hostname (same as `RABBITMQ_HOST`) |
| `RABBITMQ3_AMQP_PORT` | `5673` |
| `RABBITMQ3_MANAGEMENT_PORT` | `15673` |
| `RABBITMQ3_OPENMETRICS_PORT` | `15693` |

The three metrics come from different backends: `node.sockets_used` from the management
API, the two `process.*` gauges from the Prometheus plugin's aggregated `/metrics`. A
consumer that wants them adds two more instances, tagged so they are not summed with the
4.0 broker's series (both brokers otherwise emit the same metric names):

```yaml
  - prometheus_plugin:
      url: http://<RABBITMQ3_HOST>:15693
      include_aggregated_endpoint: true
    tags: ["rabbitmq_broker:3.13"]
  - rabbitmq_api_url: http://<RABBITMQ3_HOST>:15673/api/
    rabbitmq_user: guest
    rabbitmq_pass: guest
    collect_node_metrics: true
    tags: ["rabbitmq_broker:3.13"]
```

Everything else about `rabbitmq-full` is unchanged: the `RABBITMQ_*` provides still point
at the 4.0 broker, and a consumer that ignores the `RABBITMQ3_*` ones sees the same
endpoints as before.

### Verifying coverage

Run the check **at least twice** (`-t 2`). A single `agent check` scrape emits no
OpenMetrics counters — the OpenMetrics v2 base check needs a prior sample to submit a
`.count` metric, so one scrape drops every counter regardless of traffic:

```shell
ddev env agent rabbitmq <env> check rabbitmq -t 2 --json
```

Coverage counts a metric only when some scrape reports it **non-zero**. Measured with
`datadog/agent:7` (7.83.1) and this branch's check, four instances (the two above against
4.0.9, the OpenMetrics one also scraping the `detailed` endpoint for the
`queue_coarse_metrics`, `queue_consumer_count`, `queue_delivery_metrics`, and
`channel_queue_exchange_metrics` families, plus the two 3.13.7 instances), ten `-t 2` runs
21s apart starting ~3.5 minutes after the fixture turned healthy: **all 58 in-scope metrics
emitted and non-zero**, all live. 55 are non-zero on the 4.0 broker; the three socket
metrics are non-zero only on the 3.13 broker (`sockets_used` 3, `open_tcp_sockets` 3,
`max_tcp_sockets` 471769). The three alarm metrics read 1 only in runs that land in a drill
window, so space runs less than 25s apart, or span a few 180s cycles, to catch one.
`rabbitmq.queue.messages.paged_out` needs the `load` backlog to build, so it reads 0 in the
first minute. When a whole class of metrics (everything ending `.count`) is missing while
the matching gauges are present, suspect a single-scrape run before touching the workload.

### Live but not organic

Three workloads exist only to move specific metrics and do not resemble a real
deployment: the alarm drill (state is forced, not reached), `slow-reader` (a hand-written
AMQP client that lags on purpose), and the 3.13 broker (a second node on an older version).
Their values are live, not fixture-backed: no recorded payload under `fixtures/` is served.
