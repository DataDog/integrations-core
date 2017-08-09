# Agent Check: Tomcat

## Overview

This check collects Tomcat metrics like:

* Overall activity metrics: error count, request count, processing times
* Thread pool metrics: thread count, number of threads busy
* Servlet processing times

And more.

## Installation

The Tomcat check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your Tomcat servers.

This check is JMX-based, so you'll need to enable JMX Remote on your Tomcat servers. Follow the instructions in the [Tomcat documentation](http://tomcat.apache.org/tomcat-6.0-doc/monitoring.html) to do that.

## Configuration

Create a file `tomcat.yaml` in the Agent's `conf.d` directory:

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

Restart the Agent to start sending Tomcat metrics to Datadog.

## Validation

Run the Agent's `info` subcommand and look for `tomcat` under the Checks section:

```
  Checks
  ======
    [...]

    tomcat
    -------
      - instance #0 [OK]
      - Collected 26 metrics, 0 events & 0 service checks

    [...]
```

## Compatibility

The tomcat check is compatible with all major platforms.

## Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/tomcat/metadata.csv) for a list of metrics provided by this check.

## Further Reading

See our [blog post](https://www.datadoghq.com/blog/monitor-tomcat-metrics/) about monitoring Tomcat with Datadog.
