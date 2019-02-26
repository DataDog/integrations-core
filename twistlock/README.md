# Agent Check: Twistlock

## Overview

[Twistlock][1] is a security scanner. It scans containers, hosts and packages to find vulnerabilities and compliance issues.

## Setup

### Installation

The Twistlock check is included in the [Datadog Agent][2] package, so you do not
need to install anything else on your server.

### Configuration

1. Edit the `twistlock.d/conf.yaml` file, in the `conf.d/` folder at the root of your
   Agent's configuration directory to start collecting your twistlock performance data.
   See the [sample twistlock.d/conf.yaml][2] for all available configuration options.

2. [Restart the Agent][3]

### Validation

[Run the Agent's `status` subcommand][4] and look for `twistlock` under the Checks section.

## Data Collected

### Metrics

Twistlock collects metrics on compliance and vulnerabilities. Look in the [metadata.csv][6] to see more

### Service Checks

Twistlock sends service checks when a scan fails.

### Events

Twistlock sends an event when a new CVE is found.

## Troubleshooting

Need help? Contact [Datadog support][5].

[1]: https://www.twistlock.com/
[2]: https://github.com/DataDog/integrations-core/blob/master/twistlock/datadog_checks/twistlock/data/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[4]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[5]: https://docs.datadoghq.com/help/
[6]: https://github.com/DataDog/integrations-core/blob/master/twistlock/metadata.csv
