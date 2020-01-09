# Agent Check: Teamcity

## Overview

This check watches for successful build-related events and sends them to Datadog.

Unlike most Agent checks, this one doesn't collect any metrics-just events.

## Setup
### Installation

The Teamcity check is included in the [Datadog Agent][2] package, so you don't need to install anything else on your Teamcity servers.

### Configuration
#### Prepare Teamcity

Follow [Teamcity's documentation][3] to enable Guest Login.

#### Host

Follow the instructions below to configure this check for an Agent running on a host. For containerized environments, see the [Containerized](#containerized) section.

Edit the `teamcity.d/conf.yaml` in the `conf.d/` folder at the root of your [Agent's configuration directory][4]. See the [sample teamcity.d/conf.yaml][5] for all available configuration options:

```
init_config:

instances:
  - name: My Website
    server: teamcity.mycompany.com
 #  server: user:password@teamcity.mycompany.com # if you set basic_http_authentication to true
 #  basic_http_authentication: true # default is false
    build_configuration: MyWebsite_Deploy # the internal build ID of the build configuration you wish to track
 #  host_affected: msicalweb6 # defaults to hostname of the Agent's host
 #  is_deployment: true       # causes events to use the word 'deployment' in their messaging
 #  tls_verify: false     # default is true
 #  tags:                     # add custom tags to events
 #    - test
```

Add an item like the above to `instances` for each build configuration you want to track.

[Restart the Agent][6] to start collecting and sending Teamcity events to Datadog.

#### Containerized
For containerized environments, see the [Autodiscovery Integration Templates][1] for guidance on applying the parameters below.

| Parameter            | Value                                                                                             |
|----------------------|---------------------------------------------------------------------------------------------------|
| `<INTEGRATION_NAME>` | `teamcity`                                                                                        |
| `<INIT_CONFIG>`      | blank or `{}`                                                                                     |
| `<INSTANCE_CONFIG>`  | `{"name": "<BUILD_NAME>", "server":"%%host%%", "build_configuration":"<BUILD_CONFIGURATION_ID>"}` |

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

* [Track performance impact of code changes with TeamCity and Datadog.][9]


[1]: https://docs.datadoghq.com/agent/autodiscovery/integrations
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://confluence.jetbrains.com/display/TCD9/Enabling+Guest+Login
[4]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[5]: https://github.com/DataDog/integrations-core/blob/master/teamcity/datadog_checks/teamcity/data/conf.yaml.example
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[7]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[8]: https://docs.datadoghq.com/help
[9]: https://www.datadoghq.com/blog/track-performance-impact-of-code-changes-with-teamcity-and-datadog
