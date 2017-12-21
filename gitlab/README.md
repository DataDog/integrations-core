# Gitlab Integration

## Overview

Integration that allows to:

* Visualize and monitor metrics collected via Gitlab through Prometheus

See https://docs.gitlab.com/ee/administration/monitoring/prometheus/ for
more information about Gitlab and its integration with Prometheus

## Setup
### Installation

Install the `dd-check-gitlab` package manually or with your favorite configuration manager

### Configuration

Edit the `gitlab.yaml` file to point to the Gitlab's Prometheus metrics endpoint.
See the [sample gitlab.yaml](https://github.com/DataDog/integrations-core/blob/master/gitlab/conf.yaml.example) for all available configuration options.

The `allowed_metrics` item in the `init_config` section allows to specify the metrics that should be extracted.

### Validation

[Run the Agent's `info` subcommand](https://help.datadoghq.com/hc/en-us/articles/203764635-Agent-Status-and-Information) and look for `gitlab` under the Checks section:

    Checks
    ======

        gitlab
        -----------
          - instance #0 [OK]
          - Collected 8 metrics, 0 events & 3 service checks

## Compatibility

The gitlab check is compatible with all major platforms

## Data Collected
### Metrics
See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/gitlab/metadata.csv) for a list of metrics provided by this integration.

### Events
The Gitlab check does not include any event at this time.

### Service Checks
The Gitlab check includes a readiness and a liveness service check.
Moreover, it provides a service check to ensure that the local Prometheus endpoint is available.

## Troubleshooting
Need help? Contact [Datadog Support](http://docs.datadoghq.com/help/).

## Further Reading
Learn more about infrastructure monitoring and all our integrations on [our blog](https://www.datadoghq.com/blog/)
