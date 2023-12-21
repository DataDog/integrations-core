## Overview

* Zeek is the world’s leading platform for network security monitoring.
* Zeek interprets what it sees and creates compact, high-fidelity transaction logs, file content, and fully customized output, suitable for manual review on disk or in a more analyst-friendly tool like a security and information event management (SIEM) system.

This integration provides visulizations and log enrichments for Network Protocols, Files, Detections, Network Observations, Miscellaneous, some Diagnostics logs and Corelight Suricata eventtypes.

## Setup

### Installation

**Opensource Zeek:**
1. [Install the Agent][10] on your Zeek machine.
2. Setup json-streaming-logs package
   - Install [Corelight Zeek plugin][11] for JSON logging
     ```
     /opt/zeek/bin/zkg install corelight/json-streaming-logs
     ```
   - Load ZKG packages
     ```
     echo -e "\n# Load ZKG packages\n@load packages" >> /opt/zeek/share/zeek/site/local.zeek
     ```
   - Disable TSV logging
     ```
     echo -e "\n# Disable TSV logging\nconst JSONStreaming::disable_default_logs = T;" >> /opt/zeek/share/zeek/site/local.zeek
     ```
   - Set file log rotation to once an hour
     ```
     echo -e "\n# JSON logging - time before rotating a file\nconst JSONStreaming::rotation_interval = 60mins;" >> /opt/zeek/share/zeek/site/local.zeek
     ```
   - Start the zeek
     ```
     /opt/zeek/bin/zeekctl install
     ```
     ```
     /opt/zeek/bin/zeekctl start
     ```

**Corelight Zeek:**
* You have the [Datadog Agent][10] installed and running

### Configuration

#### Log collection

**Opensource Zeek:**
1. Collecting logs is disabled by default in the Datadog Agent. Enable it in datadog.yaml:
    ```
    logs_enabled: true
    ```

2. Add this configuration block to your zeek.d/conf.yaml file to start collecting your Zeek logs.
    ```
    logs:
    - type: file
        path: /opt/zeek/logs/current/*.log
        exclude_paths:
          - /opt/zeek/logs/current/*.*.log
        service: zeek
        source: zeek
    ```
**Note:** Add the log files path in `exclude_paths` parameter if you don't want to monitor those log files.  
eg.
  ```
  exclude_paths:
    - /opt/zeek/logs/current/ntlm.log
    - /opt/zeek/logs/current/radius.log
    - /opt/zeek/logs/current/rfb.log
  ```

3. [Restart the Agent][5].

**Corelight Zeek:**
1. Collecting logs is disabled by default in the Datadog Agent. Enable it in datadog.yaml:
    ```
    logs_enabled: true
    ```

2. Add this configuration block to your zeek.d/conf.yaml file to start collecting your logs
    ```
    logs:
    - type: tcp
      port: <PORT>
      service: zeek
      source: zeek
    ```

3. [Restart the Agent][5].

4. Configuring Syslog Message Forwarding from corelight

### Validation

[Run the Agent's status subcommand][6] and look for `zeek` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

The zeek integration does not include any events.

### Service Checks

The zeek integration does not include any service checks.

## Troubleshooting

**Opensource Zeek:**

If you see a **Permission denied** error while monitoring the log files, see the following instruction

   1. Give read permission to dd-agent user to monitor the log files
      ```
      sudo chown -R dd-agent:dd-agent /opt/zeek/current/
      ```
**Corelight Zeek:**

#### Permission denied while port binding:

If you see a **Permission denied** error while port binding in the Agent logs, see the following instructions:

   1. Binding to a port number under 1024 requires elevated permissions. Follow the instructions below to set this up.

      - Grant access to the port using the `setcap` command:

         ```
         sudo setcap CAP_NET_BIND_SERVICE=+ep /opt/datadog-agent/bin/agent/agent
         ```

      - Verify the setup is correct by running the `getcap` command:

         ```
         sudo getcap /opt/datadog-agent/bin/agent/agent
         ```

         With the expected output:

         ```
         /opt/datadog-agent/bin/agent/agent = cap_net_bind_service+ep
         ```

         **Note**: Re-run this `setcap` command every time you upgrade the Agent.

   2. [Restart the Agent][5].

#### Data is not being collected:

Make sure that traffic is bypassed from the configured port if the firewall is enabled.

#### Port already in use:

If you see the **Port <PORT-NO\> Already in Use** error, see the following instructions. The example below is for PORT-NO = 514:

On systems using Syslog, if the Agent listens for Zeek logs on port 514, the following error can appear in the Agent logs: `Can't start UDP forwarder on port 514: listen udp :514: bind: address already in use`.

This error occurs because by default, Syslog listens on port 514. To resolve this error, take **one** of the following steps:
- Disable Syslog
- Configure the Agent to listen on a different, available port


[1]: **LINK_TO_INTEGRATION_SITE**
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[4]: https://github.com/DataDog/integrations-core/blob/master/zeek/datadog_checks/zeek/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/zeek/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/zeek/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
[10]: https://docs.datadoghq.com/agent/
[11]: https://github.com/corelight/json-streaming-logs
