# Agent Check: TeamCity

## Overview

This integration connects to your TeamCity server to submit metrics, service checks, and events allowing you to monitor the health of your TeamCity projects' build configurations, build runs, server resources and more.

## Setup

### Installation

The TeamCity check is included in the [Datadog Agent][1] package, so you don't need to install anything else on your TeamCity servers.

### Configuration

#### Prepare TeamCity

1. To prepare TeamCity, see [Enabling Guest Login][2].
2. To collect metrics, enable `Per-project permissions` and assign the `View Usage Statistics` permission to the Guest user.

<!-- xxx tabs xxx -->
<!-- xxx tab "Host" xxx -->

#### Host

To configure this check for an Agent running on a host:

Edit the `teamcity.d/conf.yaml` in the `conf.d/` folder at the root of your [Agent's configuration directory][3]. See the [sample teamcity.d/conf.yaml][4] for all available configuration options:

The TeamCity check offers two methods of data collection. Configure two separate instances to collect metrics from each method to optimally monitor your TeamCity environment. 

1. OpenMetricsV2 Method:

   Enable `use_openmetrics: true` to collect metrics from the TeamCity `/metrics` Prometheus endpoint.


   ```yaml
   init_config:
   
   instances:
       ## @param server - string - required
       ## Specify the server name of your TeamCity instance.
       ## Enable Guest Authentication on your instance or enable the
       ## optional `basic_http_authentication` config param to collect data.
       ## If using `basic_http_authentication`, specify:
       ##
       ## server: http://<USER>:<PASSWORD>@teamcity.<ACCOUNT_NAME>.com
       #
     - server: http://teamcity.<ACCOUNT_NAME>.com
       ## @param use_openmetrics - boolean - optional - default: false
       ## Use the latest OpenMetrics V2 implementation to collect metrics from
       ## the TeamCity server's prometheus metrics endpoint.
       ## Requires Python version 3.
       ##
       ## Enable in a separate instance to collect prometheus metrics.
       ## This option does not collect events, service checks, or metrics from the TeamCity REST API.
       #
       use_openmetrics: true
   ```

2. TeamCity Server REST API Method:

   Configure a separate instance in the `teamcity.d/conf.yaml` file to collect additional build-specific metrics, service checks, and build status events from the TeamCity Server's REST API. Specify your projects and build configurations using the `projects` option:


   ```yaml
   init_config:
   
   instances:
     - server: http://teamcity.<ACCOUNT_NAME>.com
   
       ## @param projects - mapping - optional
       ## Mapping of TeamCity projects and build configurations to
       ## collect events and metrics from the TeamCity REST API.
       #
       projects:
         <PROJECT_A>:
           include:    
           - <BUILD_CONFIG_A>
           - <BUILD_CONFIG_B>
           exclude:
           - <BUILD_CONFIG_C>
         <PROJECT_B>:
           include:
           - <BUILD_CONFIG_D>
         <PROJECT_C>: {}
   ```


   Customize each project's build configuration monitoring using the optional `include` and `exclude` filters to specify build configuration IDs to include or exclude from monitoring, respectively. Regex patterns are supported in the `include` and `exclude` keys to specify build configuration ID matching patterns. If both `include` and `exclude` filters are omitted, all build configurations are monitored for the specified project. 


[Restart the Agent][5] to start collecting and sending TeamCity events to Datadog.

##### Log collection

1. Configure TeamCity [logs settings][6].

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
| `<INSTANCE_CONFIG>`  | `{"server": "%%host%%", "use_openmetrics": "true"}`                                               |

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

See [metadata.csv][14] for a list of metrics provided by this check.

### Events

TeamCity events representing successful and failed builds are forwarded to Datadog.

### Service Checks

See [service_checks.json][15] for a list of service checks provided by this integration.

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
[7]: https://docs.datadoghq.com/logs/processing/#integration-pipelines
[8]: https://logging.apache.org/log4j/2.x/manual/layouts.html#Patterns
[9]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[10]: https://docs.datadoghq.com/agent/kubernetes/log/
[11]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[12]: https://docs.datadoghq.com/help/
[13]: https://www.datadoghq.com/blog/track-performance-impact-of-code-changes-with-teamcity-and-datadog
[14]: https://github.com/DataDog/integrations-core/blob/master/teamcity/metadata.csv
[15]: https://github.com/DataDog/integrations-core/blob/master/teamcity/assets/service_checks.json