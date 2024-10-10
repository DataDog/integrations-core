## Overview

[ISC Bind][3] is a complete, highly portable implementation of the Domain Name System (DNS) protocol. The ISC Bind name server (named), can act as an authoritative name server, recursive resolver, DNS forwarder, or all three simultaneously.

This integration provides enrichment and visualization for Query, Query Errors, Network, Lame Servers, Notify, and Security log types. It helps to visualize detailed insights into DNS request patterns, DNS communication and proper server configurations, DNS attacks, ensuring a robust and reliable DNS environment through the out-of-the-box dashboards. Also, This integration provides out of the box detection rules.


## Setup

### Installation

To install the ISC Bind integration, run the following Agent installation command and the steps below. For more information, see the [Integration Management][4] documentation.

**Note**: This step is not necessary for Agent version >= 7.58.0.

Linux command
  ```shell
  sudo -u dd-agent -- datadog-agent integration install datadog-isc_bind==1.0.0
  ```
#### File Monitoring

1. Log in to your ISC BIND device.
2. Open `named.conf` file to add a logging clause:
    ```
    logging {
     channel <example_channel> {
          file "/folder_path/file_name.log" versions <unlimited | <integer>> size <size> suffix <increment | timestamp>;
          print-time (yes | local | iso8601 | iso8601-utc);
          print-category yes;
          print-severity yes;
     };
     category <example-category> { <example_channel>; };
    }
    ```
    **NOTE**: Recommended value for `print-time` is `iso8601-utc` because datadog expects all logs to be in the UTC time zone by default. If the timezone of your ISC Bind logs is not UTC please make sure to follow [these](#timezone-steps) steps. Also, check the categories defined by ISC Bind [here][9].
    
    Example logging channel:
    ```
    logging {
     channel default_log {
          file "/var/log/named/query.log" versions 3 size 10m;
          print-time iso8601-utc;
          print-category yes;
          print-severity yes;
     };
       category default { default_log; };
    }
    ```
3. Save and exit the file.
4. Restart the service
    ```
    service named restart
    ```

#### Syslog
1. Log in to your ISC BIND device.
2. Open `named.conf` file to add a logging clause:
    ```
    logging {
     channel <example_channel> {
          syslog <syslog_facility>;
          severity (critical | error | warning | notice | info | debug [level ] | dynamic);
          print-time (yes | local | iso8601 | iso8601-utc);
          print-category yes;
          print-severity yes;
     };
     category <example-category> { <example_channel>; };
    }
    ```
    **NOTE**: Recommended value for `print-time` is `iso8601-utc` because Datadog expects all logs to be in the UTC time zone by default. If the timezone of your ISC Bind logs is not UTC please make sure to follow [these](#timezone-steps) steps. Also, check the categories defined by ISC Bind [here][9].
    
    Example logging channel:
    ```
    logging {
     channel default_log {
          syslog local3;
          print-time iso8601-utc;
          print-category yes;
          print-severity yes;
     };
       category default { default_log; };
    }
    ```

3. Save and exit the file.
4. Edit the syslog/rsyslog configuration to log to your Datadog using the facility you selected in ISC BIND:
    ```
    <syslog_facility>.* @@<DATADOG_AGENT_IP_ADDRESS>:<PORT>
    ```
5. Restart the following services.
    ```
    service syslog/rsyslog restart
    service named restart
    ```

**Note**: Make sure you have mentioned `print-category` and `print-severity` as yes in the channels configured for ISC bind application.

### Configuration

#### Log collection

1. Collecting logs is disabled by default in the Datadog Agent. Enable it in the `datadog.yaml` file:

   ```yaml
   logs_enabled: true
   ```

#### File Monitoring

1. Add this configuration block to your `isc_bind.d/conf.yaml` file to start collecting your ISC Bind logs.

   See the [sample isc_bind.d/conf.yaml][5] for available configuration options.

   ```yaml
   logs:
     - type: file
       path: /var/log/named/*.log
       service: isc-bind
       source: isc-bind
   ```
   **Note**: Change the `path` variable in `conf.yaml` to the same as configured in `file` parameter in channels for ISC Bind application.

3. [Restart the Agent][2].

#### Syslog
1. Add this configuration block to your `isc_bind.d/conf.yaml` file to start collecting your ISC Bind logs.

   See the [sample isc_bind.d/conf.yaml][5] for available configuration options.

   ```yaml
   logs:
     - type: tcp
       port: <PORT>
       service: isc-bind
       source: isc-bind
   ```
   **Note**: Value of `port` should be the same as mentioned in `syslog.conf/rsyslog.conf`.

3. [Restart the Agent][2].

<h4 id="timezone-steps"> Specify a time zone other than UTC in the ISC Bind Datadog log pipeline</h4>

Datadog expects all logs to be in the UTC time zone by default. If the timezone of your ISC Bind logs is not UTC, specify the correct time zone in the ISC Bind Datadog pipeline.

To change the time zone in ISC Bind pipeline:

  1. Navigate to the [Pipelines page][7] in the Datadog app. 

  2. Enter "ISC Bind" in the  **Filter Pipelines** search box.

  3. Hover over the ISC Bind pipeline and click on the **clone**  button. This will create an editable clone of the ISC Bind pipeline.

  4. Edit the Grok Parser using the below steps:
      - In the cloned pipeline, find a processor with the name "Grok Parser: Parsing ISC Bind common log format" and click on the `Edit` button by hovering over the pipeline.
      - Under **Define parsing rules**,,
        - Change the string `UTC` to the [TZ identifier][8] of the time zone of your ISC Bind server. For example, if your timezone is IST, you would change the value to`Asia/Calcutta`.
      - Click the **update** button.

### Validation

[Run the Agent's status subcommand][6] and look for `isc_bind` under the Checks section.

## Data Collected

### Logs

The ISC Bind integration collects the following log types.

| Event Types    |
| -------------- |
| Query, Query Errors, Lame Servers, Notify, Security|

### Metrics

The ISC Bind does not include any metrics.

### Events

The ISC Bind integration does not include any events.

### Service Checks

The ISC Bind integration does not include any service checks.

## Troubleshooting

If you see a **Permission denied** error while monitoring the log files, give the `dd-agent` user read permission on them.

  ```shell
  sudo chown -R dd-agent:dd-agent /var/log/named/
  ```

For any further assistance, contact [Datadog support][1].

[1]: https://docs.datadoghq.com/help/
[2]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[3]: https://www.isc.org/bind/
[4]: https://docs.datadoghq.com/agent/guide/integration-management/?tab=linux#install
[5]: https://github.com/DataDog/integrations-core/blob/master/isc_bind/datadog_checks/isc_bind/data/conf.yaml.example
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://app.datadoghq.com/logs/pipelines
[8]: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones
[9]: https://downloads.isc.org/isc/bind9/9.18.29/doc/arm/html/reference.html#namedconf-statement-category