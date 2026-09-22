# Agent Check: Cisco Catalyst Center

## Overview

This check monitors [Cisco Catalyst Center][1] through the Datadog Agent.

Cisco Catalyst Center (formerly DNA Center) is Cisco's platform for managing and monitoring
enterprise campus and branch networks. This integration connects to the Catalyst Center API to
collect device inventory, network assurance health, and topology data, giving you visibility into
your Cisco campus network from within Datadog.

The integration provides:

- **Device and interface inventory**: reachability, hardware, and interface details for switches, routers, wireless controllers, and access points, with optional Network Device Monitoring metadata for pairing with the SNMP integration.
- **Assurance health**: site, network, and client health scores, plus per-application traffic and performance.
- **Assurance issues and events**: counts of open issues and, optionally, individual assurance events as Datadog events.
- **Topology**: physical (CDP/LLDP), site, and layer 3 topology sizing.
- **SD-Access and security**: fabric and virtual network health, plus rogue access point and aWIPS wireless intrusion counts.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery integration templates][3] for guidance on applying these instructions.

### Installation

The Cisco Catalyst Center check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

### Configuration

1. Edit the `cisco_catalyst_center.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your Cisco Catalyst Center performance data. See the [sample cisco_catalyst_center.d/conf.yaml][4] for all available configuration options.

2. [Restart the Agent][5].

### Event collection

Set `collect_events: true` in `cisco_catalyst_center.d/conf.yaml` to collect Catalyst Center
assurance events. Each cycle polls the window since the previous one, so an event is submitted once
per continuous Agent run.

The resume point is kept in memory, not on disk: restarting the Agent forgets it, and the next cycle
falls back to polling `events_initial_lookback_minutes` again. Events already reported before the
restart that still fall inside that window are submitted a second time. The `cisco_catalyst_center.event.count`
and `.event.total.count` metrics have no protection against this and double-count that window.

Polling costs four requests per cycle at minimum, delays each event by up to one collection
interval, and submits at most 800 events per cycle. Events that occur while the Agent is stopped for
more than seven days cannot be recovered, because that is the widest window the endpoint serves.

If Catalyst Center is already configured to notify Datadog directly, leave this disabled. Both paths
carry the same events, so enabling both submits everything twice.

### Network Device Monitoring

Set `send_ndm_metadata: true` in `cisco_catalyst_center.d/conf.yaml` to send device, interface, and
topology metadata to [Network Device Monitoring][9] (NDM).

The `namespace` option must match the namespace configured on the SNMP check polling the same
devices. If the two differ, Catalyst Center and SNMP resolve to different NDM devices instead of
merging into one, and neither integration reports it: the symptom is two half-populated devices in
the NDM device list rather than an error.

### Validation

[Run the Agent's status subcommand][6] and look for `cisco_catalyst_center` under the Checks section.

## Data collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

When `collect_events` is enabled, the Cisco Catalyst Center integration submits each Catalyst Center
assurance event as a Datadog event. The title is the event name, the body carries the reason,
sub-reason, failure category and result reported by the appliance, and the alert type is derived from
the event's syslog severity: Emergency through Error become errors, Warning becomes a warning, and
Notice and Info become informational.

Events are tagged with severity, device family, event name, device name, site and SSID. Per-client
identifiers appear in the event body rather than as tags.

### Service checks

The Cisco Catalyst Center integration does not include any service checks. To alert on collection
failures, use the `cisco_catalyst_center.collection.success` metric: it is 1 when every enabled
collector completed a cycle and 0 when any of them failed, and it is submitted on failed cycles as
well as successful ones.

## Troubleshooting

Need help? Contact [Datadog support][8].


[1]: https://www.cisco.com/site/us/en/products/networking/catalyst-center/index.html
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/containers/kubernetes/integrations/
[4]: https://github.com/DataDog/integrations-core/blob/master/cisco_catalyst_center/datadog_checks/cisco_catalyst_center/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/configuration/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/configuration/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/cisco_catalyst_center/metadata.csv
[8]: https://docs.datadoghq.com/help/
[9]: https://docs.datadoghq.com/network_monitoring/devices/setup
