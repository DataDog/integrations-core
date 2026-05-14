# Agent Check: HPE Aruba EdgeConnect

## Overview

This check monitors [HPE Aruba EdgeConnect][1] through the Datadog Agent.

HPE Aruba EdgeConnect is an SD-WAN platform used to connect branch offices, data centers, and cloud environments through an overlay of secure tunnels managed centrally by an Orchestrator. This integration authenticates against the Orchestrator and the individual EdgeConnect appliances, collects health and performance metrics from each appliance's REST API and minute-stats archives, and reports the topology of the SD-WAN fabric (devices, interfaces, and tunnels) to Network Device Monitoring (NDM).

### What this integration monitors

The integration collects metrics across multiple layers of the EdgeConnect SD-WAN fabric, including:

- **Orchestrator and appliance inventory**: Discovers all EdgeConnect appliances managed by the Orchestrator. Surfaces reachability status, uptime, hostname, site, model, and software version.
- **Appliance health**: Reports CPU, memory, and disk usage percentages, as well as hardware alarm state, to detect overloaded or failing devices.
- **Network interfaces**: Provides administrative and operational status, configured speed, RX/TX bandwidth and rate, peak and average utilization, and forward-drop counters per interface.
- **SD-WAN tunnels**: Reports per-tunnel latency, jitter, packet loss (pre- and post-FEC), Mean Opinion Score (MOS) for voice-quality tracking, downtime during the interval, and bidirectional throughput in both bits and packets per second. Allows detection of path degradation and SLA violations across the overlay.
- **Internet breakout tunnels**: Monitors RX/TX bandwidth, peak rates, and configured maximum throughput on local-internet breakout tunnels to observe direct-to-cloud traffic.
- **QoS and traffic shaping**: Tracks per-DSCP-class bandwidth and rate counters, shaper drop counts, and drop percentages. Useful for validating QoS policies and spotting classes being starved or over-subscribed.
- **Circuit SLA probes**: Reports average latency, jitter, and packet loss from SLA probes, plus next-hop administrative and operational status, to monitor underlay link quality independently of the overlay.
- **Application performance**: Provides per-application latency, enabling drill-down from tunnel or interface issues to the specific affected applications.
- **Network Device Monitoring topology**: Pushes device, interface, and tunnel metadata to NDM, enabling visualization of the SD-WAN fabric and correlation with the rest of the network.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][3] for guidance on applying these instructions.

### Installation

The HPE Aruba EdgeConnect check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

### Configuration

1. Edit the `hpe_aruba_edgeconnect.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your HPE Aruba EdgeConnect performance data. See the [sample hpe_aruba_edgeconnect.d/conf.yaml][4] for all available configuration options.

   **Note**: Admin permissions are required to collect the `hpe_aruba_edgeconnect.device.cpu.usage` metric on the appliances. If the configured credentials do not have admin access, this metric will be skipped, but the rest of the metrics will still be collected.

2. [Restart the Agent][5].

### Validation

[Run the Agent's status subcommand][6] and look for `hpe_aruba_edgeconnect` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Logs

The recommended way to collect logs from HPE Aruba EdgeConnect is to configure the appliance to forward logs through syslog, as described in the [HPE Aruba Networking documentation][8].

1. Enable log collection in your `datadog.yaml` file:

    ```yaml
    logs_enabled: true
    ```
2. Uncomment and edit the logs configuration block in your `hpe_aruba_edgeconnect.d/conf.yaml` file. For example:

    ```yaml
    logs:
      - type: tcp
        port: 10514
        source: hpe_aruba_edgeconnect
        service: <SERVICE>
    ```

### Events

The HPE Aruba EdgeConnect integration does not include any events.

### Service Checks

The HPE Aruba EdgeConnect integration does not include any service checks.

## Troubleshooting

Need help? Contact [Datadog support][9].

[1]: https://www.hpe.com/us/en/aruba-edgeconnect-sd-wan.html
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/containers/kubernetes/integrations/
[4]: https://github.com/DataDog/integrations-core/blob/master/hpe_aruba_edgeconnect/datadog_checks/hpe_aruba_edgeconnect/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/configuration/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/configuration/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/hpe_aruba_edgeconnect/metadata.csv
[8]: https://arubanetworking.hpe.com/techdocs/sdwan/docs/orch/support/tech-assistance/remote-log-msgs/
[9]: https://docs.datadoghq.com/help/
