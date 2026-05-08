# n8n integration lab

A long-running n8n simulation that pushes real metrics to a Datadog org so you can iterate on dashboards, monitors, and customer reports against live data.

It reuses the integration test environment (so you get queue mode, a worker, the full Datadog Agent) and layers on top:

- five lab-only workflows with distinct shapes (fast, slow, always-fail, flaky, multi-step chain), and
- an async traffic generator that drives a configurable webhook + REST API mix and reloads its config on the fly.

## Setup

### Datadog credentials

The lab uses a `.ddev.toml` in this directory (already committed) to point at an `n8nlab` ddev org. Add the matching entry to your global `~/.ddev/config.toml`:

```toml
[orgs.n8nlab]
api_key = "<your real Datadog API key>"
site = "datadoghq.com"
```

Use any org name you like; just keep `org = "n8nlab"` in `tests/lab/.ddev.toml` aligned with what you put in your global config.

### Traffic configuration

`tests/lab/config.yaml` controls the traffic mix. Probabilities are independent draws per tick, and values above `1.0` mean "more than one call per tick on average":

```yaml
webhook_probabilities:
  /webhook/lab/fast: 0.9      # bulk traffic, fast histogram bucket
  /webhook/lab/slow: 0.4      # populates higher histogram buckets
  /webhook/lab/fail: 0.15     # populates workflow_failed
  /webhook/lab/flaky: 0.5     # mixed success/failure
  /webhook/lab/chain: 0.3     # 4 Set nodes -> 4x node.* events
api_probabilities:
  /healthz: 1.0
  /healthz/readiness: 0.5
  /rest/login: 0.2            # 401s
tick_seconds: 1.0
reload_interval: 5
```

Edit this file while the lab is running and the generator will pick it up on the next `reload_interval` tick.

## Usage

### One-shot (recommended)

```bash
./tests/lab/run_lab.sh                # default env: py3.13-2 (n8n 2.19.5)
./tests/lab/run_lab.sh -e py3.13-1    # n8n 1.118.1
```

The script brings up the env, imports & activates the lab workflows, restarts n8n so webhooks register, and starts the traffic generator. `Ctrl+C` triggers a `cleanup` trap that runs `lab:stop` to tear everything down.

### Individual hatch commands

```bash
hatch run lab:start -e py3.13-2     # ddev env start + import lab workflows + restart
hatch run lab:generate              # traffic loop (foreground; Ctrl+C to stop)
hatch run lab:stop -e py3.13-2      # ddev env stop
```

## What this exercises

The lab is wired to populate every metric family the integration maps that does not require an SSO/embed flow:

| Metric family | How the lab drives it |
| --- | --- |
| `n8n.workflow.started/.success/.failed.count` | every webhook hit goes through the EventBus |
| `n8n.workflow.execution.duration.seconds.*` (n8n 2.x) | the slow & chain workflows spread the histogram |
| `n8n.node.started/.finished.count` | the worker fires per-node events; the chain workflow yields 4× per call |
| `n8n.queue.job.enqueued/.dequeued/.completed/.failed.count` | queue mode is enabled in the test compose |
| `n8n.scaling.mode.queue.jobs.{active,waiting,completed,failed}` | main process tracks queue depth |
| `n8n.http.request.duration.seconds.*` | the API mix (`/healthz`, `/rest/login`) drives status code labels |
| `n8n.cache.hits/.misses/.updates.count` | cache traffic comes from n8n itself during execution |
| `n8n.last.activity` | refreshed on every API call |
| `n8n.{production,production.root,manual,enabled.users,users,workflows,credentials}.total` | enabled in the test compose via `N8N_METRICS_INCLUDE_WORKFLOW_STATISTICS` |

What it does **not** exercise (these need extra infra and are documented in the README "Version-specific metrics" section):

- `n8n.token.exchange.*` and `n8n.embed.login.*` — require an SSO IdP / embed integration.
- `n8n.audit.workflow.*` — fire on UI-driven activate/deactivate; not currently driven by the generator. Future iteration could call the n8n REST API to toggle workflow active state on a slow timer.

## Stopping the lab

`Ctrl+C` from `run_lab.sh` cleans up automatically. If you ran the hatch commands directly:

```bash
hatch run lab:stop -e py3.13-2
```
