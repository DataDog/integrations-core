# Agent Check: system cores
{{< img src="integrations/systemcore/syscoredash.png" alt="System Core" responsive="true" popup="true">}}
## Overview

This check collects the number of CPU cores on a host and CPU times (i.e. system, user, idle, etc).

## Setup
### Installation

The system_core check is packaged with the Agent, so simply [install the Agent][1] on any host.

### Configuration

Create a file `system_core.yaml` in the Agent's `conf.d` directory. See the [sample system_core.yaml][2] for all available configuration options:

```
init_config:

instances:
  - foo: bar
```

The Agent just needs one item in `instances` in order to enable the check. The content of the item doesn't matter.

[Restart the Agent][3] to enable the check.

### Validation

[Run the Agent's `status` subcommand][4] and look for `system_core` under the Checks section.

## Data Collected
### Metrics

See [metadata.csv][5] for a list of metrics provided by this check.

Depending on the platform, the check may collect other CPU time metrics, e.g. `system.core.interrupt` on Windows, `system.core.iowait` on Linux, etc.

### Events
The System Core check does not include any event at this time.

### Service Checks
The System Core check does not include any service check at this time.

## Troubleshooting
Need help? Contact [Datadog Support][6].

## Further Reading
Learn more about infrastructure monitoring and all our integrations on [our blog][7]


[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://github.com/DataDog/integrations-core/blob/master/system_core/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[4]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[5]: https://github.com/DataDog/integrations-core/blob/master/system_core/metadata.csv
[6]: http://docs.datadoghq.com/help/
[7]: https://www.datadoghq.com/blog/
