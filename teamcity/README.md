# Agent Check: Teamcity

## Overview

This check watches for successful build-related events and sends them to Datadog.

Unlike most Agent checks, this one doesn't collect any metrics-just events.

## Setup
### Installation

The Teamcity check is included in the [Datadog Agent][1] package, so you don't need to install anything else on your Teamcity servers.

### Configuration
#### Prepare Teamcity

Follow [Teamcity's documentation][2] to enable Guest Login.

Edit the `teamcity.d/conf.yaml` in the `conf.d/` folder at the root of your [Agent's configuration directory][8]. See the [sample teamcity.d/conf.yaml][3] for all available configuration options:

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
 #  ssl_validation: false     # default is true
 #  tags:                     # add custom tags to events
 #    - test
```

Add an item like the above to `instances` for each build configuration you want to track.

[Restart the Agent][4] to start collecting and sending Teamcity events to Datadog.

### Validation

[Run the Agent's `status` subcommand][5] and look for `teamcity` under the Checks section.

## Data Collected
### Metrics
The Teamcity check does not include any metrics at this time.

### Events
Teamcity events representing successful builds are forwarded to your Datadog application.

### Service Checks
The Teamcity check does not include any service checks at this time.

## Troubleshooting
Need help? Contact [Datadog Support][6].

## Further Reading

* [Track performance impact of code changes with TeamCity and Datadog.][7]


[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://confluence.jetbrains.com/display/TCD9/Enabling+Guest+Login
[3]: https://github.com/DataDog/integrations-core/blob/master/teamcity/datadog_checks/teamcity/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[5]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[6]: https://docs.datadoghq.com/help/
[7]: https://www.datadoghq.com/blog/track-performance-impact-of-code-changes-with-teamcity-and-datadog/
[8]: https://docs.datadoghq.com/agent/faq/agent-configuration-files/#agent-configuration-directory
