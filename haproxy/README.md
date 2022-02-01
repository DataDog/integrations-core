# Haproxy Integration

![HAProxy Out of the box Dashboard][1]

## Overview

Capture HAProxy activity in Datadog to:

- Visualize HAProxy load-balancing performance.
- Know when a server goes down.
- Correlate the performance of HAProxy with the rest of your applications.

## Setup

### Installation

The Haproxy check is included in the [Datadog Agent][2] package, so you don't need to install anything else on your Haproxy server.

#### Prepare HAProxy

##### Using Prometheus

The recommended way to set up this integration is by enabling the Prometheus endpoint on HAProxy. This endpoint is built into HAProxy starting with version 2 (enterprise version 1.9rc1). If you are using an older version, consider setting up the [HAProxy Prometheus exporter][3], or alternatively set up the legacy socket-based integration described in the next section.

1. Configure your `haproxy.conf` using the [official guide][4].

2. [Enable](#configuration) the setting `use_prometheus` in `haproxy.d/conf.yaml`.

3. [Restart HAProxy to enable the Prometheus endpoint][5].

4. [Restart the Agent][6].

##### Using the stats endpoint

**Note**: This configuration strategy is provided as a reference for legacy users. If you are setting up the integration for the first time, consider using the Prometheus-based strategy described in the previous section.

The Agent collects metrics using a stats endpoint:

1. Configure one in your `haproxy.conf`:

   ```conf
     listen stats # Define a listen section called "stats"
     bind :9000 # Listen on localhost:9000
     mode http
     stats enable  # Enable stats page
     stats hide-version  # Hide HAProxy version
     stats realm Haproxy\ Statistics  # Title text for popup window
     stats uri /haproxy_stats  # Stats URI
     stats auth Username:Password  # Authentication credentials
   ```

2. [Restart HAProxy to enable the stats endpoint][5].

### Configuration

<!-- xxx tabs xxx -->
<!-- xxx tab "Host" xxx -->

#### Host

To configure this check for an Agent running on a host:

Edit the `haproxy.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][7] to start collecting your HAProxy [metrics](#metric-collection) and [logs](#log-collection). See the [sample haproxy.d/conf.yaml][8] for all available configuration options.

##### Metric collection

1. Add this configuration block to your `haproxy.d/conf.yaml` file to start gathering your [Haproxy Metrics](#metrics):

   ```yaml
   init_config:

   instances:
     ## @param url - string - required
     ## Haproxy URL to connect to gather metrics.
     ## Set the according <USERNAME> and <PASSWORD> or use directly a unix stats
     ## or admin socket: unix:///var/run/haproxy.sock
     #
     - url: http://localhost/admin?stats
   ```

2. [Restart the Agent][6].

##### Log collection

By default Haproxy sends logs over UDP to port 514. The Agent can listen for these logs on this port, however, binding to a port number under 1024 requires elevated permissions. Follow the instructions below to set this up. Alternatively, you can use a different port and skip step 3.

1. Collecting logs is disabled by default in the Datadog Agent, enable it in your `datadog.yaml` file:

   ```yaml
   logs_enabled: true
   ```

2. Add this configuration block to your `haproxy.d/conf.yaml` file to start collecting your Haproxy Logs:

   ```yaml
   logs:
     - type: udp
       port: 514
       service: <SERVICE_NAME>
       source: haproxy
   ```

    Change the `service` parameter value and configure it for your environment. See the [sample haproxy.d/conf.yaml][8] for all available configuration options.

3. Grant access to port 514 using the `setcap` command:

    ```bash
    sudo setcap CAP_NET_BIND_SERVICE=+ep /opt/datadog-agent/bin/agent/agent
    ```

    Verify the setup is correct by running the `getcap` command:

    ```bash
    sudo getcap /opt/datadog-agent/bin/agent/agent
    ```

    With the expected output:
    ```bash
    /opt/datadog-agent/bin/agent/agent = cap_net_bind_service+ep
    ```

    **Note:** Re-run this `setcap` command every time you upgrade the Agent.

4. [Restart the Agent][6].

<!-- xxz tab xxx -->
<!-- xxx tab "Docker" xxx -->

#### Docker

To configure this check for an Agent running on a container:

##### Metric collection

Set [Autodiscovery Integrations Templates][9] as Docker labels on your application container:

```yaml
LABEL "com.datadoghq.ad.check_names"='["haproxy"]'
LABEL "com.datadoghq.ad.init_configs"='[{}]'
LABEL "com.datadoghq.ad.instances"='[{"url": "https://%%host%%/admin?stats"}]'
```

##### Log collection

Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Docker Log Collection][10].

Then, set [Log Integrations][11] as Docker labels:

```yaml
LABEL "com.datadoghq.ad.logs"='[{"source":"haproxy","service":"<SERVICE_NAME>"}]'
```

<!-- xxz tab xxx -->
<!-- xxx tab "Kubernetes" xxx -->

#### Kubernetes

To configure this check for an Agent running on Kubernetes:

##### Metric collection

Set [Autodiscovery Integrations Templates][12] as pod annotations on your application container. Aside from this, templates can also be configured with [a file, a configmap, or a key-value store][13].

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: haproxy
  annotations:
    ad.datadoghq.com/haproxy.check_names: '["haproxy"]'
    ad.datadoghq.com/haproxy.init_configs: '[{}]'
    ad.datadoghq.com/haproxy.instances: |
      [
        {
          "url": "https://%%host%%/admin?stats"
        }
      ]
spec:
  containers:
    - name: haproxy
```

##### Log collection

_Available for Agent versions >6.0_

Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Kubernetes Log Collection][14].

