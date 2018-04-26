# Agent Check: Tomcat

## Overview

This check collects Tomcat metrics like:

* Overall activity metrics: error count, request count, processing times
* Thread pool metrics: thread count, number of threads busy
* Servlet processing times

And more.

## Setup
### Installation

The Tomcat check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your Tomcat servers.

This check is JMX-based, so you'll need to enable JMX Remote on your Tomcat servers. Follow the instructions in the [Tomcat documentation](http://tomcat.apache.org/tomcat-6.0-doc/monitoring.html) to do that.

### Configuration

Create a file `tomcat.yaml` in the Agent's `conf.d` directory. 

#### Metric Collection

*  Add this configuration setup to your `tomcat.yaml` file to start gathering your [Tomcat metrics](#metrics):

```
instances:
    -   host: localhost
        port: 7199
        user: <TOMCAT_USERNAME>
        password: <PASSWORD>
        name: my_tomcat

init_config:
  conf:
    - include:
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
    - include:
        type: GlobalRequestProcessor
        attribute:
          bytesSent:
            alias: tomcat.bytes_sent
            metric_type: counter
          bytesReceived:
            alias: tomcat.bytes_rcvd
            metric_type: counter
          errorCount:
            alias: tomcat.error_count
            metric_type: counter
          requestCount:
            alias: tomcat.request_count
            metric_type: counter
          maxTime:
            alias: tomcat.max_time
            metric_type: gauge
          processingTime:
            alias: tomcat.processing_time
            metric_type: counter
    - include:
        j2eeType: Servlet
        attribute:
          processingTime:
            alias: tomcat.servlet.processing_time
            metric_type: counter
          errorCount:
            alias: tomcat.servlet.error_count
            metric_type: counter
          requestCount:
            alias: tomcat.servlet.request_count
            metric_type: counter
    - include:
        type: Cache
        accessCount:
          alias: tomcat.cache.access_count
          metric_type: counter
        hitsCounts:
          alias: tomcat.cache.hits_count
          metric_type: counter
    - include:
        type: JspMonitor
        jspCount:
          alias: tomcat.jsp.count
          metric_type: counter
        jspReloadCount:
          alias: tomcat.jsp.reload_count
          metric_type: counter
```

See the [JMX Check documentation](http://docs.datadoghq.com/integrations/java/) for a list of configuration options usable by all JMX-based checks. The page also describes how the Agent tags JMX metrics.

[Restart the Agent](https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent) to start sending Tomcat metrics to Datadog.

Configuration Options:

* `user` and `password` (Optional) - Username and password.
* `process_name_regex` - (Optional) - Instead of specifying a host and port or jmx_url, the agent can connect using the attach api. This requires the JDK to be installed and the path to tools.jar to be set.
* `tools_jar_path` - (Optional) - To be set when process_name_regex is set.
* `java_bin_path` - (Optional) - Should be set if the agent cannot find your java executable.
* `java_options` - (Optional) - Java JVM options
* `trust_store_path` and `trust_store_password` - (Optional) - Should be set if ssl is enabled.

The `conf` parameter is a list of dictionaries. Only 2 keys are allowed in this dictionary:

* `include` (**mandatory**): Dictionary of filters, any attribute that matches these filters will be collected unless it also matches the "exclude" filters (see below)
* `exclude` (**optional**): Another dictionary of filters. Attributes that match these filters won't be collected

For a given bean, metrics get tagged in the following manner:

    mydomain:attr0=val0,attr1=val1

Your metric will be mydomain (or some variation depending on the attribute inside the bean) and have the tags `attr0:val0, attr1:val1, domain:mydomain`.

If you specify an alias in an `include` key that is formatted as *camel case*, it will be converted to *snake case*. For example, `MyMetricName` will be shown in Datadog as `my_metric_name`.

  See the [sample tomcat.yaml](https://github.com/DataDog/integrations-core/blob/master/tomcat/conf.yaml.example) for all available configuration options.

##### The `attribute` filter

The `attribute` filter can accept two types of values:

* A dictionary whose keys are attributes names:

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

In that case you can specify an alias for the metric that will become the metric name in Datadog. You can also specify the metric type either a gauge or a counter. If you choose counter, a rate per second will be computed for this metric.

* A list of attributes names:

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

In that case:

  * The metric type will be a gauge
  * The metric name will be jmx.\[DOMAIN_NAME].\[ATTRIBUTE_NAME]

Here is another filtering example:

    instances:
      - host: 127.0.0.1
        name: jmx_instance
        port: 9999

    init_config:
      conf:
        - include:
            bean: org.apache.cassandra.metrics:type=ClientRequest,scope=Write,name=Latency
            attribute:
              - OneMinuteRate
              - 75thPercentile
              - 95thPercentile
              - 99thPercentile


#### Note

List of filters is only supported in Datadog Agent > 5.3.0. If you are using an older version, please use singletons and multiple `include` statements instead.

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

#### Log Collection

**Available for Agent >6.0**

Tomcat uses by default the `log4j` logger. To activate the logging into a file and customize the log format edit the `log4j.properties` file in the `$CATALINA_BASE/lib` directory as follows:

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

Check Tomcat [logging documentation](http://tomcat.apache.org/tomcat-7.0-doc/logging.html) for more information about Tomcat logging capabilities.

By default, our integration pipeline support the following conversion patterns:

  ```
  %d{yyyy-MM-dd HH:mm:ss} %-5p %c{1}:%L - %m%n
  %d [%t] %-5p %c - %m%n
  ```

Make sure you clone and edit the [integration pipeline](https://docs.datadoghq.com/logs/processing/#integration-pipelines) if you have a different format.

* Collecting logs is disabled by default in the Datadog Agent, enable it in your `datadog.yaml` file with:

  ```
  logs_enabled: true
  ```

* Add this configuration setup to your `tomcat.yaml` file to start collecting your Tomcat Logs:

  ```
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

  Change the `path` and `service` parameter values and configure them for your environment.
    see the [sample tomcat.yaml](https://github.com/DataDog/integrations-core/blob/master/tomcat/conf.yaml.example) for all available configuration options.
    * [Restart the Agent](https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent). 

### Validation

[Run the Agent's `status` subcommand](https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information) and look for `tomcat` under the Checks section.

## Data Collected
### Metrics
See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/tomcat/metadata.csv) for a list of metrics provided by this check.

### Events
The Tomcat check does not include any event at this time.

### Service Checks

**tomcat.can_connect**

Returns `CRITICAL` if the Agent is unable to connect to and collect metrics from the monitored Tomcat instance. Returns `OK` otherwise.


## Troubleshooting
### Commands to view the metrics that are available:

The `datadog-agent jmx` command was added in version 4.1.0.

  * List attributes that match at least one of your instances configuration:
`sudo /etc/init.d/datadog-agent jmx list_matching_attributes`
  * List attributes that do match one of your instances configuration but that are not being collected because it would exceed the number of metrics that can be collected:
`sudo /etc/init.d/datadog-agent jmx list_limited_attributes`
  * List attributes that will actually be collected by your current instances configuration:
`sudo /etc/init.d/datadog-agent jmx list_collected_attributes`
  * List attributes that don't match any of your instances configuration:
`sudo /etc/init.d/datadog-agent jmx list_not_matching_attributes`
  * List every attributes available that has a type supported by JMXFetch:
`sudo /etc/init.d/datadog-agent jmx list_everything`
  * Start the collection of metrics based on your current configuration and display them in the console:
`sudo /etc/init.d/datadog-agent jmx collect`

## Further Reading

* [Monitor Tomcat metrics with Datadog](https://www.datadoghq.com/blog/monitor-tomcat-metrics/)
