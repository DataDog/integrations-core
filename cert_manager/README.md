# Agent Check: cert_manager

## Overview

This check collects metrics from [cert-manager][1].

![Cert-Manager Overview Dashboard][2]

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][3] for guidance on applying these instructions.

### Installation

The cert_manager check is included in the [Datadog Agent][3] package.
No additional installation is needed on your server.

### Configuration

1. Edit the `cert_manager.d/conf.yaml` file in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your cert_manager performance data. See the [sample cert_manager.d/conf.yaml][4] for all available configuration options.

2. [Restart the Agent][5].

### Validation

[Run the Agent's status subcommand][6] and look for `cert_manager` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this check.

### Events

The cert_manager integration does not include any events.

### Service Checks

See [service_checks.json][8] for a list of service checks provided by this integration.

## Troubleshooting

### Duplicate name tags

Each certificate name is exposed within the `name` label in the Prometheus payload and is converted to a tag by the Datadog Agent. If your hosts also use the `name` tag (for instance, automatically collected by the [AWS integration][9]), metrics coming from this integration will present both values. To avoid duplicate `name` tags, you can use the [`rename_labels`configuration parameter][10] to map the Prometheus label `name` to the Datadog tag `cert_name`. This ensures you have a single value within the tag `cert_name` to identify your certificates :
```yaml
init_config:
instances:
- openmetrics_endpoint: <OPENMETRICS_ENDPOINT>
  rename_labels:
    name: cert_name
```

Need further help? Contact [Datadog support][11].

[1]: https://github.com/jetstack/cert-manager
[2]: https://raw.githubusercontent.com/DataDog/integrations-core/master/cert_manager/images/overview_dashboard.png
[3]: https://app.datadoghq.com/account/settings/agent/latest
[4]: https://github.com/DataDog/integrations-core/blob/master/cert_manager/datadog_checks/cert_manager/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/cert_manager/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/cert_manager/assets/service_checks.json
[9]: https://docs.datadoghq.com/integrations/amazon_web_services/
[10]: https://github.com/DataDog/integrations-core/blob/81b91a54328f174c5c1e92cb818640cba1ddfec3/cert_manager/datadog_checks/cert_manager/data/conf.yaml.example#L153-L155
[11]: https://docs.datadoghq.com/help/