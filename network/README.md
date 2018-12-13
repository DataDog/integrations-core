# Network check

![Network Dashboard][1]

## Overview

The network check collects TCP/IP stats from the host operating system.

## Setup
### Installation

The network check is included in the [Datadog Agent][2] package, so you don't need to install anything else on your server.

### Configuration

1. The Agent enables the network check by default, but if you want to configure the check yourself, edit file `network.d/conf.yaml`, in the `conf.d/` folder at the root of your [Agent's configuration directory][3].
  See the [sample network.d/conf.yaml][4] for all available configuration options:

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

2. [Restart the Agent][5] to effect any configuration changes.

### Validation

[Run the Agent's `status` subcommand][6] and look for `network` under the Checks section.

## Data Collected
### Metrics
See [metadata.csv][7] for a list of metrics provided by this integration.

### Events
The Network check does not include any events at this time.

### Service Checks
The Network check does not include any service checks at this time.

## Troubleshooting

* [How to send TCP/UDP host metrics via the Datadog API ?][8]

## Further Reading

* [Built a network monitor on an http check][9]


[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/network/images/netdashboard.png
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://docs.datadoghq.com/agent/faq/agent-configuration-files/#agent-configuration-directory
[4]: https://github.com/DataDog/integrations-core/blob/master/network/datadog_checks/network/data/conf.yaml.default
[5]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[6]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/network/metadata.csv
[8]: https://docs.datadoghq.com/integrations/faq/how-to-send-tcp-udp-host-metrics-via-the-datadog-api
[9]: https://docs.datadoghq.com/monitors/monitor_types/network
