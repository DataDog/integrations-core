# GitLab Integration

## Overview

Integration that allows to:

- Visualize and monitor metrics collected with GitLab and Gitaly through Prometheus

See [Monitoring GitLab with Prometheus][1] for more information.

For more in-depth monitoring of your GitLab pipelines, check out [CI Pipeline Visibility][17]. CI Pipeline Visibility provides granular insights into your user workflow, lets you access detailed Git metadata, and tracks pipeline performance over time.

## Setup

This OpenMetrics-based integration has a latest mode (enabled by setting `openmetrics_endpoint` to point to the target endpoint) and a legacy mode (enabled by setting `prometheus_url` instead). To get all the most up-to-date features, Datadog recommends enabling the latest mode. For more information, see [Latest and Legacy Versioning For OpenMetrics-based Integrations][18].

Metrics marked as `[OpenMetricsV1]` or `[OpenMetricsV2]` are only available using the corresponding mode of the GitLab integration. All other metrics are collected by both modes. 

### Installation

The GitLab check is included in the [Datadog Agent][2] package, so you don't need to install anything else on your GitLab servers.

### Configuration

<!-- xxx tabs xxx -->
<!-- xxx tab "Host" xxx -->

#### Host

To configure this check for an Agent running on a host:

##### Metric collection

1. Edit the `gitlab.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][3], to point to the GitLab's metrics [endpoint][4].
See the [sample gitlab.d/conf.yaml][5] for all available configuration options. If you previously implemented this integration, see the [legacy example][16].

2. In the GitLab settings page, ensure that the option `Enable Prometheus Metrics` is enabled (administrator access is required). For more information on how to enable metric collection, see [GitLab Prometheus metrics][6].

3. Allow access to monitoring endpoints by updating your `/etc/gitlab/gitlab.rb` to include the following line:

    ```
    gitlab_rails['monitoring_whitelist'] = ['127.0.0.0/8', '192.168.0.1']
    ```
    **Note** Save and restart GitLab to see the changes.

4. [Restart the Agent][7].

##### Log collection

1. Collecting logs is disabled by default in the Datadog Agent, enable it in your `datadog.yaml` file:

   ```yaml
   logs_enabled: true
   ```

2. Next, edit `gitlab.d/conf.yaml` by uncommenting the `logs` lines at the bottom. Update the logs `path` with the correct path to your GitLab log files.

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

3. [Restart the Agent][7].

<!-- xxz tab xxx -->
<!-- xxx tab "Containerized" xxx -->

#### Containerized

For containerized environments, see the [Autodiscovery Integration Templates][9] for guidance on applying the parameters below.

##### Metric collection

| Parameter            | Value                                                                                         |
| -------------------- |-----------------------------------------------------------------------------------------------|
| `<INTEGRATION_NAME>` | `gitlab`                                                                                      |
| `<INIT_CONFIG>`      | blank or `{}`                                                                                 |
| `<INSTANCE_CONFIG>`  | `{"gitlab_url":"http://%%host%%/", "openmetrics_endpoint":"http://%%host%%:10055/-/metrics"}` |

##### Log collection

Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Kubernetes Log Collection][10].

| Parameter      | Value                                       |
| -------------- | ------------------------------------------- |
| `<LOG_CONFIG>` | `{"source": "gitlab", "service": "gitlab"}` |

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

### Validation

[Run the Agent's status subcommand][11] and look for `gitlab` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][12] for a list of metrics provided by this integration. 

### Events

The GitLab check does not include any events.

### Service Checks

See [service_checks.json][13] for a list of service checks provided by this integration. More information about the `gitlab.readiness.*` service checks can be found in the official [GitLab documentation][15].

## Troubleshooting

Need help? Contact [Datadog support][14].

[1]: https://docs.gitlab.com/ee/administration/monitoring/prometheus
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[4]: https://docs.gitlab.com/ee/administration/monitoring/prometheus/gitlab_metrics.html#collecting-the-metrics
[5]: https://github.com/DataDog/integrations-core/blob/master/gitlab/datadog_checks/gitlab/data/conf.yaml.example
[6]: https://docs.gitlab.com/ee/administration/monitoring/prometheus/gitlab_metrics.html
[7]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[8]: https://github.com/DataDog/integrations-core/blob/master/gitlab/datadog_checks/gitlab/metrics.py
[9]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[10]: https://docs.datadoghq.com/agent/kubernetes/log/
[11]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[12]: https://github.com/DataDog/integrations-core/blob/master/gitlab/metadata.csv
[13]: https://github.com/DataDog/integrations-core/blob/master/gitlab/assets/service_checks.json
[14]: https://docs.datadoghq.com/help/
[15]: https://docs.gitlab.com/ee/user/admin_area/monitoring/health_check.html#readiness
[16]: https://github.com/DataDog/integrations-core/blob/7.43.x/gitlab/datadog_checks/gitlab/data/conf.yaml.example
[17]: https://app.datadoghq.com/ci/getting-started
[18]: https://docs.datadoghq.com/integrations/guide/versions-for-openmetrics-based-integrations