# Agent Check: Twistlock

## Overview

[Twistlock][1] is a security scanner. It scans containers, hosts and packages to find vulnerabilities and compliance issues.

## Setup

### Installation

The Twistlock check is included in the [Datadog Agent][2] package, so you do not need to install anything else on your server.

### Configuration

Edit the `twistlock.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your twistlock performance data. See the [sample twistlock.d/conf.yaml][2] for all available configuration options.

If you're using Kubernetes, add the config to the Twistlock Console.

[Restart the Agent][3]

### Validation

[Run the Agent's `status` subcommand][4] and look for `twistlock` under the Checks section.

#### Log Collection

**Available for Agent >6.0**

Collecting logs is disabled by default in the Datadog Agent, enable it in the `datadog.yaml` file with:

```yaml
logs_enabled: true
```

##### Kubernetes



##### Docker

If you're running on docker, uncomment this block in your `twistlock.d/conf.yaml` file to start collecting your Twistlock logs:

```yaml
logs:
  - type: docker
    image: twistlock/private
    source: twistlock
    service: twistlock
```

[Restart the Agent][3] to begin sending Twistlock logs to Datadog.

**Learn more about log collection [in the log documentation][7]**


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
[7]: https://docs.datadoghq.com/logs
