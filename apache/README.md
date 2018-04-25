# Agent Check: Apache Web Server
{{< img src="integrations/apache/apachegraph.png" alt="apache graph" responsive="true" popup="true">}}
## Overview

The Apache check tracks requests per second, bytes served, number of worker threads, service uptime, and more.

## Setup
### Installation

The Apache check is packaged with the Agent. To start gathering your Apache metrics and logs, you need to:

1. [Install the Agent](https://app.datadoghq.com/account/settings#agent) on your Apache servers.
  

2. Install `mod_status` on your Apache servers and enable `ExtendedStatus`.

### Configuration

Create a file `apache.yaml` in the Agent's `conf.d` directory.

#### Metric Collection

*  Add this configuration setup to your `apache.yaml` file to start gathering your [Apache Metrics](#metrics):

  ```
  init_config:

  instances:
    - apache_status_url: http://example.com/server-status?auto
  #   apache_user: example_user # if apache_status_url needs HTTP basic auth
  #   apache_password: example_password
  #   disable_ssl_validation: true # if you need to disable SSL cert validation, i.e. for self-signed certs
  ```
  Change the `apache_status_url` parameter value and configure it for your environment.
  See the [sample apache.yaml](https://github.com/DataDog/integrations-core/blob/master/apache/conf.yaml.example) for all available configuration options.

*  [Restart the Agent](https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent).

#### Log Collection

**Available for Agent >6.0**

* Collecting logs is disabled by default in the Datadog Agent, you need to enable it in `datadog.yaml`:

  ```
  logs_enabled: true
  ```

* Add this configuration setup to your `apache.yaml` file to start collecting your Apache Logs:

  ```
    logs:
        - type: file
          path: /var/log/apache2/access.log
          source: apache
          sourcecategory: http_web_access
          service: apache

        - type: file
          path: /var/log/apache2/error.log
          source: apache
          sourcecategory: http_web_access
          service: apache
  ```

  Change the `path` and `service` parameter values and configure them for your environment.
  See the [sample apache.yaml](https://github.com/DataDog/integrations-core/blob/master/apache/conf.yaml.example) for all available configuration options.

* [Restart the Agent](https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent).

**Learn more about log collection [on the log documentation](https://docs.datadoghq.com/logs)**

### Validation

[Run the Agent's `status` subcommand](https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information) and look for `apache` under the Checks section.

## Compatibility

The Apache check is compatible with all major platforms.

## Data Collected
### Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/apache/metadata.csv) for a list of metrics provided by this check.

### Events
The Apache check does not include any event at this time.

### Service Checks

**apache.can_connect**:

Returns CRITICAL if the Agent cannot connect to the configured `apache_status_url`, otherwise OK.

## Troubleshooting

* [Issues with Apache Integration](https://docs.datadoghq.com/integrations/faq/issues-with-apache-integration)
* [Apache SSL certificate issues](https://docs.datadoghq.com/integrations/faq/apache-ssl-certificate-issues)

## Further Reading

* [Monitoring Apache web server performance](https://www.datadoghq.com/blog/monitoring-apache-web-server-performance/)
* [How to collect Apache performance metrics](https://www.datadoghq.com/blog/collect-apache-performance-metrics/)
* [How to monitor Apache web server with Datadog](https://www.datadoghq.com/blog/monitor-apache-web-server-datadog/)
