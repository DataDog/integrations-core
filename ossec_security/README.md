# Agent Integration: ossec-security

## Overview

[OSSEC][4] is an open source, host based intrusion detection system. It performs log analysis, integrity checking, Windows registry monitoring, rootkit detection, real-time alerting and active response. It helps to monitor and manage security events across various IT infrastructures.

This integration ingests the following types of logs:
- FTPD
- Firewall
- System
- Syslog
- SSHD
- PAM
- Windows
- Web access

Visualize detailed insights into these logs through the out-of-the-box dashboards.

## Setup

### Installation

To install the OSSEC Security integration, run the following Agent installation command and the steps below. For more information, see the [Integration Management][6] documentation.

**Note**: This step is not necessary for Agent version >= 7.57.0.

Linux command
  ```shell
  sudo -u dd-agent -- datadog-agent integration install datadog-ossec_security==1.0.0
  ```

### Configuration

#### Logs collection

1. Collecting logs is disabled by default in the Datadog Agent. Enable it in `datadog.yaml`:

    ```yaml
    logs_enabled: true
    ```
2. Add this configuration block to your `ossec_security.d/conf.yaml` file to start collecting your logs.

    Use the UDP method to collect the OSSEC alerts data.
    See the [sample ossec_security.d/conf.yaml][8] for available configuration options.

    ```yaml
      logs:
      - type: udp
        port: <PORT>
        source: ossec-security
        service: ossec-security
    ```
    **Note**: It is recommended not to change the service and source values, as these parameters are integral to the pipeline's operation.

3. [Restart the Agent][3].

#### Configure syslog message forwarding from OSSEC
  1. Add following configuration in `/var/ossec/etc/ossec.conf`.

      In this example, all alerts are sent to 1.1.1.1 on port 8080 in JSON format.
      ```xml
        <syslog_output>
          <server>1.1.1.1</server>
          <port>8080</port>
          <format>json</format>
        </syslog_output>
      ```

      * The `server` tag should contain the IP address where your Datadog Agent is running.

      * The `port` tag should contain the port on which your Datadog Agent is listening.

      Note: Using JSON format is required, since OSSEC Security pipeline parses JSON formatted logs only.

  2. Enable client-syslog process:
      ```shell
      /var/ossec/bin/ossec-control enable client-syslog
      ```

  3. Restart the OSSEC service:
      ```shell
      /var/ossec/bin/ossec-control restart
      ```

#### Enable firewall logs collection (optional):
OSSEC server does not forward the firewall alert logs by default. To forward firewall alert logs via OSSEC server, follow the steps below.

  1. Locate the `firewall_rules.xml` file at `/var/ossec/rules/firewall_rules.xml`.

  2. Edit `firewall_rules.xml` to remove all the occurrences of the below line from the file:
  ```xml
  <options>no_log</options>
  ``` 

  3. Restart your OSSEC server:
  ```shell
  /var/ossec/bin/ossec-control restart
  ```

#### Specify a time zone other than UTC in the OSSEC Security Datadog log pipeline

Datadog expects all logs to be in the UTC time zone by default. If the timezone of your OSSEC logs is not UTC, specify the correct time zone in the OSSEC Security Datadog pipeline.

To change the time zone in OSSEC Security pipeline:

  1. Navigate to the [**Pipelines** page][10] in the Datadog app. 

  2. Enter "OSSEC Security" in the  **Filter Pipelines** search box.

  3. Hover over the OSSEC Security pipeline and click on the **clone**  button. This will create an editable clone of the OSSEC Security pipeline.

  4. Edit the Grok Parser using the below steps:
      - In the cloned pipeline, find a processor with the name "Grok Parser: Parsing OSSEC alerts" and click on the `Edit` button by hovering over the pipeline.
      - Under **Define parsing rules**,,
        - Change the string `UTC` to the [TZ identifier][9] of the time zone of your OSSEC server. For example, if your timezone is IST, you would change the value to`Asia/Calcutta`.
      - Click the **update** button.



### Validation

[Run the Agent's status subcommand][7] and look for `ossec_security` under the Checks section.

## Data Collected

### Log 

| Format     | Event Types    |
| ---------  | -------------- |
| JSON | syslog, sshd, pam, ossec, windows, firewall, ftpd, web_access |

### Metrics

The OSSEC Security integration does not include any metrics.

### Events

The OSSEC Security integration does not include any events.

### Service Checks

The OSSEC Security integration does not include any service checks.

## Troubleshooting

**Permission denied while port binding:**

If you see a **Permission denied** error while port binding in the Agent logs:

1. Binding to a port number under 1024 requires elevated permissions. Grant access to the port using the `setcap` command:
    ```shell
    sudo setcap CAP_NET_BIND_SERVICE=+ep /opt/datadog-agent/bin/agent/agent
    ```

2. Verify the setup is correct by running the `getcap` command:

    ```shell
    sudo getcap /opt/datadog-agent/bin/agent/agent
    ```

    With the expected output:

    ```shell
    /opt/datadog-agent/bin/agent/agent = cap_net_bind_service+ep
    ```

    **Note**: Re-run this `setcap` command every time you upgrade the Agent.

3. [Restart the Agent][3].

**Data is not being collected:**

Make sure that traffic is bypassed from the configured port if the firewall is enabled.

**Port already in use:**

- If you see the **Port <PORT_NUMBER> Already in Use** error, see the following instructions. The example below is for port 514:

- On systems using Syslog, if the Agent listens for OSSEC logs on port 514, the following error can appear in the Agent logs: `Can't start UDP forwarder on port 514: listen udp :514: bind: address already in use`. This error occurs because by default, Syslog listens on port 514. To resolve this error, take **one** of the following steps: 

    - Disable Syslog.
    - Configure the Agent to listen on a different, available port.


For further assistance, contact [Datadog support][1].

[1]: https://docs.datadoghq.com/help/
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[4]: https://www.ossec.net/
[5]: https://github.com/DataDog/integrations-core/blob/master/ossec_security/assets/service_checks.json
[6]: https://docs.datadoghq.com/agent/guide/integration-management/?tab=linux#install
[7]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[8]: https://github.com/DataDog/integrations-core/blob/master/ossec_security/datadog_checks/ossec_security/data/conf.yaml.example
[9]: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones
[10]: https://app.datadoghq.com/logs/pipelines