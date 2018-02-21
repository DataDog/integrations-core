# Linux_proc_extras Integration

## Overview
Get metrics from linux_proc_extras service in real time to:

* Visualize and monitor linux_proc_extras states
* Be notified about linux_proc_extras failovers and events.

## Setup
### Installation

The Linux_proc_extras check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your servers.

### Configuration

Edit the `linux_proc_extras.yaml` file to point to your server and port, set the masters to monitor. See the [sample linux_proc_extras.yaml](https://github.com/DataDog/integrations-core/blob/master/linux_proc_extras/conf.yaml.example) for all available configuration options.

### Validation

[Run the Agent's `status` subcommand](https://docs.datadoghq.com/agent/faq/agent-status-and-information/) and look for `linux_proc_extras` under the Checks section:

    Checks
    ======

        linux_proc_extras
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The linux_proc_extras check is compatible with all major platforms

## Data Collected
### Metrics
The Linux proc extras check does not include any metric at this time.

### Events
The Linux proc extras check does not include any event at this time.

### Service Checks
The Linux proc extras check does not include any service check at this time.

## Troubleshooting

Need help? Contact [Datadog Support](http://docs.datadoghq.com/help/).

## Further Reading
Learn more about infrastructure monitoring and all our integrations on [our blog](https://www.datadoghq.com/blog/)
