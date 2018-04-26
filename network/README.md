# Network check
{{< img src="integrations/network/netdashboard.png" alt="Network Dashboard" responsive="true" popup="true">}}
## Overview

The network check collects TCP/IP stats from the host operating system.

## Setup
### Installation

The network check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on any host.

### Configuration

The Agent enables the network check by default, but if you want to configure the check yourself, create a file `network.yaml` in the Agent's `conf.d` directory. See the [sample network.yaml](https://github.com/DataDog/integrations-core/blob/master/network/conf.yaml.default) for all available configuration options:

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

[Restart the Agent](https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent) to effect any configuration changes.

### Validation

[Run the Agent's `status` subcommand](https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information) and look for `network` under the Checks section.

## Data Collected
### Metrics
See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/network/metadata.csv) for a list of metrics provided by this integration.

### Events
The Network check does not include any event at this time.

### Service Checks
The Network check does not include any service check at this time.

## Troubleshooting

* [How to send TCP/UDP host metrics via the Datadog API ?](https://docs.datadoghq.com/integrations/faq/how-to-send-tcp-udp-host-metrics-via-the-datadog-api)

## Further Reading
### Datadog Blog
Learn more about infrastructure monitoring and all our integrations on [our blog](https://www.datadoghq.com/blog/)

### Knowledge Base
* [Built a network monitor on an http check](https://docs.datadoghq.com/monitors/monitor_types/network)
