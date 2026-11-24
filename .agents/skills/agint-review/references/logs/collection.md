# The log source in config and README

An Agent integration tells customers which log `source` to use, and the pipeline only runs on logs with that source. If the two differ, the pipeline never matches.

## Where the source lives

| Place | Example |
|---|---|
| The `logs` template `example` in `assets/configuration/spec.yaml` | `nginx/assets/configuration/spec.yaml:108` (`source: nginx`) |
| The commented `logs:` block in `datadog_checks/<name>/data/conf.yaml.example`, generated from the spec | `nginx/datadog_checks/nginx/data/conf.yaml.example:481` |
| The README's "Log collection" section: the `logs:` block, plus the Docker label or Kubernetes annotation | `nginx/README.md:197` (block), `:253` (`com.datadoghq.ad.logs` label), `:362` (`ad.datadoghq.com/nginx.logs` annotation) |
| `auto_conf.yaml` | Holds `ad_identifiers` and no log source (`nginx/datadog_checks/nginx/data/auto_conf.yaml`); log annotations live in the README instead. Check it only if a PR adds a `logs` entry there. |

On the pipeline side, the source is `installation_sources` (e.g. `barracuda_secure_edge/assets/logs/barracuda_secure_edge.yaml:5`) and the root pipeline `filter.query` `source:<x>` (e.g. `nginx/assets/logs/nginx.yaml:120`). Older pipelines like nginx's have no `installation_sources`.

## The rule

The `source` in all those places matches the pipeline's `installation_sources` and root query.

- The PR adds the integration, or changes the source on one side (pipeline, spec, example or README) without the other: **Request**.
- The mismatch was already there and the PR doesn't touch either side: **Follow-up** (tenet 3).

In these examples, `service` is the customer's choice. Don't require it to match anything.
