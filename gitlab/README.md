# Gitlab Integration

## Overview

Integration that allows to:

* Visualize and monitor metrics collected via Gitlab through Prometheus

See https://docs.gitlab.com/ee/administration/monitoring/prometheus/ for
more information about Gitlab and its integration with Prometheus

## Setup
### Installation

The Gitlab check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your Gitlab servers.

### Configuration

Edit the `gitlab.yaml` file to point to the Gitlab's Prometheus metrics endpoint.
See the [sample gitlab.yaml](https://github.com/DataDog/integrations-core/blob/master/gitlab/conf.yaml.example) for all available configuration options.

The `allowed_metrics` item in the `init_config` section allows to specify the metrics that should be extracted.

### Validation

[Run the Agent's `status` subcommand](https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information) and look for `gitlab` under the Checks section.

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
