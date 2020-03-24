# Agent Check: Apache Web Server

![Apache Dashboard][1]

## Overview

The Apache check tracks requests per second, bytes served, number of worker threads, service uptime, and more.

## Setup

### Installation

The Apache check is packaged with the Agent. To start gathering your Apache metrics and logs, you need to:

1. [Install the Agent][2] on your Apache servers.

2. Install `mod_status` on your Apache servers and enable `ExtendedStatus`.

### Configuration

#### Host

Follow the instructions below to configure this check for an Agent running on a host. For containerized environments, see the [Containerized](#containerized) section.

##### Metric collection

1. Edit the `apache.d/conf.yaml` file in the `conf.d/` folder at the root of your [Agent's configuration directory][3] to start collecting your Apache metrics. See the [sample apache.d/conf.yaml][4] for all available configuration options.

   ```yaml
   init_config:

   instances:
     ## @param apache_status_url - string - required
     ## Status url of your Apache server.
     #
     - apache_status_url: http://localhost/server-status?auto
   ```

2. [Restart the Agent][5].

##### Log collection

_Available for Agent versions >6.0_

1. Collecting logs is disabled by default in the Datadog Agent, you need to enable it in `datadog.yaml`:

   ```yaml
   logs_enabled: true
   ```

2. Add this configuration block to your `apache.d/conf.yaml` file to start collecting your Apache Logs:

   ```yaml
   logs:
     - type: file
       path: /var/log/apache2/access.log
       source: apache
       service: apache

     - type: file
       path: /var/log/apache2/error.log
       source: apache
       service: apache
   ```

    Change the `path` and `service` parameter values and configure them for your environment. See the [sample apache.d/conf.yaml][4] for all available configuration options.

3. [Restart the Agent][5].

#### Containerized

For containerized environments, see the [Autodiscovery Integration Templates][6] for guidance on applying the parameters below.

##### Metric collection

| Parameter            | Value                                                         |
| -------------------- | ------------------------------------------------------------- |
| `<INTEGRATION_NAME>` | `apache`                                                      |
| `<INIT_CONFIG>`      | blank or `{}`                                                 |
| `<INSTANCE_CONFIG>`  | `{"apache_status_url": "http://%%host%%/server-status?auto"}` |

##### Log collection

_Available for Agent versions >6.0_

Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Docker log collection][7].

| Parameter      | Value                                               |
| -------------- | --------------------------------------------------- |
| `<LOG_CONFIG>` | `{"source": "apache", "service": "<SERVICE_NAME>"}` |

### Validation

[Run the Agent's status subcommand][8] and look for `apache` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][9] for a list of metrics provided by this check.

### Events

The Apache check does not include any events.

### Service Checks

**apache.can_connect**:<br>
Returns `CRITICAL` if the Agent cannot connect to the configured `apache_status_url`, otherwise returns `OK`.

## Troubleshooting

### Apache status URL

If you are having issues with your Apache integration, it is mostly like due to the Agent not being able to access your Apache status URL. Try running curl for the `apache_status_url` listed in [your `apache.d/conf.yaml` file][4] (include your login credentials if applicable).

- [Apache SSL certificate issues][10]

## Further Reading

Additional helpful documentation, links, and articles:

- [Deploying and configuring Datadog with CloudFormation][11]
- [Monitoring Apache web server performance][12]
- [How to collect Apache performance metrics][13]
- [How to monitor Apache web server with Datadog][14]

[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/apache/images/apache_dashboard.png
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[4]: https://github.com/DataDog/integrations-core/blob/master/apache/datadog_checks/apache/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/autodiscovery/integrations
[7]: https://docs.datadoghq.com/agent/docker/log/
[8]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[9]: https://github.com/DataDog/integrations-core/blob/master/apache/metadata.csv
[10]: https://docs.datadoghq.com/integrations/faq/apache-ssl-certificate-issues
[11]: https://www.datadoghq.com/blog/deploying-datadog-with-cloudformation
[12]: https://www.datadoghq.com/blog/monitoring-apache-web-server-performance
[13]: https://www.datadoghq.com/blog/collect-apache-performance-metrics
[14]: https://www.datadoghq.com/blog/monitor-apache-web-server-datadog
