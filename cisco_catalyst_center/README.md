# Agent Check: Cisco Catalyst Center

## Overview

This check monitors [Cisco Catalyst Center][1] through the Datadog Agent.

Cisco Catalyst Center (formerly DNA Center) is Cisco's platform for managing and monitoring enterprise campus and branch networks. This integration connects to the Catalyst Center API to collect device inventory, network assurance health, and topology data, giving you visibility into your Cisco campus network from within Datadog.

The integration provides:

- **Device and interface inventory**: Reachability, hardware, and interface details for switches, routers, wireless controllers, and access points, with optional Network Device Monitoring metadata for pairing with the SNMP integration.
- **Assurance health**: Site, network, and client health scores, plus traffic and performance for the busiest applications at each site.
- **Assurance issues and events**: Optional counts of open assurance issues and of assurance events, with each one also submitted as a Datadog event.
- **Topology**: Physical (CDP/LLDP), site, and layer 3 topology sizing.
- **SD-Access and security**: Fabric and virtual network health, plus rogue access point and aWIPS wireless intrusion counts.

The integration also includes two dashboards, **Cisco Catalyst Center Overview** and **Cisco Catalyst Center Devices and Interfaces**, and four recommended monitors for collection failures, unreachable devices, degraded network health, and poor SD-Access fabric health.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery integration templates][3] for guidance on applying these instructions.

### Prerequisites

Before you configure the check, make sure that:

- Your appliance runs Catalyst Center 2.3.7 or later. The integration reads the Catalyst Center Assurance data API.
- You have a Catalyst Center account with API access for the Agent to use. The OBSERVER role is enough, because the check only reads data.
- The Agent host can reach the appliance over HTTPS on port 443.

### Installation

The Cisco Catalyst Center check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

### Configuration

