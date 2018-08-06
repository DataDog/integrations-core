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

#### Preparing Istio

Istio needs to have the built in [prometheus adapter][2] enabled and the ports exposed to the agent.

#### Connect the Agent

Edit the `istio.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][8], to connect it to Istio. See the [sample istio.d/conf.yaml][3] for all available configuration options:

```
init_config:

instances:
  - istio_mesh_endpoint: http://istio-telemetry.istio-system:42422/metrics
    mixer_endpoint: http://istio-telemetry.istio-system:9093/metrics
    send_histograms_buckets: true
```

Both endpoints need to be connected to the check for it to work. To learn more about the prometheus adapter, you can read the [istio documentation][4].

### Validation

[Run the Agent's `info` subcommand][5] and look for `istio` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][6] for a list of metrics provided by this check.

### Events
The Istio check does not include any events at this time.

### Service Checks
The Istio check does not include any service checks at this time.

## Troubleshooting
Need help? Contact [Datadog Support][7].

[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://istio.io/docs/tasks/telemetry/querying-metrics.html#about-the-prometheus-add-on
[3]: https://github.com/DataDog/integrations-core/blob/master/istio/datadog_checks/istio/data/conf.yaml.example
[4]: https://istio.io/docs/tasks/telemetry/querying-metrics.html#about-the-prometheus-add-on
[5]: https://docs.datadoghq.com/agent/faq/agent-status-and-information/
[6]: https://github.com/DataDog/integrations-core/blob/master/istio/metadata.csv
[7]: https://docs.datadoghq.com/help/
[8]: https://docs.datadoghq.com/agent/faq/agent-configuration-files/#agent-configuration-directory
