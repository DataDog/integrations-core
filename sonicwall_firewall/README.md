## Overview

[Sonicwall Firewall][1] is a network security solution designed to protect organizations from a wide range of cyber threats. It offers advanced security features, high performance, and scalability, making it suitable for businesses of all sizes. Sonicwall Firewall are known for their ability to provide real-time protection against emerging threats while ensuring secure and efficient network traffic management.

This integration provides enrichment and visualization for all log types shared by Sonicwall Firewall over syslog. It helps to visualize detailed insights into the analysis of logs received by Syslog through the out-of-the-box dashboards and detection rules.


## Setup

### Installation

To install the Sonicwall Firewall integration, run the following Agent installation command and the steps below. 

For more information, see the [Integration Management][2] documentation.

**Note**: This step is not necessary for Agent version >= 7.58.0.

Linux command
  ```shell
  sudo -u dd-agent -- datadog-agent integration install datadog-sonicwall-firewall==1.0.0
  ```

### Configuration

#### Log Collection

1.  Collecting logs is disabled by default in the Datadog Agent. Enable it in the `datadog.yaml` file:
    ```yaml
    logs_enabled: true
    ```

2. Add this configuration block to your `sonicwall_firewall.d/conf.yaml` file to start collecting your Sonicwall Firewall logs:

    ```yaml
    logs:
      - type: udp
        port: <udp_port>
        source: sonicwall-firewall
    ```
    See the [sample sonicwall_firewall.d/conf.yaml][3] for available configuration options.
    
    **NOTE**: configure a [syslog server][8] on a Sonicwall Firewall with `<udp_port>`.
   
    Configure a Syslog Server in your firewall using the following options:

    - **Name or IP Address**: The address where your Datadog Agent running this integration is reachable.
    - **Port**: The Syslog port (UDP) configured in this integration.
    - **Server Type**: Syslog Server.
    - **Syslog Format**: Enhanced Syslog.
    - **Syslog ID**: Change this default (firewall) if you need to differentiate between multiple firewalls.

    Set default time as UTC:

    - In `Device -> Log -> Syslog` first select the **Syslog Settings** tab and enable **Display Syslog Timestamp in UTC** and click **Accept** button to get time in UTC.

    Additional Configuration:

    - In `Device -> Log -> Settings` you can select the **Logging Level** and **Alert Level** to get different kind of logs.

3. [Restart the Agent][4].

#### Specify a time zone other than UTC in the Sonicwall Firewall Datadog log pipeline
Datadog expects all logs to be in the UTC time zone by default. If the timezone of your Sonicwall Firewall logs is not UTC, specify the correct time zone in the Sonicwall Firewall Datadog pipeline.

To change the time zone in Sonicwall Firewall pipeline:

1. Navigate to the [**Pipelines** page][10] in the Datadog app.

2. Enter "Sonicwall Firewall" in the **Filter Pipelines** search box.

3. Hover over the Sonicwall Firewall pipeline and click on the **clone** button. This will create an editable clone of the Sonicwall Firewall pipeline.

4. Edit the Grok Parser using the below steps:

   - In the cloned pipeline, find a processor with the name `"Grok Parser: Parsing Sonicwall Firewall time"` and click on the `Edit` button by hovering over the pipeline.
   - Under **Define parsing rules**
      - Modify the rule and provide the [TZ identifier][9] of the time zone of your Sonicwall Firewall server. For example, if your timezone is IST, you would remove `' z'` and add the value to `Asia/Calcutta`.
      - Example:

        **Existing rule**

          ```shell
          rule %{date("yyyy-MM-dd HH:mm:ss z"):timestamp}
          ```
        
        **Modified rule for IST timezone**

          ```shell
          rule %{date("yyyy-MM-dd HH:mm:ss", "Asia/Calcutta"):timestamp}
          ```

      - Additional step
      
        - Under **log samples**
          - Remove UTC from the existing value.
          - Example:

              **Existing Value**

              ```shell
              2024-09-11 06:30:00 UTC
              ```
              
              **Updated Value**
              ```shell
              2024-09-11 06:30:00
              ```

    - Click the **update** button.

### Validation

[Run the Agent's status subcommand][5] and look for `sonicwall_firewall` under the Checks section.

## Data Collected

### Log

|         Format          | Log Types    |
| --------------------    | -------------- |
| CEF (Enhanced Syslog)   | All          |

### Metrics

The Sonicwall Firewall integration does not include any metrics.
### Events

The Sonicwall Firewall integration does not include any events.

### Service Checks

The Sonicwall Firewall integration does not include any service checks.

See [service_checks.json][6] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][7].

[1]: https://www.sonicwall.com/
[2]: https://docs.datadoghq.com/agent/guide/integration-management/?tab=linux#install
[3]: https://github.com/DataDog/integrations-core/blob/master/sonicwall_firewall/datadog_checks/sonicwall_firewall/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[6]: https://github.com/DataDog/integrations-core/blob/master/sonicwall_firewall/assets/service_checks.json
[7]: https://docs.datadoghq.com/help/
[8]: https://www.sonicwall.com/support/knowledge-base/how-can-i-configure-a-syslog-server-on-a-sonicwall-firewall/170505984096810
[9]: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones
[10]: https://app.datadoghq.com/logs/pipelines