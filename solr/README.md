# Solr Check

![Solr Graph][1]

## Overview

The Solr check tracks the state and performance of a Solr cluster. It collects metrics for the number of documents indexed, cache hits and evictions, average request times, average requests per second, and more.

## Setup

### Installation

The Solr check is included in the [Datadog Agent][2] package, so you don't need to install anything else on your Solr nodes.

This check is JMX-based, so you need to enable JMX Remote on your Solr servers. See the [JMX Check documentation][3] for more details.

### Configuration

<!-- xxx tabs xxx -->
<!-- xxx tab "Host" xxx -->

#### Host

To configure this check for an Agent running on a host:

1. Edit the `solr.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][4]. See the [sample solr.d/conf.yaml][5] for all available configuration options.

   ```yaml
   init_config:

     ## @param is_jmx - boolean - required
     ## Whether or not this file is a configuration for a JMX integration.
     #
     is_jmx: true

     ## @param collect_default_metrics - boolean - required
     ## Whether or not the check should collect all default metrics.
     #
     collect_default_metrics: true
    
   instances:
     ## @param host - string - required
     ## Solr host to connect to.
     - host: localhost

       ## @param port - integer - required
       ## Solr port to connect to.
       port: 9999
   ```

2. [Restart the Agent][6].

#### List of metrics

The `conf` parameter is a list of metrics to be collected by the integration. Only 2 keys are allowed:

- `include` (**mandatory**): A dictionary of filters, any attribute that matches these filters are collected unless it also matches the `exclude` filters (see below).
- `exclude` (**optional**): A dictionary of filters, attributes that match these filters are not collected.

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

<!-- xxz tab xxx -->
<!-- xxx tab "Containerized" xxx -->

#### Containerized

For containerized environments, see the [Autodiscovery with JMX][7] guide.

##### Log collection

1. Collecting logs is disabled by default in the Datadog Agent, enable it in your `datadog.yaml` file:

      ```yaml
       logs_enabled: true
     ```

2. Solr uses the `log4j` logger by default. To customize the logging format, edit the [`server/resources/log4j2.xml`][8] file. By default, Datadog's integration pipeline supports the following conversion [pattern][9]:

   ```text
   %maxLen{%d{yyyy-MM-dd HH:mm:ss.SSS} %-5p (%t) [%X{collection} %X{shard} %X{replica} %X{core}] %c{1.} %m%notEmpty{ =>%ex{short}}}{10240}%n
   ```

    Clone and edit the [integration pipeline][10] if you have a different format.


3. Uncomment and edit the logs configuration block in your `solr.d/conf.yaml` file. Change the `type`, `path`, and `service` parameter values based on your environment. See the [sample solr.d/solr.yaml][5] for all available configuration options.

      ```yaml
       logs:
         - type: file
           path: /var/solr/logs/solr.log
           source: solr
           # To handle multi line that starts with yyyy-mm-dd use the following pattern
           # log_processing_rules:
           #   - type: multi_line
           #     pattern: \d{4}\-(0?[1-9]|1[012])\-(0?[1-9]|[12][0-9]|3[01])
           #     name: new_log_start_with_date
     ```

4. [Restart the Agent][6].

To enable logs for Kubernetes environments, see [Kubernetes Log Collection][11].

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

### Validation

[Run the Agent's status subcommand][12] and look for `solr` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][13] for a list of metrics provided by this check.

### Events

The Solr check does not include any events.

### Service Checks

See [service_checks.json][14] for a list of service checks provided by this integration.

## Troubleshooting

### Commands to view the available metrics

The `datadog-agent jmx` command was added in version 4.1.0.

- List attributes that match at least one of your instances configuration:
  `sudo datadog-agent jmx list matching`
- List attributes that do match one of your instances configuration but that are not being collected because it would exceed the number of metrics that can be collected:
  `sudo datadog-agent jmx list limited`
- List attributes expected to be collected by your current instances configuration:
  `sudo datadog-agent jmx list collected`
- List attributes that don't match any of your instances configuration:
  `sudo datadog-agent jmx list not-matching`
- List every attributes available that has a type supported by JMXFetch:
  `sudo datadog-agent jmx list everything`
- Start the collection of metrics based on your current configuration and display them in the console:
  `sudo datadog-agent jmx collect`

## Further Reading

### Parsing a string value into a number

If your jmxfetch returns only string values like **false** and **true** and you want to transform it into a Datadog gauge metric for advanced usages. For instance if you want the following equivalence for your jmxfetch:

```text
"myJmxfetch:false" = myJmxfetch:0
"myJmxfetch:true" = myJmxfetch:1
```

You may use the `attribute` filter as follow:

```yaml
# ...
attribute:
  myJmxfetch:
    alias: your_metric_name
    metric_type: gauge
    values:
      "false": 0
      "true": 1
```

[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/solr/images/solrgraph.png
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/integrations/java/
[4]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[5]: https://github.com/DataDog/integrations-core/blob/master/solr/datadog_checks/solr/data/conf.yaml.example
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[7]: https://docs.datadoghq.com/agent/guide/autodiscovery-with-jmx/?tab=containerizedagent
[8]: https://lucene.apache.org/solr/guide/configuring-logging.html#permanent-logging-settings
[9]: https://logging.apache.org/log4j/2.x/manual/layouts.html#Patterns
[10]: https://docs.datadoghq.com/logs/processing/#integration-pipelines
[11]: https://docs.datadoghq.com/agent/docker/log/
[12]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[13]: https://github.com/DataDog/integrations-core/blob/master/solr/metadata.csv
[14]: https://github.com/DataDog/integrations-core/blob/master/solr/assets/service_checks.json
