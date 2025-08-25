# Agent Check: checkpoint_harmony_endpoint

## Overview

Checkpoint Harmony Endpoint is a next-generation endpoint security solution designed to prevent, detect, and respond to threats on user devices (desktops, laptops, servers, etc). This integration monitors [Checkpoint Harmony Endpoint][1].

## Setup
1. Collecting logs is disabled by default in the Datadog Agent. Enable it in the `datadog.yaml` file with:

    ```yaml
      logs_enabled: true
    ```
2. Add this configuration block to your `checkpoint_harmony_endpoint.d/conf.yaml` file to start collecting your checkpoint_harmony_endpoint logs:

    ```yaml
      logs:
        - type: file
          path:  /var/log/checkpoint.log
          source: checkpoint_harmony_endpoint
          service: <SERVICE_NAME>
    ```

    Change the `path` and `service` parameter values for your environment.

3. [Restart the Agent][4].

### Installation

The checkpoint harmony endpoint check is included in the [Datadog Agent][2] package.

### Prerequisites

1. Administrative access to Checkpoint Harmony Endpoint - Gaia installed on your server.
2. The Datadog Agent installed and running (on a server or container that can receive syslog messages).
3. Network Access between the endpoint and the Datadog Agent (usually port 514, but may be a custom value). Enable log exporter in the Smart Console for log streaming.
4. Syslog support enabled in the Datadog Agent (with a TCP or UDP  listener configured).

### Validation

1. Confirm the Datadog Agent is listening on the correct port (`514` in the following examples)
    `sudo netstat -tunlp | grep 514`
    If using TCP and UDP listeners, use the following command:
    `sudo lsof -i :514`
2. Confirm logs are reaching the Agent from the correct log source.
    `tail -f /var/log/datadog/syslog.log`
**Note**: If the file doesn't exist, verify that syslog logs are being written by your configuration.
3. Use the tcpdump command to confirm network traffic. On the Datadog Agent host:
    `sudo tcpdump -i any port 514`
After running this command, you should see traffic from the Checkpoint endpoint client's IP address. If you don't see any such traffic, check the firewall rules between Checkpoint Endpoint and the Datadog Agent. Confirm the correct protocol (UDP or TCP) is being used on both sides.
4. Check the Datadog [Live Tail][7] in Datadog for logs from the source and service you defined in the `conf.yaml` file.
5. After following these steps, you can create a test log on the harmony client by triggering an event.
6. Check for tags or facets to use them for better filtering based on the required data.

### Metrics

The Checkpoint Harmony Endpoint integration does not include any metrics.

### Log collection
## Data Collected
The Checkpoint Harmony Endpoint logs contain key information of the endpoint client such as the event timestamp, detected_by and client IPs and ports, protocol used, firewall action (allow/deny), the matched rule name, user identity (if available), log type (e.g., forensic, malware, etc), action used, device name, and status of the operation, all of which help monitor endpoint behavior, access control, and system activity and many more which are collected by DataDog.


### Events

The checkpoint harmony endpoint integration includes log events such as attacks and malware hits.

## Troubleshooting

Need help? Contact [Datadog support][3].

[1]: https://www.checkpoint.com/harmony/endpoint/
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/help/
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[5]: https://app.datadoghq.com/integrations?search=checkpoint_harmony_endpoint
[6]: https://github.com/DataDog/integrations-core/blob/master/checkpoint_harmony_endpoint/assets/service_checks.json