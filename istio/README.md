# Istio check

## Overview

Use the Datadog Agent to monitor how well Istio is performing.

* Collect metrics on what apps are making what kinds of requests
* Look at how applications are using bandwidth
* Understand istio's resource consumption

## Setup
### Installation

Istio is included in the Datadog Agent. So, just [install the Agent](https://app.datadoghq.com/account/settings#agent) on your istio servers or in your cluster and point it at Istio.

### Configuration

#### Preparing Istio

Istio needs to have the built in [prometheus adapter](https://istio.io/docs/tasks/telemetry/querying-metrics.html#about-the-prometheus-add-on) enabled and the ports exposed to the agent.

#### Connect the Agent

Create a basic `istio.yaml` in the Agent's `conf.d` directory to connect it to istio. See the [sample mysql.yaml](https://github.com/DataDog/integrations-core/blob/master/istio/conf.yaml.example) for all available configuration options:

```
init_config:

instances:
  - istio_mesh_endpoint http://localhost:42422/metrics
    mixer_endpoint http://localhost:9093/metrics
    send_histograms_buckets true
```

Both endpoints need to be connected to the check for it to work. To learn more about the prometheus adapter, you can read the [istio documentation](https://istio.io/docs/tasks/telemetry/querying-metrics.html#about-the-prometheus-add-on).

### Validation

[Run the Agent's `info` subcommand](https://docs.datadoghq.com/agent/faq/agent-status-and-information/) and look for `istio` under the Checks section:

```
  Checks
  ======

    [...]

    istio
    -----
      - instance #0 [OK]
      - Collected 168 metrics, 0 events & 1 service check

    [...]
```

If the status is not OK, see the Troubleshooting section.

## Compatibility

The Istio integration is supported on Istio 0.4.

## Data Collected
### Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/istio/metadata.csv) for a list of metrics provided by this check.

### Events
The Istio check does not include any event at this time.

### Service Checks
The Istio check does not include any service check at this time.

## Troubleshooting
Need help? Contact [Datadog Support](http://docs.datadoghq.com/help/).

## Further Reading
Learn more about infrastructure monitoring and all our integrations on [our blog](https://www.datadoghq.com/blog/)
