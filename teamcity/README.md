# Agent Check: Teamcity

## Overview

This check watches for build-related events and sends them to Datadog.

Unlike most Agent checks, this one doesn't collect any metrics—just events.

## Setup
### Installation

The Teamcity check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your Teamcity servers. If you need the newest version of the check, install the `dd-check-teamcity` package.

### Configuration
#### Prepare Teamcity

Follow [Teamcity's documentation](https://confluence.jetbrains.com/display/TCD9/Enabling+Guest+Login) to enable Guest Login. 

Create a file `teamcity.yaml` in the Agent's `conf.d` directory:

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

Restart the Agent to start collecting and sending Teamcity events to Datadog.

### Validation

Run the Agent's `info` subcommand and look for `teamcity` under the Checks section:

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
See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/teamcity/metadata.csv) for a list of metrics provided by this integration.

### Events
All Teamcity events are forwared to your Datadog application.

### Service Checks
The Teamcity check does not include any service check at this time.

## Troubleshooting

If you have any questions about Datadog or a use case our [Docs](https://docs.datadoghq.com/) didn’t mention, we’d love to help! Here’s how you can reach out to us:

### Visit the Knowledge Base

Learn more about what you can do in Datadog on the [Support Knowledge Base](https://datadog.zendesk.com/agent/).

### Web Support

Messages in the [event stream](https://app.datadoghq.com/event/stream) containing **@support-datadog** will reach our Support Team. This is a convenient channel for referencing graph snapshots or a particular event. In addition, we have a livechat service available during the day (EST) from any page within the app.

### By Email

You can also contact our Support Team via email at [support@datadoghq.com](mailto:support@datadoghq.com).

### Over Slack

Reach out to our team and other Datadog users on [Slack](http://chat.datadoghq.com/).

## Further Reading
To get a better idea of how (or why) to track performance impact of code changes with TeamCity and Datadog, check out our [series of blog posts](https://www.datadoghq.com/blog/track-performance-impact-of-code-changes-with-teamcity-and-datadog/) about it.
