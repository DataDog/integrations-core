# Agent Check: Tomcat

![Tomcat Dashboard][1]

## Overview

This check collects Tomcat metrics, for example:

- Overall activity metrics: error count, request count, processing times, etc.
- Thread pool metrics: thread count, number of threads busy, etc.
- Servlet processing times

## Setup

### Installation

The Tomcat check is included in the [Datadog Agent][2] package, so you don't need to install anything else on your Tomcat servers.

This check is JMX-based, so you need to enable JMX Remote on your Tomcat servers. Follow the instructions in [Monitoring and Managing Tomcat][3].

### Configuration

<!-- xxx tabs xxx -->
<!-- xxx tab "Host" xxx -->

#### Host

To configure this check for an Agent running on a host:

1. Edit the `tomcat.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][4] to collect Tomcat metrics and [logs](#log-collection). See the [sample tomcat.d/conf.yaml][5] for all available configuration options.

2. [Restart the Agent][6].

See the [JMX Check documentation][7] for a list of configuration options usable by all JMX-based checks.

#### List of metrics

The `conf` parameter is a list of metrics to be collected by the integration. Only two keys are allowed:

- `include` (**mandatory**): A dictionary of filters. Any attribute that matches these filters is collected unless it also matches the `exclude` filters (see below).
- `exclude` (**optional**): A dictionary of filters. Attributes that match these filters are not collected.

For a given bean, metrics get tagged in the following manner:

```text
mydomain:attr0=val0,attr1=val1
```

In this example, your metric is `mydomain` (or some variation depending on the attribute inside the bean) and has the tags `attr0:val0`, `attr1:val1`, and `domain:mydomain`.

If you specify an alias in an `include` key that is formatted as _camel case_, it is converted to _snake case_. For example, `MyMetricName` is shown in Datadog as `my_metric_name`.

##### The attribute filter

The `attribute` filter can accept two types of values:

- A dictionary whose keys are attributes names (see below). For this case, you can specify an alias for the metric that becomes the metric name in Datadog. You can also specify the metric type as a gauge or counter. If you choose counter, a rate per second is computed for the metric.

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

- A list of attributes names (see below). For this case, the metric type is a gauge, and the metric name is `jmx.\[DOMAIN_NAME].\[ATTRIBUTE_NAME]`.

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

```yaml
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
```

#### Log collection


1. To submit logs to Datadog, Tomcat uses the `log4j` logger. For versions of Tomcat before 8.0, `log4j` is configured by default. For Tomcat 8.0+, you must configure Tomcat to use `log4j`, see [Using Log4j][8]. In the first step of those instructions, edit the `log4j.properties` file in the `$CATALINA_BASE/lib` directory as follows:

   ```conf
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
   Then follow the remaining steps in [the Tomcat docs][8] for configuring `log4j`.

2. By default, Datadog's integration pipeline support the following conversion patterns:

   ```text
     %d{yyyy-MM-dd HH:mm:ss} %-5p %c{1}:%L - %m%n
     %d [%t] %-5p %c - %m%n
   ```

    Clone and edit the [integration pipeline][9] if you have a different format. See [Logging in Tomcat][10] for details on Tomcat logging capabilities.

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
       service: "<SERVICE>"
       #To handle multi line that starts with yyyy-mm-dd use the following pattern
       #log_processing_rules:
       #  - type: multi_line
       #    name: log_start_with_date
       #    pattern: \d{4}\-(0?[1-9]|1[012])\-(0?[1-9]|[12][0-9]|3[01])
   ```

    Change the `path` and `service` parameter values and configure them for your environment. See the [sample tomcat.yaml][5] for all available configuration options.

5. [Restart the Agent][6].

<!-- xxz tab xxx -->
<!-- xxx tab "Containerized" xxx -->

#### Containerized

For containerized environments, see the [Autodiscovery with JMX][11] guide.

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

### Validation

[Run the Agent's status subcommand][12] and look for `tomcat` under the **Checks** section.

## Data Collected

### Metrics

See [metadata.csv][13] for a list of metrics provided by this check.

### Events

The Tomcat check does not include any events.

### Service Checks

See [service_checks.json][14] for a list of service checks provided by this integration.

## Troubleshooting

### Missing `tomcat.*` metrics
The integration collects default Tomcat metrics from the `Catalina` bean domain name. If exposed Tomcat metrics are prefixed with a different bean domain name, such as `Tomcat`, copy the default metrics from the `metrics.yaml` to the `conf` section of the `tomcat.d/conf.yaml` and modify the `domain` filter to use the applicable bean domain name. 

```yaml
- include:
    domain: Tomcat      # default: Catalina
    type: ThreadPool
    attribute:
      maxThreads:
        alias: tomcat.threads.max
        metric_type: gauge
      currentThreadCount:
        alias: tomcat.threads.count
        metric_type: gauge
      currentThreadsBusy:
        alias: tomcat.threads.busy
        metric_type: gauge
```

See the [JMX Check documentation][7] for more detailed information.

### Commands to view the available metrics

The `datadog-agent jmx` command was added in version 4.1.0.

- List attributes that match at least one of your instance configurations:
  `sudo /etc/init.d/datadog-agent jmx list_matching_attributes`
- List attributes that match one of your instance configurations but that are not collected because it would exceed the number of metrics that can be collected:
  `sudo /etc/init.d/datadog-agent jmx list_limited_attributes`
- List attributes that are actually collected by your current instance configurations:
  `sudo /etc/init.d/datadog-agent jmx list_collected_attributes`
- List attributes that don't match any of your instance configurations:
  `sudo /etc/init.d/datadog-agent jmx list_not_matching_attributes`
- List every attribute available that has a type supported by JMXFetch:
  `sudo /etc/init.d/datadog-agent jmx list_everything`
- Start the collection of metrics based on your current configuration and display them in the console:
  `sudo /etc/init.d/datadog-agent jmx collect`

## Further Reading

Additional helpful documentation, links, and articles:

- [Monitor Tomcat metrics with Datadog][15]
- [Key metrics for monitoring Tomcat][16]

[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/tomcat/images/tomcat_dashboard.png
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://tomcat.apache.org/tomcat-6.0-doc/monitoring.html
[4]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[5]: https://github.com/DataDog/integrations-core/blob/master/tomcat/datadog_checks/tomcat/data/conf.yaml.example
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[7]: https://docs.datadoghq.com/integrations/java/
[8]: https://tomcat.apache.org/tomcat-8.0-doc/logging.html#Using_Log4j
[9]: https://docs.datadoghq.com/logs/processing/#integration-pipelines
[10]: https://tomcat.apache.org/tomcat-7.0-doc/logging.html
[11]: https://docs.datadoghq.com/agent/guide/autodiscovery-with-jmx/?tab=containerizedagent
[12]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[13]: https://github.com/DataDog/integrations-core/blob/master/tomcat/metadata.csv
[14]: https://github.com/DataDog/integrations-core/blob/master/tomcat/assets/service_checks.json
[15]: https://www.datadoghq.com/blog/monitor-tomcat-metrics
[16]: https://www.datadoghq.com/blog/tomcat-architecture-and-performance
