# Agent Check: Apache Web Server

![Apache Dashboard][1]

## Overview

The Apache check tracks requests per second, bytes served, number of worker threads, service uptime, and more.

## Setup

### Installation

The Apache check is packaged with the [Datadog Agent][2]. To start gathering your Apache metrics and logs, you need to:

1. [Install the Agent][3] on your Apache servers.

2. Install `mod_status` on your Apache servers and enable `ExtendedStatus`.

### Configuration

<!-- xxx tabs xxx -->
<!-- xxx tab "Host" xxx -->

#### Host

To configure this check for an Agent running on a host:

##### Metric collection

1. Edit the `apache.d/conf.yaml` file in the `conf.d/` folder at the root of your [Agent's configuration directory][4] to start collecting your Apache metrics. See the [sample apache.d/conf.yaml][5] for all available configuration options.

   ```yaml
   init_config:

   instances:
     ## @param apache_status_url - string - required
     ## Status url of your Apache server.
     #
     - apache_status_url: http://localhost/server-status?auto
   ```

2. [Restart the Agent][6].

##### Log collection

_Available for Agent versions >6.0_

1. Collecting logs is disabled by default in the Datadog Agent. Enable it in `datadog.yaml`:

   ```yaml
   logs_enabled: true
   ```

2. Add this configuration block to your `apache.d/conf.yaml` file to start collecting your Apache logs, adjusting the `path` and `service` values to configure them for your environment:

   ```yaml
   logs:
     - type: file
       path: /path/to/your/apache/access.log
       source: apache
       service: apache
       sourcecategory: http_web_access

     - type: file
       path: /path/to/your/apache/error.log
       source: apache
       service: apache
       sourcecategory: http_web_error
   ```

    See the [sample apache.d/conf.yaml][5] for all available configuration options.

3. [Restart the Agent][6].

<!-- xxz tab xxx -->
<!-- xxx tab "Docker" xxx -->

#### Docker

To configure this check for an Agent running on a container:

##### Metric collection

Set [Autodiscovery Integrations Templates][7] as Docker labels on your application container:

```yaml
LABEL "com.datadoghq.ad.check_names"='["apache"]'
LABEL "com.datadoghq.ad.init_configs"='[{}]'
LABEL "com.datadoghq.ad.instances"='[{"apache_status_url": "http://%%host%%/server-status?auto"}]'
```

##### Log collection


Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Docker Log Collection][8].

Then, set [Log Integrations][9] as Docker labels:

```yaml
LABEL "com.datadoghq.ad.logs"='[{"source": "apache", "service": "<SERVICE_NAME>"}]'
```

<!-- xxz tab xxx -->
<!-- xxx tab "Kubernetes" xxx -->

#### Kubernetes

To configure this check for an Agent running on Kubernetes:

##### Metric collection

Set [Autodiscovery Integrations Templates][10] as pod annotations on your application container. Aside from this, templates can also be configured with [a file, a configmap, or a key-value store][11].

**Annotations v1** (for Datadog Agent < v7.36)

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: apache
  annotations:
    ad.datadoghq.com/apache.check_names: '["apache"]'
    ad.datadoghq.com/apache.init_configs: '[{}]'
    ad.datadoghq.com/apache.instances: |
      [
        {
          "apache_status_url": "http://%%host%%/server-status?auto"
        }
      ]
spec:
  containers:
    - name: apache
```

**Annotations v2** (for Datadog Agent v7.36+)

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: apache
  annotations:
    ad.datadoghq.com/apache.checks: |
      {
        "apache": {
          "init_config": {},
          "instances": [
            {
              "apache_status_url": "http://%%host%%/server-status?auto"
            }
          ]
        }
      }
spec:
  containers:
    - name: apache
```

##### Log collection


Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Kubernetes Log Collection][12].

Then, set [Log Integrations][9] as pod annotations. This can also be configured with [a file, a configmap, or a key-value store][13].

**Annotations v1/v2**

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: apache
  annotations:
    ad.datadoghq.com/apache.logs: '[{"source":"apache","service":"<SERVICE_NAME>"}]'
spec:
  containers:
    - name: apache
```


<!-- xxz tab xxx -->
<!-- xxx tab "ECS" xxx -->

#### ECS

To configure this check for an Agent running on ECS:

##### Metric collection

Set [Autodiscovery Integrations Templates][7] as Docker labels on your application container:

```json
{
  "containerDefinitions": [{
    "name": "apache",
    "image": "apache:latest",
    "dockerLabels": {
      "com.datadoghq.ad.check_names": "[\"apache\"]",
      "com.datadoghq.ad.init_configs": "[{}]",
      "com.datadoghq.ad.instances": "[{\"apache_status_url\": \"http://%%host%%/server-status?auto\"}]"
    }
  }]
}
```

##### Log collection


Collecting logs is disabled by default in the Datadog Agent. To enable it, see [ECS Log Collection][14].

Then, set [Log Integrations][9] as Docker labels:

```json
{
  "containerDefinitions": [{
    "name": "apache",
    "image": "apache:latest",
    "dockerLabels": {
      "com.datadoghq.ad.logs": "[{\"source\":\"apache\",\"service\":\"<YOUR_APP_NAME>\"}]"
    }
  }]
}
```

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

### Validation

[Run the Agent's status subcommand][15] and look for `apache` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][16] for a list of metrics provided by this check.

### Events

The Apache check does not include any events.

### Service Checks

See [service_checks.json][17] for a list of service checks provided by this integration.

## Troubleshooting

### Apache status URL

If you are having issues with your Apache integration, it is mostly like due to the Agent not being able to access your Apache status URL. Try running curl for the `apache_status_url` listed in [your `apache.d/conf.yaml` file][5] (include your login credentials if applicable).

- [Apache SSL certificate issues][18]

## Further Reading

Additional helpful documentation, links, and articles:

- [Deploying and configuring Datadog with CloudFormation][19]
- [Monitoring Apache web server performance][20]
- [How to collect Apache performance metrics][21]
- [How to monitor Apache web server with Datadog][22]

[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/apache/images/apache_dashboard.png
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/agent/
[4]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[5]: https://github.com/DataDog/integrations-core/blob/master/apache/datadog_checks/apache/data/conf.yaml.example
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[7]: https://docs.datadoghq.com/agent/docker/integrations/?tab=docker
[8]: https://docs.datadoghq.com/agent/docker/log/?tab=containerinstallation#installation
[9]: https://docs.datadoghq.com/agent/docker/log/?tab=containerinstallation#log-integrations
[10]: https://docs.datadoghq.com/agent/kubernetes/integrations/?tab=kubernetes
[11]: https://docs.datadoghq.com/agent/kubernetes/integrations/?tab=kubernetes#configuration
[12]: https://docs.datadoghq.com/agent/kubernetes/log/?tab=containerinstallation#setup
[13]: https://docs.datadoghq.com/agent/kubernetes/log/?tab=daemonset#configuration
[14]: https://docs.datadoghq.com/agent/amazon_ecs/logs/?tab=linux
[15]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[16]: https://github.com/DataDog/integrations-core/blob/master/apache/metadata.csv
[17]: https://github.com/DataDog/integrations-core/blob/master/apache/assets/service_checks.json
[18]: https://docs.datadoghq.com/integrations/faq/apache-ssl-certificate-issues/
[19]: https://www.datadoghq.com/blog/deploying-datadog-with-cloudformation
[20]: https://www.datadoghq.com/blog/monitoring-apache-web-server-performance
[21]: https://www.datadoghq.com/blog/collect-apache-performance-metrics
[22]: https://www.datadoghq.com/blog/monitor-apache-web-server-datadog
