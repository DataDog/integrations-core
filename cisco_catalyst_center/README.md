# Agent Check: cisco_catalyst_center

## Overview

This check monitors [cisco_catalyst_center][1] through the Datadog Agent.

Include a high level overview of what this integration does:
- What does your product do (in 1-2 sentences)?
- What value will customers get from this integration, and why is it valuable to them?
- What specific data will your integration monitor, and what's the value of that data?

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery integration templates][3] for guidance on applying these instructions.

### Installation

The cisco_catalyst_center check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

### Configuration

1. Edit the `cisco_catalyst_center.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your cisco_catalyst_center performance data. See the [sample cisco_catalyst_center.d/conf.yaml][4] for all available configuration options.

2. [Restart the Agent][5].

### Event collection

Set `collect_events: true` in `cisco_catalyst_center.d/conf.yaml` to collect Catalyst Center
assurance events. Each cycle polls the window since the previous one, so an event is submitted
exactly once.

Polling costs four requests per cycle at minimum, delays each event by up to one collection
interval, and submits at most 800 events per cycle. Events that occur while the Agent is stopped for
more than seven days cannot be recovered, because that is the widest window the endpoint serves.

If Catalyst Center is already configured to notify Datadog directly, leave this disabled. Both paths
carry the same events, so enabling both submits everything twice.

### Validation

[Run the Agent's status subcommand][6] and look for `cisco_catalyst_center` under the Checks section.

## Data collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

When `collect_events` is enabled, the cisco_catalyst_center integration submits each Catalyst Center
assurance event as a Datadog event. The title is the event name, the body carries the reason,
sub-reason, failure category and result reported by the appliance, and the alert type is derived from
the event's syslog severity: Emergency through Error become errors, Warning becomes a warning, and
Notice and Info become informational.

Events are tagged with severity, device family, event name, device name, site and SSID. Per-client
identifiers appear in the event body rather than as tags.

### Service checks

See [service_checks.json][8] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][9].


[1]: **LINK_TO_INTEGRATION_SITE**
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/containers/kubernetes/integrations/
[4]: https://github.com/DataDog/integrations-core/blob/master/cisco_catalyst_center/datadog_checks/cisco_catalyst_center/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/configuration/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/configuration/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/cisco_catalyst_center/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/cisco_catalyst_center/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
