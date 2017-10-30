# Wmi_check Integration

## Overview

Get metrics from wmi_check service in real time to:

* Visualize and monitor wmi_check states
* Be notified about wmi_check failovers and events.

## Setup
### Installation

Install the `dd-check-wmi_check` package manually or with your favorite configuration manager

### Configuration

Edit the `wmi_check.yaml` file to point to your server and port, set the masters to monitor. See the [sample wmi_check.yaml](https://github.com/DataDog/integrations-core/blob/master/wmi_check/conf.yaml.example) for all available configuration options.

### Validation

[Run the Agent's `info` subcommand](https://help.datadoghq.com/hc/en-us/articles/203764635-Agent-Status-and-Information) and look for `wmi_check` under the Checks section:

    Checks
    ======

        wmi_check
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The wmi_check check is compatible with all major platforms

## Data Collected
### Metrics
See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/wmi_check/metadata.csv) for a list of metrics provided by this integration.

### Events
The WMI check does not include any event at this time.

### Service Checks
The WMI check does not include any service check at this time.

## Troubleshooting
Need help? Contact [Datadog Support](http://docs.datadoghq.com/help/).

## Further Reading
Learn more about infrastructure monitoring and all our integrations on [our blog](https://www.datadoghq.com/blog/)