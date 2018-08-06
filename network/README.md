# Network check

![Network Dashboard][9]

## Overview

The network check collects TCP/IP stats from the host operating system.

## Setup
### Installation

The network check is included in the [Datadog Agent][1] package, so you don't need to install anything else on your server.

### Configuration

1. The Agent enables the network check by default, but if you want to configure the check yourself, edit file `network.d/conf.yaml`, in the `conf.d/` folder at the root of your [Agent's configuration directory][10].
  See the [sample network.d/conf.yaml][2] for all available configuration options:

    ```yaml
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

2. [Restart the Agent][3] to effect any configuration changes.

### Validation

[Run the Agent's `status` subcommand][4] and look for `network` under the Checks section.

## Data Collected
### Metrics
See [metadata.csv][5] for a list of metrics provided by this integration.

### Events
The Network check does not include any events at this time.

### Service Checks
The Network check does not include any service checks at this time.

## Troubleshooting

* [How to send TCP/UDP host metrics via the Datadog API ?][6]

## Further Reading

* [Built a network monitor on an http check][8]


[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://github.com/DataDog/integrations-core/blob/master/network/datadog_checks/network/data/conf.yaml.default
[3]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[4]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[5]: https://github.com/DataDog/integrations-core/blob/master/network/metadata.csv
[6]: https://docs.datadoghq.com/integrations/faq/how-to-send-tcp-udp-host-metrics-via-the-datadog-api
[8]: https://docs.datadoghq.com/monitors/monitor_types/network
[9]: https://raw.githubusercontent.com/DataDog/integrations-core/master/network/images/netdashboard.png
[10]: https://docs.datadoghq.com/agent/faq/agent-configuration-files/#agent-configuration-directory
