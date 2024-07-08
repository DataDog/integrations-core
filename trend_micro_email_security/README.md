## Overview

[Trend Micro Email Security][4] is a cloud-based solution that stops phishing, ransomware, and Business Email Compromise (BEC) attacks. This solution uses an optimum blend of cross-generational threat techniques, like machine learning, sandbox analysis, data loss prevention (DLP), and other methods to stop all types of email threats.

This integration ingests the following logs:

- Policy Events/Detection
- Mail Tracking
- URL Click Tracking
- Audit logs

Using out-of-the-box dashboards, you can visualize detailed insights into email traffic analysis, URL click analysis, real time threat detection, security detection and observation, and compliance monitoring.

## Setup

### Installation

To install the Trend Micro Email Security integration, run the following Agent installation command and the steps below. For more information, see the [Integration Management][8] documentation.

**Note**: This step is not necessary for Agent version >= 7.52.0.

Linux command:

```shell
sudo -u dd-agent -- datadog-agent integration install datadog-trend_micro_email_security==1.0.0
```

### Configuration

#### Log collection

**Trend Micro Email Security:**

1. Collecting logs is disabled by default in the Datadog Agent. Enable it in the `datadog.yaml` file:

   ```yaml
   logs_enabled: true
   ```

2. Add this configuration block to your `trend_micro_email_security.d/conf.yaml` file to start collecting your Trend Micro Email Security logs.

   See the [sample trend_micro_email_security.d/conf.yaml][9] for available configuration options.

   ```yaml
   logs:
     - type: tcp
       port: <PORT>
       service: trend-micro-email-security
       source: trend-micro-email-security
   ```

3. [Restart the Agent][1].

4. Configure Trend Micro Email Security to send data to Datadog:
   1. Login into Trend Micro Email Security administrator console.
   2. Configure syslog server's firewall to accept connections from the IP addresses or CIDR blocks listed in [Configuring Syslog Settings][5], allowing Trend Micro Email Security to forward syslog messages.
   3. Follow the [Syslog Server Profiles][6] steps.
      1. In step 4 of the `Syslog Server Profiles` instructions, please use the `CEF` format for the `syslog messages`.
   4. Follow the [Syslog Forwarding][7] steps.
      1. In steps 2 to 5 of the `Syslog Forwarding` instructions, select the syslog server created in above step iii.

### Validation

[Run the Agent's status subcommand][2] and look for `trend_micro_email_security` under the Checks section.

## Data Collected

### Logs

The Trend Micro Email Security integration collects the following log-types.

| Format     | Event Types                                                            |
| ---------- | ---------------------------------------------------------------------- |
| CEF Format | Policy Events/Detection, Mail Tracking, URL Click Tracking, Audit logs |

### Metrics

The Trend Micro Email Security integration does not include any metrics.

### Events

The Trend Micro Email Security integration does not include any events.

### Service Checks

The Trend Micro Email Security integration does not include any service checks.

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

3. [Restart the Agent][1].

**Data is not being collected:**

Make sure that traffic is bypassed from the configured port if the firewall is enabled.

**Port already in use:**

If you see the **Port <PORT-NO\> Already in Use** error, see the following instructions. The example below is for PORT-NO = 514:

On systems using Syslog, if the Agent listens for Trend Micro Email Security logs on port 514, the following error can appear in the Agent logs: `Can't start TCP forwarder on port 514: listen tcp :514: bind: address already in use`.

This error occurs because by default, Syslog listens on port 514. To resolve this error, take **one** of the following steps:

- Disable Syslog
- Configure the Agent to listen on a different, available port

For any further assistance, contact [Datadog support][3].

[1]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[2]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[3]: https://docs.datadoghq.com/help/
[4]: https://www.trendmicro.com/en_in/business/products/user-protection/sps/email-and-collaboration/email-security.html
[5]: https://docs.trendmicro.com/en-us/documentation/article/trend-micro-email-security-online-help-managing-syslog
[6]: https://docs.trendmicro.com/en-us/documentation/article/trend-micro-email-security-online-help-syslog-server-profil
[7]: https://docs.trendmicro.com/en-us/documentation/article/trend-micro-email-security-online-help-configuring-syslog-f
[8]: https://docs.datadoghq.com/agent/guide/integration-management/?tab=linux#install
[9]: https://github.com/DataDog/integrations-core/blob/master/trend_micro_email_security/datadog_checks/trend_micro_email_security/data/conf.yaml.example