1. Edit the `cisco_catalyst_center.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory, to start collecting your Cisco Catalyst Center data. Only the appliance host and the account credentials are required:

   ```yaml
   init_config:

   instances:
     - catalyst_center_host: catalyst-center.example.com
       catalyst_center_username: <USERNAME>
       catalyst_center_password: <PASSWORD>
   ```

   Enter the host without a scheme. The check always uses HTTPS. See the [sample cisco_catalyst_center.d/conf.yaml][4] for all available configuration options, including TLS verification settings for appliances that use a self-signed certificate.

2. [Restart the Agent][5].

### Optional collectors

The check always collects device inventory and health, network health, and client health. The other collectors are controlled by options in `cisco_catalyst_center.d/conf.yaml`:

| Option | Default | What it collects |
| --- | --- | --- |
| `collect_interfaces` | Enabled | Interface status and configuration |
| `collect_interface_statistics` | Enabled | Interface throughput, errors, and discards, plus per-device throughput and uplink totals |
| `collect_interface_poe` | Disabled | Per-port Power over Ethernet (PoE) state and power draw |
| `collect_site_health` | Enabled | Per-site health scores and device, client, and issue counts |
| `collect_client_experience` | Enabled | Client signal quality and onboarding times by SSID and band |
| `collect_stacks` | Disabled | Switch stack membership and member health |
| `collect_topology` | Disabled | Physical, site, and layer 3 topology sizes |
| `collect_sda_fabric` | Disabled | SD-Access fabric health, virtual network health, and device counts by fabric role |
| `collect_assurance_issues` | Disabled | Open assurance issues, as counts and as Datadog events |
| `collect_events` | Disabled | Assurance events, as counts and as Datadog events |
| `collect_application_health` | Disabled | Health and traffic for the 100 busiest applications at each site |
| `collect_security` | Disabled | Rogue access point and aWIPS threat counts |
| `collect_wireless` | Disabled | Access point radio metrics, which have not yet been validated against a live wireless controller |

Most collectors make a fixed number of requests per cycle. Three scale with the size of your deployment: site health makes one request per 20 sites, switch stacks make one request per stackable switch, and application health makes one request per site.

### Event collection

Set `collect_events: true` in `cisco_catalyst_center.d/conf.yaml` to collect Catalyst Center
assurance events. Each cycle polls the window since the previous one, so an event is submitted once
per continuous Agent run.

The resume point is kept in memory, not on disk: restarting the Agent forgets it, and the next cycle
falls back to polling `events_initial_lookback_minutes` again. Events already reported before the
restart that still fall inside that window are submitted a second time. The metrics `cisco_catalyst_center.event.count`
and `cisco_catalyst_center.event.total.count` have no protection against this and double-count that window.

Events can also be lost rather than duplicated. If one device family's request fails, or a sweep is
cut short by the per-cycle page budget, the window still advances without a retry. Those events are
gone rather than double-counted.

Polling costs four requests per cycle at minimum, delays each event by up to one collection
interval, and submits at most 800 events per cycle. Events that occur while the Agent is stopped for
more than seven days cannot be recovered, because that is the widest window the endpoint serves.

If Catalyst Center is already configured to notify Datadog directly, leave this disabled. Both paths
carry the same events, so enabling both submits everything twice.

### Assurance issue collection

Set `collect_assurance_issues: true` in `cisco_catalyst_center.d/conf.yaml` to collect open assurance issues. Every cycle reports how many issues are open, broken down by severity, priority, category, and status.

Each issue is also submitted as a Datadog event the first time the check sees it, and again whenever it recurs. The check remembers which issues it reported only while the Agent is running, so after a restart every open issue is reported again.

### Network Device Monitoring

Set `send_ndm_metadata: true` in `cisco_catalyst_center.d/conf.yaml` to send device and interface
metadata to [Network Device Monitoring][9] (NDM).

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
assurance event as a Datadog event. The title is the event name, and the body carries the reason,
sub-reason, failure category, and result reported by the appliance.

The alert type is derived from the event's syslog severity:

- Emergency through Error become errors
- Warning becomes a warning
- Notice and Info become informational

Events are tagged with severity, device family, event name, device name, site, and SSID. Per-client
identifiers appear in the event body rather than as tags.

When `collect_assurance_issues` is enabled, the integration also submits assurance issues as Datadog events. The title is the issue name, and the body carries the summary, description, suggested actions, device type, site, and affected entity reported by the appliance. The alert type is derived from the issue's priority, which runs from P1, the most severe, to P4:

- P1 and P2 become errors
- P3 becomes a warning
- P4 becomes informational

Issue events are tagged with severity, priority, category, and status.

### Service checks

The Cisco Catalyst Center integration does not include any service checks. To alert on collection
failures, use the `cisco_catalyst_center.collection.success` metric: it is 1 when every enabled
collector completed a cycle and 0 when any of them failed, and it is submitted on failed cycles as
well as successful ones.

## Troubleshooting

### Collection is failing

When the `cisco_catalyst_center.collection.success` metric reports 0, at least one enabled collector failed during the cycle. The Agent log names the collector in a line such as `Catalyst Center site health collection failed`. Errors that Catalyst Center reports carry its `x-correlation-id` value, which Cisco Technical Assistance Center (TAC) asks for when investigating a failed API call.

If `cisco_catalyst_center.device.count` is still being reported, the appliance is reachable and the credentials work, so the failure is in a later collector.

### Authentication errors

The check requests a token with the configured account and renews it before it expires. If Catalyst Center rejects the token twice for the same request, the Agent log reports `Catalyst Center rejected authentication twice` and that collector is skipped for the cycle. Check the username and password, and confirm that the account has API access.

### Rate limiting

Catalyst Center enforces rate limits per API endpoint and answers with HTTP 429 when one is exceeded. The check makes up to three attempts for a throttled request. Between attempts, it waits as long as the appliance's `Retry-After` header asks, up to 30 seconds, or backs off on its own when the header is absent.

If requests keep failing, reduce the load in this order:

1. Disable `collect_interface_statistics`, which removes a full sweep of every interface from each cycle.
2. Disable `collect_application_health` or `collect_stacks`, whose cost grows with the number of sites and switches.
3. Raise `min_collection_interval`. Catalyst Center recomputes assurance health about every 5 minutes, so collecting more often does not produce fresher health scores.

### Empty dashboard widgets

Widgets for optional collectors stay empty until you enable the matching option. The dashboard groups for those collectors are labeled "Opt-In".

### Help

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
