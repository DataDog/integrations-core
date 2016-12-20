# Tomcat Integration

## Overview

Get metrics from Tomcat in real time to

* Visualize your web server performance
* Correlate the performance of Tomcat with the rest of your applications

## Installation

To capture Tomcat metrics you need to install the Datadog Agent. Metrics will be captured using a JMX connection. 
We recommend the use of Oracle's JDK for this integration. 

This check has a limit of 350 metrics per instance. The number of returned metrics is indicated in the info page. You can specify the metrics you are interested in by editing the configuration below. To learn how to customize the metrics to collect visit the JMX Checks documentation for more detailed instructions. If you need to monitor more metrics, please send us an email at support@datadoghq.com

1. Make sure that [JMX Remote is enabled](http://tomcat.apache.org/tomcat-6.0-doc/monitoring.html) on your Tomcat server.
2. Configure the Agent to connect to Tomcat
 Edit [conf.d/tomcat.yaml](http://docs.datadoghq.com/guides/basic_agent_usage/)
```
instances:
    -   host: localhost
        port: 7199
        user: username
        password: password
        name: tomcat_instance

# List of metrics to be collected by the integration
# Visit http://docs.datadoghq.com/integrations/java/ to customize it
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

3. Restart the Agent
4. Execute the info command and verify that the integration check has passed. The output of the command should contain a section similar to the following:
```
Checks
======

  [...]

  tomcat
  ------
      - instance #0 [OK]
      - Collected 8 metrics & 0 events
```

## Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        tomcat
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The tomcat check is compatible with all major platforms
