# External DNS Integration

## Overview

Get real-time metrics from External DNS to visualize and monitor DNS synchronization. Track source and registry records, controller status, and HTTP request latencies.

For more information about External DNS, see the [GitHub repo][1].

**Minimum Agent version:** 7.17.0

## Setup

This OpenMetrics-based integration has two modes: latest mode (enabled by setting `openmetrics_endpoint`) and legacy mode (enabled by setting `prometheus_url`). Datadog recommends using the latest mode for all new deployments. For more information, see [Latest and Legacy Versioning For OpenMetrics-based Integrations][10].

### Prerequisites

The latest mode requires Python 3. For hosts that cannot use Python 3, use the legacy mode instead.

Configure External DNS to expose Prometheus metrics by setting the `--metrics-address` flag (default: `:7979`).

### Installation

The External DNS check is included in the [Datadog Agent][2] package. You do not need to install anything else on your servers.

### Configuration

**Note**: For hosts unable to use Python 3, see the legacy mode [configuration example][11]. The `external_dns.d/auto_conf.yaml` file enables the `prometheus_url` option for legacy mode by default. See the sample [external_dns.d/conf.yaml.example][3] for all available configuration options.

To configure this check for an Agent running on Kubernetes:

Set [Autodiscovery Integration Templates][8] as pod annotations on your application container. Alternatively, you can configure templates with a [file, configmap, or key-value store][9].

**Annotations v1** (for Datadog Agent < v7.36)

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: external-dns
  annotations:
    ad.datadoghq.com/external-dns.check_names: '["external_dns"]'
    ad.datadoghq.com/external-dns.init_configs: '[{}]'
    ad.datadoghq.com/external-dns.instances: |
      [
        {
          "openmetrics_endpoint": "http://%%host%%:7979/metrics",
          "tags": ["externaldns-pod:%%host%%"]
        }
      ]
  labels:
    name: external-dns
spec:
  containers:
    - name: external-dns
```

**Annotations v2** (for Datadog Agent v7.36 or later)

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: external-dns
  annotations:
    ad.datadoghq.com/external-dns.checks: |
      {
        "external_dns": {
          "init_config": {},
          "instances": [
            {
              "openmetrics_endpoint": "http://%%host%%:7979/metrics",
              "tags": ["externaldns-pod:%%host%%"]
            }
          ]
        }
      }
  labels:
    name: external-dns
spec:
  containers:
    - name: external-dns
```

To enable the legacy mode of this OpenMetrics-based check, replace `openmetrics_endpoint` with `prometheus_url`:

**Annotations v1** (for Datadog Agent < v7.36)

```yaml
    ad.datadoghq.com/external-dns.instances: |
      [
        {
          "prometheus_url": "http://%%host%%:7979/metrics",
          "tags": ["externaldns-pod:%%host%%"]
        }
      ]
```

**Annotations v2** (for Datadog Agent v7.36 or later)

```yaml
          "instances": [
            {
              "prometheus_url": "http://%%host%%:7979/metrics",
              "tags": ["externaldns-pod:%%host%%"]
            }
          ]
```

**Notes**:

- The shipped `external_dns.d/auto_conf.yaml` file enables the `prometheus_url` option by default for legacy mode.
- The `externaldns-pod` tag keeps track of the target DNS pod IP. The other tags are related to the Datadog Agent that is polling the information using the service discovery.
- For Deployments, add the annotations to the metadata of the template's specifications. Do not add them at the outer specification level.

### Validation

[Run the Agent's `status` subcommand][4] and look for `external_dns` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][5] for a list of metrics provided by this integration.

The latest mode submits the `.sum` and `.count` summary samples as `monotonic_count` type. In legacy mode, these are submitted as `gauge` type.

#### Metric type differences between integration modes

The integration supports two modes that handle Prometheus metric types differently:

| Prometheus Type | Legacy mode (`prometheus_url`) | Latest mode (`openmetrics_endpoint`) |
|-----------------|-------------------------------|-------------------------------------|
| gauge | gauge | gauge |
| counter | gauge (raw value) | monotonic_count (delta between scrapes) |
| summary.quantile | gauge | gauge |
| summary.sum | gauge | monotonic_count |
| summary.count | gauge | monotonic_count |

**Notes:**:

- Counter metrics with zero values are not emitted by the latest mode on the first scrape (requires a delta > 0).
- The `metadata.csv` reflects the latest mode behavior as the reference.
- The `host` label from `http_request_duration_seconds` is automatically renamed to `http_host` to avoid conflicts with Datadog's reserved tags.

#### External DNS version differences

The integration supports the following External DNS metric formats:

| External DNS version | Metric format | Example |
|---------------------|---------------|---------|
| Before v1.18 | Separate metrics per record type | `external_dns_registry_a_records`, `external_dns_registry_aaaa_records` |
| v1.18+ | Vector metrics with `record_type` label | `external_dns_registry_records{record_type="a"}` |

### Events

The External DNS check does not include any events.

### Service Checks

**external_dns.prometheus.health** (Legacy mode): Returns `CRITICAL` if the check cannot access the metrics endpoint, otherwise returns `OK`.

**external_dns.openmetrics.health** (Latest mode): Returns `CRITICAL` if the check cannot access the metrics endpoint, otherwise returns `OK`.

See [service_checks.json][6] for the full specification.

## Troubleshooting

Need help? Contact [Datadog support][7].

[1]: https://github.com/kubernetes-sigs/external-dns
[2]: /account/settings/agent/latest
[3]: https://github.com/DataDog/integrations-core/blob/master/external_dns/datadog_checks/external_dns/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[5]: https://github.com/DataDog/integrations-core/blob/master/external_dns/metadata.csv
[6]: https://github.com/DataDog/integrations-core/blob/master/external_dns/assets/service_checks.json
[7]: https://docs.datadoghq.com/help/
[8]: https://docs.datadoghq.com/agent/kubernetes/integrations/?tab=kubernetes
[9]: https://docs.datadoghq.com/agent/kubernetes/integrations/?tab=kubernetes#configuration
[10]: https://docs.datadoghq.com/integrations/guide/versions-for-openmetrics-based-integrations
[11]: https://github.com/DataDog/integrations-core/blob/7.32.x/external_dns/datadog_checks/external_dns/data/conf.yaml.example
