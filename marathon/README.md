# Marathon Integration

## Overview

The Agent's Marathon check lets you:

* Track the state and health of every application: see configured memory, disk, cpu, and instances; monitor the number of healthy and unhealthy tasks
* Monitor the number of queued applications and the number of deployments

## Setup
### Installation

The Marathon check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your Marathon master. If you need the newest version of the check, install the `dd-check-marathon` package.

### Configuration

Create a file `marathon.yaml` in the Agent's `conf.d` directory:

```
init_config:
  - default_timeout: 5 # how many seconds to wait for Marathon API response

instances:
  - url: https://<server>:<port> # the API endpoint of your Marathon master; required
#   acs_url: https://<server>:<port> # if your Marathon master requires ACS auth
    user: <username> # the user for marathon API or ACS token authentication
    password: <password> # the password for marathon API or ACS token authentication
```

The function of `user` and `password` depends on whether or not you configure `acs_url`; If you do, the Agent uses them to request an authentication token from ACS, which it then uses to authenticate to the Marathon API. Otherwise, the Agent uses `user` and `password` to directly authenticate to the Marathon API.

Restart the Agent to begin sending Marathon metrics to Datadog.

### Validation

Run the Agent's `info` subcommand and look for `marathon` under the Checks section:

```
  Checks
  ======
    [...]

    marathon
    -------
      - instance #0 [OK]
      - Collected 26 metrics, 0 events & 1 service check

    [...]
```

## Compatibility

The marathon check is compatible with all major platforms.

## Data Collected
### Metrics
See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/marathon/metadata.csv) for a list of metrics provided by this integration.

### Events
The Marathon check does not include any event at this time.

### Service Checks

`marathon.can_connect`:

Returns CRITICAL if the Agent cannot connect to the Marathon API to collect metrics, otherwise OK.

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
Learn more about infrastructure monitoring and all our integrations on [our blog](https://www.datadoghq.com/blog/)