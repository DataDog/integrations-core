# Agent Check: Teamcity

## Overview

This check watches for successful build-related events and sends them to Datadog.

Unlike most Agent checks, this one doesn't collect any metrics-just events.

## Setup

### Installation

The Teamcity check is included in the [Datadog Agent][1] package, so you don't need to install anything else on your Teamcity servers.

### Configuration

#### Prepare Teamcity

To prepare Teamcity, see [Enabling Guest Login][2].

<!-- xxx tabs xxx -->
<!-- xxx tab "Host" xxx -->

#### Host

To configure this check for an Agent running on a host:

Edit the `teamcity.d/conf.yaml` in the `conf.d/` folder at the root of your [Agent's configuration directory][3]. See the [sample teamcity.d/conf.yaml][4] for all available configuration options:

```yaml
init_config:

instances:
  - name: My Website
    server: teamcity.mycompany.com

    # the internal build ID of the build configuration you wish to track
    build_configuration: MyWebsite_Deploy
```

Add an item like the above to `instances` for each build configuration you want to track.

[Restart the Agent][5] to start collecting and sending Teamcity events to Datadog.

##### Log collection

1. Configure Teamcity [logs settings][6].

2. By default, Datadog's integration pipeline supports the following kind of log format:

   ```text
   [2020-09-10 21:21:37,486]   INFO -  jetbrains.buildServer.STARTUP - Current stage: System is ready
   ```

   Clone and edit the [integration pipeline][7] if you defined different conversion [patterns][8].

3. Collecting logs is disabled by default in the Datadog Agent. Enable it in your `datadog.yaml` file:

   ```yaml
   logs_enabled: true
   ```

4. Uncomment the following configuration block in your `teamcity.d/conf.yaml` file. Change the `path` parameter value based on your environment. See the [sample teamcity.d/conf.yaml][4] for all available configuration options.

   ```yaml
   logs:
     - type: file
       path: /opt/teamcity/logs/teamcity-server.log
       source: teamcity
     - type: file
       path: /opt/teamcity/logs/teamcity-activities.log
       source: teamcity
     - type: file
       path: /opt/teamcity/logs/teamcity-vcs.log
       source: teamcity
     - type: file
       path: /opt/teamcity/logs/teamcity-cleanup.log
       source: teamcity
     - type: file
       path: /opt/teamcity/logs/teamcity-notifications.log
       source: teamcity
     - type: file
       path: /opt/teamcity/logs/teamcity-ws.log
       source: teamcity
   ```

5. [Restart the Agent][5].

<!-- xxz tab xxx -->
<!-- xxx tab "Containerized" xxx -->

#### Containerized

For containerized environments, see the [Autodiscovery Integration Templates][9] for guidance on applying the parameters below.

| Parameter            | Value                                                                                             |
| -------------------- | ------------------------------------------------------------------------------------------------- |
| `<INTEGRATION_NAME>` | `teamcity`                                                                                        |
| `<INIT_CONFIG>`      | blank or `{}`                                                                                     |
| `<INSTANCE_CONFIG>`  | `{"name": "<BUILD_NAME>", "server":"%%host%%", "build_configuration":"<BUILD_CONFIGURATION_ID>"}` |

##### Log collection

Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Kubernetes log collection][10].

| Parameter      | Value                                                |
| -------------- | ---------------------------------------------------- |
| `<LOG_CONFIG>` | `{"source": "teamcity"}` |

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

### Validation

[Run the Agent's `status` subcommand][11] and look for `teamcity` under the Checks section.

## Data Collected

### Metrics

The Teamcity check does not include any metrics.

### Events

Teamcity events representing successful builds are forwarded to Datadog.

### Service Checks

The Teamcity check does not include any service checks.

## Troubleshooting

Need help? Contact [Datadog support][12].

## Further Reading

- [Track performance impact of code changes with TeamCity and Datadog.][13]

[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://confluence.jetbrains.com/display/TCD9/Enabling+Guest+Login
[3]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[4]: https://github.com/DataDog/integrations-core/blob/master/teamcity/datadog_checks/teamcity/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://www.jetbrains.com/help/teamcity/teamcity-server-logs.html
[7]: https://docs.datadoghq.com/logs/log_configuration/pipelines/#integration-pipelines
[8]: https://logging.apache.org/log4j/2.x/manual/layouts.html#Patterns
[9]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[10]: https://docs.datadoghq.com/agent/kubernetes/log/
[11]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[12]: https://docs.datadoghq.com/help/
[13]: https://www.datadoghq.com/blog/track-performance-impact-of-code-changes-with-teamcity-and-datadog
