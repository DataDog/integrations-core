# GitLab Runner Integration

## Overview

Integration that allows to:

- Visualize and monitor metrics collected with GitLab Runners through Prometheus
- Validate that the GitLab Runner can connect to GitLab

For more information about the GitLab Runner and its integration with Prometheus, see the [GitLab Runner documentation][1].

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][2] for guidance on applying these instructions.

### Installation

The GitLab Runner check is included in the [Datadog Agent][3] package, so you don't need to install anything else on your GitLab servers.

### Configuration

Edit the `gitlab_runner.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][4], to point to the Runner's Prometheus metrics endpoint and to the GitLab master to have a service check. See the [sample gitlab_runner.d/conf.yaml][5] for all available configuration options.

The `allowed_metrics` item in the `init_config` section allows you to specify the metrics that should be extracted. Some metrics should be reported as `rate`, for example: `ci_runner_errors`.

### Validation

[Run the Agent's `status` subcommand][6] and look for `gitlab_runner` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Log collection


1. In your `gitlab_runner` [configuration file][8], change the log format to `json` (_Available for GitLab Runner versions >=11.4.0_ ):
   ```toml
   log_format = "json"
   ```

2. Collecting logs is disabled by default in the Datadog Agent, you need to enable it in `datadog.yaml`:

   ```yaml
   logs_enabled: true
   ```

3. Add the `dd-agent` user to the `systemd-journal` group by running:
   ```text
   usermod -a -G systemd-journal dd-agent
   ```

4. Add this configuration block to your `gitlab_runner.d/conf.yaml` file to start collecting your GitLab Runner Logs:

   ```yaml
   logs:
     - type: journald
       source: gitlab-runner
   ```

    See the [sample gitlab_runner.d/conf.yaml][5] for all available configuration options.

5. [Restart the Agent][9].

### Events

The GitLab Runner check does not include any events.

### Service Checks

The GitLab Runner check provides a service check to confirm that the Runner can talk to the GitLab master and another one to ensure that the local Prometheus endpoint is available.

## Troubleshooting

Need help? Contact [Datadog support][10].

[1]: https://docs.gitlab.com/runner/monitoring/
[2]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[3]: https://app.datadoghq.com/account/settings/agent/latest
[4]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[5]: https://github.com/DataDog/integrations-core/blob/master/gitlab_runner/datadog_checks/gitlab_runner/data/conf.yaml.example
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/gitlab_runner/metadata.csv
[8]: https://docs.gitlab.com/runner/configuration/advanced-configuration.html
[9]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[10]: https://docs.datadoghq.com/help/
