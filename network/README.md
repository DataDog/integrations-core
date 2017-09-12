# Network check

## Overview

The network check collects TCP/IP stats from the host operating system.

## Setup
### Installation

The network check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on any host. If you need the newest version of the check, install the `dd-check-network` package.

### Configuration

The Agent enables the network check by default, but if you want to configure the check yourself, create a file `network.yaml` in the Agent's `conf.d` directory:

```
init_config:

instances:
  # Network check only supports one configured instance
  - collect_connection_state: false # set to true to collect TCP connection state metrics, e.g. SYN_SENT, ESTABLISHED
    excluded_interfaces: # the check will collect metrics on all other interfaces
      - lo
      - lo0
# ignore any network interface matching the given regex:
#   excluded_interface_re: eth1.*
```

Restart the Agent to effect any configuration changes.

### Validation

Run the Agent's `info` subcommand and look for `network` under the Checks section:

```
  Checks
  ======
    [...]

    network
    -------
      - instance #0 [OK]
      - Collected 26 metrics, 0 events & 0 service checks

    [...]
```

## Compatibility

The network check is compatible with all major platforms.

## Data Collected
### Metrics
See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/network/metadata.csv) for a list of metrics provided by this check.

### Events
The Network check does not include any event at this time.

### Service Checks
The Network check does not include any service check at this time.

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
### Blog Article
Learn more about infrastructure monitoring and all our integrations on [our blog](https://www.datadoghq.com/blog/)

### Knowledge Base
* [Built a network monitor on an http check](https://help.datadoghq.com/hc/en-us/articles/115003314726-Built-a-network-monitor-on-an-http-check-)
