# Gitlab Integration

## Overview

Integration that allows to:

- Visualize and monitor metrics collected via Gitlab through Prometheus

See the [Gitlab documentation][1] for more information about Gitlab and its integration with Prometheus.

## Setup

### Installation

The Gitlab check is included in the [Datadog Agent][2] package, so you don't need to install anything else on your Gitlab servers.

### Configuration

#### Host

Follow the instructions below to configure this check for an Agent running on a host. For containerized environments, see the [Containerized](#containerized) section.

##### Metric collection

1. Edit the `gitlab.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][3], to point to the Gitlab's metrics [endpoint][13]. See the [sample gitlab.d/conf.yaml][4] for all available configuration options.

2. In the Gitlab settings page, ensure that the option `Enable Prometheus Metrics` is enabled. You will need to have administrator access. For more information on how to enable metric collection, see the [Gitlab documentation][12]

3. Allow access to monitoring endpoints by updating your `/etc/gitlab/gitlab.rb` to include the following line:

    ```
    gitlab_rails['monitoring_whitelist'] = ['127.0.0.0/8', '192.168.0.1']
    ```
    **Note** Save and restart Gitlab to see the changes.

4. [Restart the Agent][5]

**Note**: The metrics in [gitlab/metrics.py][11] are collected by default. The `allowed_metrics` configuration option in the `init_config` collects specific legacy metrics. Some metrics may not be collected depending on your Gitlab instance version and configuration. See [Gitlab's documentation][12] for further information about its metric collection.


##### Log collection

1. Collecting logs is disabled by default in the Datadog Agent, enable it in your `datadog.yaml` file:

   ```yaml
   logs_enabled: true
   ```

2. Next, edit `gitlab.d/conf.yaml` by uncommenting the `logs` lines at the bottom. Update the logs `path` with the correct path to your Gitlab log files.

   ```yaml
     logs:
       - type: file
         path: /var/log/gitlab/gitlab-rails/production_json.log
         service: '<SERVICE_NAME>'
         source: gitlab
       - type: file
         path: /var/log/gitlab/gitlab-rails/production.log
         service: '<SERVICE_NAME>'
         source: gitlab
       - type: file
         path: /var/log/gitlab/gitlab-rails/api_json.log
         service: '<SERVICE_NAME>'
         source: gitlab
   ```

3. [Restart the Agent][5].

#### Containerized

For containerized environments, see the [Autodiscovery Integration Templates][6] for guidance on applying the parameters below.

##### Metric collection

| Parameter            | Value                                                                                      |
| -------------------- | ------------------------------------------------------------------------------------------ |
| `<INTEGRATION_NAME>` | `gitlab`                                                                                   |
| `<INIT_CONFIG>`      | blank or `{}`                                                                              |
| `<INSTANCE_CONFIG>`  | `{"gitlab_url":"http://%%host%%/", "prometheus_endpoint":"http://%%host%%:10055/-/metrics"}` |

##### Log collection

Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Kubernetes log collection documentation][7].

| Parameter      | Value                                       |
| -------------- | ------------------------------------------- |
| `<LOG_CONFIG>` | `{"source": "gitlab", "service": "gitlab"}` |

### Validation

[Run the Agent's status subcommand][8] and look for `gitlab` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][9] for a list of metrics provided by this integration.

### Events

The Gitlab check does not include any events.

### Service Checks

The Gitlab check includes health, readiness, and liveness service checks.

`gitlab.prometheus_endpoint_up`: Returns `CRITICAL` if the check cannot access the Prometheus metrics endpoint of the Gitlab instance.
`gitlab.health`: Returns `CRITICAL` if the check cannot access the Gitlab instance.
`gitlab.liveness`: Returns `CRITICAL` if the check cannot access the Gitlab instance due to deadlock with Rails Controllers.
`gitlab.readiness`: Returns `CRITICAL` if the Gitlab instance is able to accept traffic via Rails Controllers.

## Troubleshooting

Need help? Contact [Datadog support][10].

[1]: https://docs.gitlab.com/ee/administration/monitoring/prometheus
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[4]: https://github.com/DataDog/integrations-core/blob/master/gitlab/datadog_checks/gitlab/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[7]: https://docs.datadoghq.com/agent/kubernetes/log/
[8]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[9]: https://github.com/DataDog/integrations-core/blob/master/gitlab/metadata.csv
[10]: https://docs.datadoghq.com/help/
[11]: https://github.com/DataDog/integrations-core/blob/master/gitlab/datadog_checks/gitlab/metrics.py
[12]: https://docs.gitlab.com/ee/administration/monitoring/prometheus/gitlab_metrics.html
[13]: https://docs.gitlab.com/ee/administration/monitoring/prometheus/gitlab_metrics.html#collecting-the-metrics
