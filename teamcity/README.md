# Agent Check: Teamcity

## Overview

This check watches for successful build-related events and sends them to Datadog.

Unlike most Agent checks, this one doesn't collect any metrics—just events.

## Setup

### Installation

The Teamcity check is included in the [Datadog Agent][2] package, so you don't need to install anything else on your Teamcity servers.

### Configuration

#### Prepare Teamcity

Follow [Teamcity's documentation][3] to enable Guest Login.

<!-- xxx tabs xxx -->
<!-- xxx tab "Host" xxx -->

#### Host

To configure this check for an Agent running on a host:

Edit the `teamcity.d/conf.yaml` in the `conf.d/` folder at the root of your [Agent's configuration directory][4]. See the [sample teamcity.d/conf.yaml][5] for all available configuration options:

```yaml
init_config:

instances:
  - name: My Website
    server: teamcity.mycompany.com

    # the internal build ID of the build configuration you wish to track
    build_configuration: MyWebsite_Deploy
```

Add an item like the above to `instances` for each build configuration you want to track.

[Restart the Agent][6] to start collecting and sending Teamcity events to Datadog.

##### Log collection

1. Configure Teamcity [logs settings][11].

2. By default, Datadog's integration pipeline supports the following kind of log format:

   ```text
   [2020-09-10 21:21:37,486]   INFO -  jetbrains.buildServer.STARTUP - Current stage: System is ready
   ```

   Clone and edit the [integration pipeline][12] if you defined different conversion [patterns][13].

3. Collecting logs is disabled by default in the Datadog Agent. Enable it in your `datadog.yaml` file:

   ```yaml
   logs_enabled: true
   ```

4. Uncomment the following configuration block in your `teamcity.d/conf.yaml` file. Change the `path` parameter value based on your environment. See the [sample teamcity.d/conf.yaml][5] for all available configuration options.

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

5. [Restart the Agent][6].

<!-- xxz tab xxx -->
<!-- xxx tab "Containerized" xxx -->

#### Containerized

For containerized environments, see the [Autodiscovery Integration Templates][1] for guidance on applying the parameters below.

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

[Run the Agent's `status` subcommand][7] and look for `teamcity` under the Checks section.

## Data Collected

### Metrics

The Teamcity check does not include any metrics.

### Events

Teamcity events representing successful builds are forwarded to your Datadog application.

### Service Checks

The Teamcity check does not include any service checks.

## Troubleshooting

Need help? Contact [Datadog support][8].

## Further Reading

- [Track performance impact of code changes with TeamCity and Datadog.][9]

[1]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://confluence.jetbrains.com/display/TCD9/Enabling+Guest+Login
[4]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[5]: https://github.com/DataDog/integrations-core/blob/master/teamcity/datadog_checks/teamcity/data/conf.yaml.example
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[7]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[8]: https://docs.datadoghq.com/help/
[9]: https://www.datadoghq.com/blog/track-performance-impact-of-code-changes-with-teamcity-and-datadog
[10]: https://docs.datadoghq.com/agent/kubernetes/log/
[11]: https://www.jetbrains.com/help/teamcity/teamcity-server-logs.html
[12]: https://docs.datadoghq.com/logs/processing/#integration-pipelines
[13]: https://logging.apache.org/log4j/2.x/manual/layouts.html#Patterns
