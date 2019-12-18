# Agent Check: Tomcat

![Tomcat Dashboard][1]

## Overview

This check collects Tomcat metrics, for example:

* Overall activity metrics: error count, request count, processing times
* Thread pool metrics: thread count, number of threads busy
* Servlet processing times

And more.

## Setup
### Installation

The Tomcat check is included in the [Datadog Agent][3] package, so you don't need to install anything else on your Tomcat servers.

This check is JMX-based, so you need to enable JMX Remote on your Tomcat servers. Follow the instructions in the [Tomcat documentation][4].

### Configuration
#### Host

Follow the instructions below to configure this check for an Agent running on a host. For containerized environments, see the [Containerized](#containerized) section.

1. Edit the `tomcat.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][5] to collect Tomcat metrics and [logs](#log-collection). See the [sample tomcat.d/conf.yaml][6] for all available configuration options.

2. [Restart the Agent][7].

See the [JMX Check documentation][8] for a list of configuration options usable by all JMX-based checks.

#### List of metrics

The `conf` parameter is a list of metrics to be collected by the integration. Only two keys are allowed:

* `include` (**mandatory**): A dictionary of filters. Any attribute that matches these filters is collected unless it also matches the `exclude` filters (see below).
* `exclude` (**optional**): A dictionary of filters. Attributes that match these filters are not collected.

For a given bean, metrics get tagged in the following manner:

```
mydomain:attr0=val0,attr1=val1
```

In this example, your metric is `mydomain` (or some variation depending on the attribute inside the bean) and has the tags `attr0:val0`, `attr1:val1`, and `domain:mydomain`.

If you specify an alias in an `include` key that is formatted as *camel case*, it is converted to *snake case*. For example, `MyMetricName` is shown in Datadog as `my_metric_name`.

##### The attribute filter

The `attribute` filter can accept two types of values:

* A dictionary whose keys are attributes names (see below). For this case, you can specify an alias for the metric that becomes the metric name in Datadog. You can also specify the metric type as a gauge or counter. If you choose counter, a rate per second is computed for the metric.
    ```yaml
      conf:
        - include:
          attribute:
            maxThreads:
              alias: tomcat.threads.max
              metric_type: gauge
            currentThreadCount:
              alias: tomcat.threads.count
              metric_type: gauge
            bytesReceived:
              alias: tomcat.bytes_rcvd
              metric_type: counter
    ```

* A list of attributes names (see below). For this case, the metric type is a gauge, and the metric name is `jmx.\[DOMAIN_NAME].\[ATTRIBUTE_NAME]`.
    ```yaml
      conf:
        - include:
          domain: org.apache.cassandra.db
          attribute:
            - BloomFilterDiskSpaceUsed
            - BloomFilterFalsePositives
            - BloomFilterFalseRatio
            - Capacity
            - CompressionRatio
            - CompletedTasks
            - ExceptionCount
            - Hits
            - RecentHitRate
    ```

#### Older versions

List of filters is only supported in Datadog Agent > 5.3.0. If you are using an older version, use singletons and multiple `include` statements instead.

    # Datadog Agent > 5.3.0
      conf:
        - include:
          domain: domain_name
          bean:
            - first_bean_name
            - second_bean_name

    # Older Datadog Agent versions
      conf:
        - include:
          domain: domain_name
          bean: first_bean_name
        - include:
          domain: domain_name
          bean: second_bean_name

#### Log collection

**Available for Agent >6.0**

1. Tomcat uses by default the `log4j` logger. To activate the logging into a file and customize the log format edit the `log4j.properties` file in the `$CATALINA_BASE/lib` directory as follows:

    ```
      log4j.rootLogger = INFO, CATALINA

      # Define all the appenders
      log4j.appender.CATALINA = org.apache.log4j.DailyRollingFileAppender
      log4j.appender.CATALINA.File = /var/log/tomcat/catalina.log
      log4j.appender.CATALINA.Append = true

      # Roll-over the log once per day
      log4j.appender.CATALINA.layout = org.apache.log4j.PatternLayout
      log4j.appender.CATALINA.layout.ConversionPattern = %d{yyyy-MM-dd HH:mm:ss} %-5p [%t] %c{1}:%L - %m%n

      log4j.appender.LOCALHOST = org.apache.log4j.DailyRollingFileAppender
      log4j.appender.LOCALHOST.File = /var/log/tomcat/localhost.log
      log4j.appender.LOCALHOST.Append = true
      log4j.appender.LOCALHOST.layout = org.apache.log4j.PatternLayout
      log4j.appender.LOCALHOST.layout.ConversionPattern = %d{yyyy-MM-dd HH:mm:ss} %-5p [%t] %c{1}:%L - %m%n

      log4j.appender.MANAGER = org.apache.log4j.DailyRollingFileAppender
      log4j.appender.MANAGER.File = /var/log/tomcat/manager.log
      log4j.appender.MANAGER.Append = true
      log4j.appender.MANAGER.layout = org.apache.log4j.PatternLayout
      log4j.appender.MANAGER.layout.ConversionPattern = %d{yyyy-MM-dd HH:mm:ss} %-5p [%t] %c{1}:%L - %m%n

      log4j.appender.HOST-MANAGER = org.apache.log4j.DailyRollingFileAppender
      log4j.appender.HOST-MANAGER.File = /var/log/tomcat/host-manager.log
      log4j.appender.HOST-MANAGER.Append = true
      log4j.appender.HOST-MANAGER.layout = org.apache.log4j.PatternLayout
      log4j.appender.HOST-MANAGER.layout.ConversionPattern = %d{yyyy-MM-dd HH:mm:ss} %-5p [%t] %c{1}:%L - %m%n

      log4j.appender.CONSOLE = org.apache.log4j.ConsoleAppender
      log4j.appender.CONSOLE.layout = org.apache.log4j.PatternLayout
      log4j.appender.CONSOLE.layout.ConversionPattern = %d{yyyy-MM-dd HH:mm:ss} %-5p [%t] %c{1}:%L - %m%n

      # Configure which loggers log to which appenders
      log4j.logger.org.apache.catalina.core.ContainerBase.[Catalina].[localhost] = INFO, LOCALHOST
      log4j.logger.org.apache.catalina.core.ContainerBase.[Catalina].[localhost].[/manager] =\
        INFO, MANAGER
      log4j.logger.org.apache.catalina.core.ContainerBase.[Catalina].[localhost].[/host-manager] =\
        INFO, HOST-MANAGER
    ```

2. By default, Datadog's integration pipeline support the following conversion patterns:

    ```
      %d{yyyy-MM-dd HH:mm:ss} %-5p %c{1}:%L - %m%n
      %d [%t] %-5p %c - %m%n
    ```

    Clone and edit the [integration pipeline][10] if you have a different format. Check Tomcat [logging documentation][9] for more information about Tomcat logging capabilities.

3. Collecting logs is disabled by default in the Datadog Agent, enable it in your `datadog.yaml` file:

    ```yaml
      logs_enabled: true
    ```

4. Add this configuration block to your `tomcat.d/conf.yaml` file to start collecting your Tomcat Logs:

    ```yaml
      logs:
        - type: file
          path: /var/log/tomcat/*.log
          source: tomcat
          service: myapp
          #To handle multi line that starts with yyyy-mm-dd use the following pattern
          #log_processing_rules:
          #  - type: multi_line
          #    name: log_start_with_date
          #    pattern: \d{4}\-(0?[1-9]|1[012])\-(0?[1-9]|[12][0-9]|3[01])
    ```

    Change the `path` and `service` parameter values and configure them for your environment. See the [sample tomcat.yaml][6] for all available configuration options.

5. [Restart the Agent][7].

#### Containerized

For containerized environments, see the [Autodiscovery with JMX][2] guide.

### Validation

[Run the Agent's status subcommand][11] and look for `tomcat` under the **Checks** section.

## Data Collected
### Metrics
See [metadata.csv][12] for a list of metrics provided by this check.

### Events
The Tomcat check does not include any events.

### Service Checks

**tomcat.can_connect**:<br>
Returns `CRITICAL` if the Agent is unable to connect to and collect metrics from the monitored Tomcat instance, otherwise returns `OK`.

## Troubleshooting
### Commands to view the available metrics

The `datadog-agent jmx` command was added in version 4.1.0.

  * List attributes that match at least one of your instance configurations:
`sudo /etc/init.d/datadog-agent jmx list_matching_attributes`
  * List attributes that match one of your instance configurations but that are not collected because it would exceed the number of metrics that can be collected:
`sudo /etc/init.d/datadog-agent jmx list_limited_attributes`
  * List attributes that are actually collected by your current instance configurations:
`sudo /etc/init.d/datadog-agent jmx list_collected_attributes`
  * List attributes that don't match any of your instance configurations:
`sudo /etc/init.d/datadog-agent jmx list_not_matching_attributes`
  * List every attribute available that has a type supported by JMXFetch:
`sudo /etc/init.d/datadog-agent jmx list_everything`
  * Start the collection of metrics based on your current configuration and display them in the console:
`sudo /etc/init.d/datadog-agent jmx collect`

## Further Reading
Additional helpful documentation, links, and articles:

* [Monitor Tomcat metrics with Datadog][13]
* [Key metrics for monitoring Tomcat][14]


[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/tomcat/images/tomcat_dashboard.png
[2]: https://docs.datadoghq.com/agent/guide/autodiscovery-with-jmx/?tab=containerizedagent
[3]: https://app.datadoghq.com/account/settings#agent
[4]: https://tomcat.apache.org/tomcat-6.0-doc/monitoring.html
[5]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[6]: https://github.com/DataDog/integrations-core/blob/master/tomcat/datadog_checks/tomcat/data/conf.yaml.example
[7]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[8]: https://docs.datadoghq.com/integrations/java
[9]: https://tomcat.apache.org/tomcat-7.0-doc/logging.html
[10]: https://docs.datadoghq.com/logs/processing/#integration-pipelines
[11]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[12]: https://github.com/DataDog/integrations-core/blob/master/tomcat/metadata.csv
[13]: https://www.datadoghq.com/blog/monitor-tomcat-metrics
[14]: https://www.datadoghq.com/blog/tomcat-architecture-and-performance
