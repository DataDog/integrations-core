# Linux_proc_extras Integration

## Overview
Get metrics from linux_proc_extras service in real time to:

* Visualize and monitor linux_proc_extras states
* Be notified about linux_proc_extras failovers and events.

## Setup
### Installation

The Linux_proc_extras check is packaged with the Agent, so simply [install the Agent][1] on your servers.

### Configuration

Create a `linux_proc_extras.yaml` file in the Datadog Agent's `conf.d` directory. See the [sample linux_proc_extras.yaml][2] for all available configuration options.

### Validation

[Run the Agent's `status` subcommand][3] and look for `linux_proc_extras` under the Checks section.

## Data Collected
### Metrics
The Linux proc extras check does not include any metric at this time.

### Events
The Linux proc extras check does not include any event at this time.

### Service Checks
The Linux proc extras check does not include any service check at this time.

## Troubleshooting

Need help? Contact [Datadog Support][4].

## Further Reading
Learn more about infrastructure monitoring and all our integrations on [our blog][5]


[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://github.com/DataDog/integrations-core/blob/master/linux_proc_extras/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[4]: http://docs.datadoghq.com/help/
[5]: https://www.datadoghq.com/blog/