Then, set [Log Integrations][11] as pod annotations. This can also be configured with [a file, a configmap, or a key-value store][15].

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: haproxy
  annotations:
    ad.datadoghq.com/haproxy.logs: '[{"source":"haproxy","service":"<SERVICE_NAME>"}]'
spec:
  containers:
    - name: haproxy
```

<!-- xxz tab xxx -->
<!-- xxx tab "ECS" xxx -->

#### ECS

To configure this check for an Agent running on ECS:

##### Metric collection

Set [Autodiscovery Integrations Templates][9] as Docker labels on your application container:

```json
{
  "containerDefinitions": [{
    "name": "haproxy",
    "image": "haproxy:latest",
    "dockerLabels": {
      "com.datadoghq.ad.check_names": "[\"haproxy\"]",
      "com.datadoghq.ad.init_configs": "[{}]",
      "com.datadoghq.ad.instances": "[{\"url\": \"https://%%host%%/admin?stats\"}]"
    }
  }]
}
```

##### Log collection

_Available for Agent versions >6.0_

Collecting logs is disabled by default in the Datadog Agent. To enable it, see [ECS Log Collection][16].

Then, set [Log Integrations][11] as Docker labels:

```json
{
  "containerDefinitions": [{
    "name": "haproxy",
    "image": "haproxy:latest",
    "dockerLabels": {
      "com.datadoghq.ad.logs": "[{\"source\":\"haproxy\",\"service\":\"<SERVICE_NAME>\"}]"
    }
  }]
}
```

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

### Validation

[Run the Agent's status subcommand][17] and look for `haproxy` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][18] for a list of metrics provided by this integration.

### Events

The Haproxy check does not include any events.

### Service Checks

See [service_checks.json][19] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][20].

## Further Reading

- [Monitoring HAProxy performance metrics][21]
- [How to collect HAProxy metrics][22]
- [Monitor HAProxy with Datadog][23]
- [HA Proxy Multi Process Configuration][24]
- [How to collect HAProxy metrics][22]

[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/haproxy/images/haproxy-dash.png
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://github.com/prometheus/haproxy_exporter
[4]: https://www.haproxy.com/blog/haproxy-exposes-a-prometheus-metrics-endpoint/
[5]: https://www.haproxy.org/download/1.7/doc/management.txt
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[7]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[8]: https://github.com/DataDog/integrations-core/blob/master/haproxy/datadog_checks/haproxy/data/conf.yaml.example
[9]: https://docs.datadoghq.com/agent/docker/integrations/?tab=docker
[10]: https://docs.datadoghq.com/agent/docker/log/?tab=containerinstallation#installation
[11]: https://docs.datadoghq.com/agent/docker/log/?tab=containerinstallation#log-integrations
[12]: https://docs.datadoghq.com/agent/kubernetes/integrations/?tab=kubernetes
[13]: https://docs.datadoghq.com/agent/kubernetes/integrations/?tab=kubernetes#configuration
[14]: https://docs.datadoghq.com/agent/kubernetes/log/?tab=containerinstallation#setup
[15]: https://docs.datadoghq.com/agent/kubernetes/log/?tab=daemonset#configuration
[16]: https://docs.datadoghq.com/agent/amazon_ecs/logs/?tab=linux
[17]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[18]: https://github.com/DataDog/integrations-core/blob/master/haproxy/metadata.csv
[19]: https://github.com/DataDog/integrations-core/blob/master/haproxy/assets/service_checks.json
[20]: https://docs.datadoghq.com/help/
[21]: https://www.datadoghq.com/blog/monitoring-haproxy-performance-metrics
[22]: https://www.datadoghq.com/blog/how-to-collect-haproxy-metrics
[23]: https://www.datadoghq.com/blog/monitor-haproxy-with-datadog
[24]: https://docs.datadoghq.com/integrations/faq/haproxy-multi-process/
