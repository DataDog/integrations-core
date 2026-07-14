# Memchurn

## Overview

Memchurn is a synthetic check whose sole purpose is to reproduce, on demand, the
memory-fragmentation behavior of heavily multi-threaded native checks such as
[`postgres`][1] (psycopg2) and [`kafka_consumer`][2] (librdkafka). It emits a few
metrics for observability, but the metrics themselves are irrelevant — only the
check's allocation *behavior* matters.

Use it to A/B test allocators (glibc vs. jemalloc), tune `MALLOC_ARENA_MAX`, and
validate memory-related Agent changes with a workload you can dial up and down.

### Why native checks fragment memory

The Agent's RSS grows under fragmentation because C-backed checks spawn many OS
threads that allocate and free memory concurrently *at the C level*. Under glibc,
each such thread is assigned its own malloc **arena** (up to `8 * ncores`), and
freed memory is not returned to the OS, so RSS climbs and stays high.

Two properties are essential to reproducing this, and Memchurn is built around
both:

1. **The GIL must be released during allocation.** Pure-Python allocation holds
   the GIL, so threads never allocate in parallel and glibc never grows past ~2
   arenas. Memchurn allocates through libc `malloc`/`free` via `ctypes`, whose
   foreign calls release the GIL, so worker threads genuinely allocate in
   parallel in C.
2. **Allocations must bypass CPython's `pymalloc`.** Small Python objects
   (≤512 B) are served by CPython's `obmalloc`, which manages its own arenas and
   returns them to the OS, so glibc never sees the churn. Memchurn allocates raw
   bytes with libc directly instead of using `bytes`/`bytearray`/lists.

## Setup

### Installation

This is a development-only check that ships with the Agent's Python environment.
Because all runtime logic lives in a single module with no third-party
dependencies, it can also be deployed as a single-file check by copying
[`check.py`][3] into the Agent's `checks.d/` directory as `memchurn.py`.

### Configuration

1. Edit the `memchurn.d/conf.yaml` file in the `conf.d/` folder at the root of
   your Agent's configuration directory. See the [sample conf.yaml][4] for all
   available options.

2. [Restart the Agent][5].

A minimal, ready-to-run instance uses the defaults for everything:

```yaml
instances:
  - {}
```

The most impactful options:

| Option                   | Default | Effect                                                                 |
| ------------------------ | ------- | ---------------------------------------------------------------------- |
| `num_workers`            | 48      | Long-lived allocator threads. More workers → more glibc arenas → more RSS. |
| `allocations_per_worker` | 256     | malloc/free cycles per worker per run.                                 |
| `min_alloc_bytes`        | 512     | Smallest allocation.                                                   |
| `max_alloc_bytes`        | 4194304 | Largest allocation (default 4 MiB crosses glibc's ~128 KiB mmap threshold). |
| `retained_fraction`      | 0.1     | Fraction of allocations retained across runs.                          |
| `max_retained_bytes`     | 268435456 | Cap on the retained working set (256 MiB). Lower it to lower the RSS plateau. |
| `max_total_bytes`        | 1073741824 | Hard ceiling on live bytes (1 GiB). The check never allocates past this. |
| `hold_ms`                | 0       | Hold time per allocation; raises the concurrent live set.              |
| `thread_churn_per_run`   | 8       | Short-lived threads per run that force glibc to cycle arenas.          |
| `run_budget_seconds`     | 5       | Wall-clock budget per run; the check idles between runs.               |

## Data Collected

### Metrics

See [metadata.csv][6] for a list of metrics provided by this check. All values
are diagnostic (worker count, retained/live bytes, malloc/free call counts, RSS,
and — on Linux/glibc — the glibc arena count from `malloc_info`).

### Service Checks

Memchurn does not include any service checks.

### Events

Memchurn does not include any events.

## Standalone reproduction

To sanity-check the allocation engine without an Agent, run the bundled script on
a Linux box:

```shell
python memchurn/dev/standalone_repro.py --workers 48 --runs 20
```

It prints thread count, RSS, retained bytes, and (on glibc) the arena count over
time. Under glibc you should see RSS climb and then plateau well above the
retained bytes — that gap is the fragmentation. Re-run under jemalloc to see the
contrast:

```shell
LD_PRELOAD=$(find / -name 'libjemalloc.so.2' 2>/dev/null | head -1) \
  python memchurn/dev/standalone_repro.py --workers 48 --runs 20
```

With jemalloc, RSS tracks much closer to the retained bytes.

## Troubleshooting

Need help? Contact [Datadog support][7].

[1]: https://github.com/DataDog/integrations-core/tree/master/postgres
[2]: https://github.com/DataDog/integrations-core/tree/master/kafka_consumer
[3]: https://github.com/DataDog/integrations-core/blob/master/memchurn/datadog_checks/memchurn/check.py
[4]: https://github.com/DataDog/integrations-core/blob/master/memchurn/datadog_checks/memchurn/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#restart-the-agent
[6]: https://github.com/DataDog/integrations-core/blob/master/memchurn/metadata.csv
[7]: https://docs.datadoghq.com/help/
