# Agent Check: Teamcity

## Overview

This check watches for build-related events and sends them to Datadog.

Unlike most Agent checks, this one doesn't collect any metrics—just events.

## Setup
### Installation

The Teamcity check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your Teamcity servers.

If you need the newest version of the Teamcity check, install the `dd-check-teamcity` package; this package's check overrides the one packaged with the Agent. See the [integrations-core repository README.md for more details](https://github.com/DataDog/integrations-core#installing-the-integrations).

### Configuration
#### Prepare Teamcity

Follow [Teamcity's documentation](https://confluence.jetbrains.com/display/TCD9/Enabling+Guest+Login) to enable Guest Login.

Create a file `teamcity.yaml` in the Agent's `conf.d` directory. See the [sample teamcity.yaml](https://github.com/DataDog/integrations-core/blob/master/teamcity/conf.yaml.example) for all available configuration options:

```
init_config:

instances:
  - name: My Website
    server: teamcity.mycompany.com
#   server: user:password@teamcity.mycompany.com # if you set basic_http_authentication to true
#   basic_http_authentication: true # default is false
    build_configuration: MyWebsite_Deploy # the internal build ID of the build configuration you wish to track
#   host_affected: msicalweb6 # defaults to hostname of the Agent's host
#   is_deployment: true       # causes events to use the word 'deployment' in their messaging
#   ssl_validation: false     # default is true
#   tags:                     # add custom tags to events
#   - test
```

Add an item like the above to `instances` for each build configuration you want to track.

[Restart the Agent](https://docs.datadoghq.com/agent/faq/start-stop-restart-the-datadog-agent) to start collecting and sending Teamcity events to Datadog.

### Validation

[Run the Agent's `status` subcommand](https://docs.datadoghq.com/agent/faq/agent-status-and-information/) and look for `teamcity` under the Checks section:

```
  Checks
  ======
    [...]

    teamcity
    -------
      - instance #0 [OK]
      - Collected 0 metrics, 3 events & 0 service checks

    [...]
```

## Compatibility

The teamcity check is compatible with all major platforms.

## Data Collected
### Metrics
The Teamcity check does not include any metric at this time.

### Events
All Teamcity events are forwared to your Datadog application.

### Service Checks
The Teamcity check does not include any service check at this time.

## Troubleshooting
Need help? Contact [Datadog Support](http://docs.datadoghq.com/help/).

## Further Reading

* [Track performance impact of code changes with TeamCity and Datadog.](https://www.datadoghq.com/blog/track-performance-impact-of-code-changes-with-teamcity-and-datadog/)
