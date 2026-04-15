# External DNS Integration

## Overview

Get real-time metrics from external-dns to visualize and monitor DNS synchronization. Track source and registry records, controller status, and HTTP request latencies.

For more information about external-dns, see the [GitHub repo][1].

**Minimum Agent version:** 7.17.0

## Setup

Starting with version 7.0.0, this OpenMetrics-based integration has a latest mode (enabled by setting `openmetrics_endpoint` to point to the target endpoint) and a legacy mode (enabled by setting `prometheus_url` instead). To get all the most up-to-date features, Datadog recommends enabling the latest mode. For more information, see [Latest and Legacy Versioning For OpenMetrics-based Integrations][11].

The latest mode of the External DNS check requires Python 3 and submits the `.sum` and `.count` summary samples as monotonic count type. These metrics were previously submitted as `gauge` type in the legacy mode. See the [`metadata.csv` file][5] for a list of metrics available in each mode.

For hosts unable to use Python 3, or if you previously implemented this integration mode, see the `legacy` mode [configuration example][12]. For Autodiscovery users relying on the `external_dns.d/auto_conf.yaml` file, this file enables the `prometheus_url` option for the `legacy` mode of the check by default. See the sample [external_dns.d/auto_conf.yaml][13] for the default configuration options and the sample [external_dns.d/conf.yaml.example][3] for all available configuration options.

### Prerequisites

Ensure external-dns is configured to expose Prometheus metrics by setting the `--metrics-address` flag (default: `:7979`).

### Installation

The External DNS check is included in the [Datadog Agent][2] package, so you don't need to install anything else on your servers.

### Configuration
<!-- xxx tabs xxx -->
<!-- xxx tab "Docker" xxx -->
#### Docker

To configure this check for an Agent running on a container:

##### Metric collection

Set [Autodiscovery Integration Templates][8] as Docker labels on your application container:

```yaml
LABEL "com.datadoghq.ad.check_names"='["external_dns"]'
LABEL "com.datadoghq.ad.init_configs"='[{}]'
LABEL "com.datadoghq.ad.instances"='[{"openmetrics_endpoint":"http://%%host%%:7979/metrics", "tags":["externaldns-pod:%%host%%"]}]'
```

To enable the legacy mode of this OpenMetrics-based check, replace `openmetrics_endpoint` with `prometheus_url`:

```yaml
LABEL "com.datadoghq.ad.instances"='[{"prometheus_url":"http://%%host%%:7979/metrics", "tags":["externaldns-pod:%%host%%"]}]'
```

<!-- xxz tab xxx -->
<!-- xxx tab "Kubernetes" xxx -->

#### Kubernetes

To configure this check for an Agent running on Kubernetes:

##### Metric collection

Set [Autodiscovery Integrations Templates][9] as pod annotations on your application container. Alternatively, you can configure templates with a [file, configmap, or key-value store][10].

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
- For Deployments, add the annotations to the metadata of the template's specifications. Do not add it at the outer specification level.

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

### Validation

[Run the Agent's `status` subcommand][4] and look for `external_dns` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][5] for a list of metrics provided by this integration.

#### Metric type differences between integration modes

The integration supports two modes that handle Prometheus metric types differently:

| Prometheus Type | Legacy mode (`prometheus_url`) | Latest mode (`openmetrics_endpoint`) |
|-----------------|-------------------------------|-------------------------------------|
| gauge | gauge | gauge |
| counter | gauge (raw value) | monotonic_count (delta between scrapes) |
| summary.quantile | gauge | gauge |
| summary.sum | gauge | monotonic_count |
| summary.count | gauge | monotonic_count |

**Notes:**

- Counter metrics with zero values are not emitted by the latest mode on the first scrape (requires a delta > 0)
- The `metadata.csv` reflects the latest mode behavior as the reference
- The `host` label from `http_request_duration_seconds` is automatically renamed to `http_host` to avoid conflicts with Datadog's reserved tags

#### External-dns version differences

The integration supports both old and new external-dns metric formats:

| external-dns version | Metric format | Example |
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
[8]: https://docs.datadoghq.com/agent/docker/integrations/?tab=docker
[9]: https://docs.datadoghq.com/agent/kubernetes/integrations/?tab=kubernetes
[10]: https://docs.datadoghq.com/agent/kubernetes/integrations/?tab=kubernetes#configuration
[11]: https://docs.datadoghq.com/integrations/guide/versions-for-openmetrics-based-integrations
[12]: https://github.com/DataDog/integrations-core/blob/7.32.x/external_dns/datadog_checks/external_dns/data/conf.yaml.example
[13]: https://github.com/DataDog/integrations-core/blob/master/external_dns/datadog_checks/external_dns/data/auto_conf.yaml
