# Gitlab Integration

## Overview

Integration that allows to:

* Visualize and monitor metrics collected via Gitlab through Prometheus

See the [Gitlab documentation][107] for more information about Gitlab and its integration with Prometheus

## Setup
### Installation

The Gitlab check is included in the [Datadog Agent][101] package, so you don't need to install anything else on your Gitlab servers.

### Configuration

Edit the `gitlab.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][108], to point to the Gitlab's Prometheus metrics endpoint.
See the [sample gitlab.d/conf.yaml][102] for all available configuration options.

**Note**: The `allowed_metrics` item in the `init_config` section allows to specify the metrics that should be extracted.

### Validation

[Run the Agent's `status` subcommand][103] and look for `gitlab` under the Checks section.

## Data Collected
### Metrics
See [metadata.csv][104] for a list of metrics provided by this integration.

### Events
The Gitlab check does not include any events at this time.

### Service Checks
The Gitlab check includes a readiness and a liveness service check.
Moreover, it provides a service check to ensure that the local Prometheus endpoint is available.

## Troubleshooting
Need help? Contact [Datadog Support][105].

[101]: https://app.datadoghq.com/account/settings#agent
[102]: https://github.com/DataDog/integrations-core/blob/master/gitlab/datadog_checks/gitlab/data/conf.yaml.example
[103]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[104]: https://github.com/DataDog/integrations-core/blob/master/gitlab/metadata.csv
[105]: https://docs.datadoghq.com/help/
[107]: https://docs.gitlab.com/ee/administration/monitoring/prometheus/
[108]: https://docs.datadoghq.com/agent/faq/agent-configuration-files/#agent-configuration-directory
