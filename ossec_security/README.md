# Agent Integration: ossec-security

## Overview

[OSSEC][4] is an Open Source Host based Intrusion Detection System. It performs log analysis, integrity checking, Windows registry monitoring, rootkit detection, real-time alerting and active response. It helps to monitor and manage security events across various IT infrastructures.

This integration ingests the following types of logs:
- FTPD
- Firewall
- System
- Syslog
- SSHD
- Pam
- Windows
- Web Access

Visualize detailed insights into Firewall, FTPD, System, Syslog, SSHD, Pam, Windows, Web Access logs through the out-of-the-box dashboards.

## Setup

### Installation

To install the OSSEC Security integration, run the following Agent installation command and the steps below. For more information, see the [Integration Management][6] documentation.

**Note**: This step is not necessary for Agent version >= 7.54.0.

Linux command
  ```shell
  sudo -u dd-agent -- datadog-agent integration install datadog-ossec_security==1.0.0
  ```

### Configuration

#### Logs Collection

1. Collecting logs is disabled by default in the Datadog Agent. Enable it in datadog.yaml:

    ```shell
    logs_enabled: true
    ```
2. Add this configuration block to your `ossec_security.d/conf.yaml` file to start collecting your logs.

    We will be using the UDP method to collect the OSSEC alerts data.
    See the [sample ossec_security.d/conf.yaml][8] for available configuration options.

    ```yaml
      logs:
      - type: udp
        port: <PORT>
        source: ossec-security
        service: ossec-security
    ```
    **Note**: It is recommended not to change the service and source values as these parameters are integral to the pipeline's operation.

3. [Restart the Agent][3].

#### Configure Syslog Message Forwarding from OSSEC.
  1. Add following configuration in `/var/ossec/etc/ossec.conf`.

      In this example all alerts are sent to 1.1.1.1 on port 8080 in **JSON** format.
      ```xml
        <syslog_output>
          <server>1.1.1.1</server>
          <port>8080</port>
          <format>json</format>
        </syslog_output>
      ```

      *IP_ADDRESS(1.1.1.1): ip address where your datadog-agent is running.

      *PORT(8080): port on which your datadog-agent is listening.

      Note: Using JSON format is required since OSSEC Security pipeline parses JSON formatted logs only.

  2. After this change is made, the client-syslog process should be enabled:
      ```shell
      /var/ossec/bin/ossec-control enable client-syslog
      ```

  3. Restart OSSEC service:
      ```shell
      /var/ossec/bin/ossec-control restart
      ```

#### Firewall Logs Collection[Optional]:
Since OSSEC server does not forward the firewall alert logs via syslog by default, if you want to forward firewall alert logs via OSSEC server follow the below step.

  1. Locate `firewall_rules.xml` file.
  ```
  /var/ossec/rules/firewall_rules.xml
  ```

  2. Edit firewall_rules.xml and remove all the occurrences of below line from the file:
  ```xml
  <options>no_log</options>
  ``` 

  3. Restart your OSSEC server:
  ```shell
  /var/ossec/bin/ossec-control restart
  ```

#### Changes in OSSEC Security Datadog log pipeline for timezone other than UTC

Since Datadog expects all the logs in UTC timezone by default, If the timezone of your OSSEC logs is other than UTC, please specify it in the OSSEC Security datadog pipeline.

In order to change the timezone in OSSEC Security pipeline follow the below steps:

  1. Navigate to Pipelines in the datadog cloud account. 
      - Go to Logs -> Log Stream -> Pipelines.

  2. Search for `OSSEC Security` using Filter Pipelines.

  3. Clone `OSSEC Security` pipeline in order to change the timezone.
      - Hover over the `OSSEC Security` pipeline and click on the `clone`  button. This will clone the `OSSEC Security` pipeline which will be editable.

  4. Edit the Grok Parser using below steps:
      - Find a processor with the name "Grok Parser: Parsing OSSEC alerts" and click on the `Edit` button by hovering over the pipeline.
      - Under the Define parsing rules,
        - Change the string `UTC` to the timezone of your OSSEC server. For example, if your timezone is IST then as per the timezone mentioned in the below reference link,you need to replace the value as `Asia/Calcutta`.

        Timezone IDs are pulled from the TZ database. For more information, [see TZ database names][9].
      - Click on the `update` button.



### Validation

[Run the Agent's status subcommand][7] and look for `ossec_security` under the Checks section.

## Data Collected

### Log 

| Format     | Event Types    |
| ---------  | -------------- |
| JSON | syslog, sshd, pam, ossec, windows, firewall, ftpd, web_access |

### Metrics

The OSSEC Security does not include any metrics.

### Events

The OSSEC Security integration does not include any events.

### Service Checks

The OSSEC Security integration does not include any service checks.

## Troubleshooting

**Permission denied while port binding:**

If you see a **Permission denied** error while port binding in the Agent logs, see the following instructions:

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

- If you see the **Port <PORT-NO> Already in Use** error, see the following instructions. The example below is for PORT-NO = 514:

- On systems using Syslog, if the Agent listens for OSSEC logs on port 514, the following error can appear in the Agent logs: `Can't start UDP forwarder on port 514: listen udp :514: bind: address already in use`.

- This error occurs because by default, Syslog listens on port 514. To resolve this error, take **one** of the following steps: 

    - Disable Syslog 
    - Configure the Agent to listen on a different, available port


For any further assistance, contact [Datadog support][1].

[1]: https://docs.datadoghq.com/help/
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[4]: https://www.ossec.net/
[5]: https://github.com/DataDog/integrations-core/blob/master/ossec_security/assets/service_checks.json
[6]: https://docs.datadoghq.com/agent/guide/integration-management/?tab=linux#install
[7]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[8]: https://github.com/DataDog/integrations-core/blob/master/ossec_security/datadog_checks/ossec_security/data/conf.yaml.example
[9]: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones