# Istio check

## Overview

Use the Datadog Agent to monitor how well Istio is performing.

* Collect metrics on what apps are making what kinds of requests
* Look at how applications are using bandwidth
* Understand istio's resource consumption

## Setup

### Installation

Istio is included in the Datadog Agent. So, just [install the Agent][1] on your istio servers or in your cluster and point it at Istio.

### Configuration

#### Connect the Agent

Edit the `istio.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][2], to connect it to Istio. See the [sample istio.d/conf.yaml][3] for all available configuration options:

```
init_config:

instances:
  - istio_mesh_endpoint: http://istio-telemetry.istio-system:42422/metrics
    mixer_endpoint: http://istio-telemetry.istio-system:15014/metrics
    galley_endpoint: http://istio-galley.istio-system:15014/metrics
    pilot_endpoint: http://istio-pilot.istio-system:15014/metrics
    send_histograms_buckets: true
```

The first two endpoints are required for the check to work. See the [istio documentation][4] to learn more about the prometheus adapter.

### Validation

[Run the Agent's `info` subcommand][5] and look for `istio` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][6] for a list of metrics provided by this check.

### Events
The Istio check does not include any events.

### Service Checks
The Istio check does not include any service checks.

## Troubleshooting
Need help? Contact [Datadog support][7].

## Further Reading
Additional helpful documentation, links, and articles:

- [Monitor your Istio service mesh with Datadog][8]

[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/?tab=agentv6#agent-configuration-directory
[3]: https://github.com/DataDog/integrations-core/blob/master/istio/datadog_checks/istio/data/conf.yaml.example
[4]: https://istio.io/docs/tasks/telemetry/metrics/querying-metrics
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#agent-status-and-information
[6]: https://github.com/DataDog/integrations-core/blob/master/istio/metadata.csv
[7]: https://docs.datadoghq.com/help
[8]: https://www.datadoghq.com/blog/monitor-istio-with-datadog
