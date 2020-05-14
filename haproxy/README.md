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

The Agent collects metrics via a stats endpoint:

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

2. [Restart HAProxy to enable the stats endpoint][3].

### Configuration

#### Host

Follow the instructions below to configure this check for an Agent running on a host. For containerized environments, see the [Containerized](#containerized) section.

Edit the `haproxy.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][4] to start collecting your HAProxy [metrics](#metric-collection) and [logs](#log-collection). See the [sample haproxy.d/conf.yaml][5] for all available configuration options.

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

_Available for Agent versions >6.0_

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

    Change the `service` parameter value and configure it for your environment. See the [sample haproxy.d/conf.yaml][5] for all available configuration options.

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

#### Containerized

For containerized environments, see the [Autodiscovery Integration Templates][7] for guidance on applying the parameters below.

##### Metric collection

| Parameter            | Value                                     |
| -------------------- | ----------------------------------------- |
| `<INTEGRATION_NAME>` | `haproxy`                                 |
| `<INIT_CONFIG>`      | blank or `{}`                             |
| `<INSTANCE_CONFIG>`  | `{"url": "https://%%host%%/admin?stats"}` |

##### Log collection

_Available for Agent versions >6.0_

Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Kubernetes log collection documentation][8].

| Parameter      | Value                                                |
| -------------- | ---------------------------------------------------- |
| `<LOG_CONFIG>` | `{"source": "haproxy", "service": "<SERVICE_NAME>"}` |

### Validation

[Run the Agent's status subcommand][9] and look for `haproxy` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][10] for a list of metrics provided by this integration.

### Events

The Haproxy check does not include any events.

### Service Checks

**haproxy.backend_up**:<br>
Converts the HAProxy status page into service checks.
Returns `CRITICAL` for a given service if HAProxy is reporting it `down`.
Returns `OK` for `maint`, `ok` and any other state.

## Troubleshooting

Need help? Contact [Datadog support][11].

## Further Reading

- [Monitoring HAProxy performance metrics][12]
- [How to collect HAProxy metrics][13]
- [Monitor HAProxy with Datadog][14]
- [HA Proxy Multi Process Configuration][15]
- [How to collect HAProxy metrics][13]

[1]: https://raw.githubusercontent.com/DataDog/integrations-core/39f2cb0977c0e0446a0e905d15d2e9a4349b3b5d/haproxy/images/haproxy-dash.png
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://www.haproxy.org/download/1.7/doc/management.txt
[4]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[5]: https://github.com/DataDog/integrations-core/blob/master/haproxy/datadog_checks/haproxy/data/conf.yaml.example
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[7]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[8]: https://docs.datadoghq.com/agent/kubernetes/log/
[9]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[10]: https://github.com/DataDog/integrations-core/blob/master/haproxy/metadata.csv
[11]: https://docs.datadoghq.com/help/
[12]: https://www.datadoghq.com/blog/monitoring-haproxy-performance-metrics
[13]: https://www.datadoghq.com/blog/how-to-collect-haproxy-metrics
[14]: https://www.datadoghq.com/blog/monitor-haproxy-with-datadog
[15]: https://docs.datadoghq.com/integrations/faq/haproxy-multi-process/
