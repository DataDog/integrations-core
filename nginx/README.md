# Agent Check: Nginx

## Overview

The Datadog Agent can collect many metrics from NGINX instances, including (but not limited to)::

- Total requests
- Connections (e.g. accepted, handled, active)

For users of NGINX Plus, the commercial version of NGINX, the Agent can collect the significantly more metrics that NGINX Plus provides, like:

- Errors (e.g. 4xx codes, 5xx codes)
- Upstream servers (e.g. active connections, 5xx codes, health checks, etc.)
- Caches (e.g. size, hits, misses, etc.)
- SSL (e.g. handshakes, failed handshakes, etc.)


## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For
containerized environments, see the [Autodiscovery Integration Templates][1] for guidance on applying these
instructions.

### Installation

The NGINX check pulls metrics from a local NGINX status endpoint, so your `nginx` binaries need to have been compiled with one of two NGINX status modules:

- [stub status module][2] - for open source NGINX
- [http status module][3] - only for NGINX Plus

#### NGINX Open Source

If you use open source NGINX, your instances may lack the stub status module. Verify that your `nginx` binary includes the module before proceeding to **Configuration**:
```shell
$ nginx -V 2>&1| grep -o http_stub_status_module
http_stub_status_module
```

If the command output does not include `http_stub_status_module`, you must install an NGINX package that includes the module. You _can_ compile your own NGINX-enabling the module as you compile it-but most modern Linux distributions provide alternative NGINX packages with various combinations of extra modules built in. Check your operating system's NGINX packages to find one that includes the stub status module.


#### NGINX Plus

NGINX Plus packages prior to release 13 include the http status module. For NGINX Plus release 13 and above, the status module is deprecated and you must use the new Plus API instead. See [the announcement][4] for more information.

[4]: https://www.nginx.com/blog/nginx-plus-r13-released


#### Prepare NGINX

On each NGINX server, create a `status.conf` file in the directory that contains your other NGINX configuration files (e.g. `/etc/nginx/conf.d/`).

```conf
server {
  listen 81;
  server_name localhost;

  access_log off;
  allow 127.0.0.1;
  deny all;

  location /nginx_status {
    # Choose your status module

    # freely available with open source NGINX
    stub_status;

    # for open source NGINX < version 1.7.5
    # stub_status on;

    # available only with NGINX Plus
    # status;

    # ensures the version information can be retrieved
    server_tokens on;
  }
}
```
**NGINX Plus**

NGINX Plus users can also utilize `stub_status`, but since that module provides fewer metrics, Datadog recommends using `status`.

For NGINX Plus releases 15+, the `status` module is deprecated. Use the [http_api_module][5] instead. For example, enable the `/api` endpoint in your main NGINX configuration file (`/etc/nginx/conf.d/default.conf`):

```conf
server {
  listen 8080;
  location /api {
    api write=on;
  }
}
```

To get more detailed metrics with NGINX Plus (such as 2xx / 3xx / 4xx / 5xx response counts per second), set a `status_zone` on the servers you want to monitor. For example:

```conf
server {
  listen 80;
  status_zone <ZONE_NAME>;
  ...
}
```

Reload NGINX to enable the status or API endpoint. There's no need for a full restart.

```shell
sudo nginx -t && sudo nginx -s reload
```


### Configuration



<!-- xxx tabs xxx -->
<!-- xxx tab "Host" xxx -->

#### Host

To configure this check for an Agent running on a host:

Follow the instructions below to configure this check for an Agent running on a host. For containerized environments, see the [Containerized section][4].


<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

#### Metric collection

1. Set the `nginx_status_url` parameter to `http://localhost:81/nginx_status/` in your `nginx.d/conf.yaml` file to start gathering your [NGINX metrics][5]. See the [sample nginx.d/conf.yaml][6] for all available configuration options.

    **NGINX Plus**:

      - For NGINX Plus releases 13+, set the parameter `use_plus_api` to `true` in your `nginx.d/conf.yaml` configuration file.
      - Stream stats API calls are included by default for NGINX Plus. If you want to disable them, set the parameter `use_plus_api_stream` to `false` in your `nginx.d/conf.yaml` configuration file.
      - If you are using `http_api_module`, set the parameter `nginx_status_url` to the server's `/api` location in your `nginx.d/conf.yaml` configuration file, for example:

          ```yaml
          nginx_status_url: http://localhost:8080/api
          ```

2. Optional - If you are using the NGINX `vhost_traffic_status module`, set the parameter `use_vts` to `true` in your `nginx.d/conf.yaml` configuration file.

3. [Restart the Agent][7] to start sending NGINX metrics to Datadog.

[7]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent


#### Log collection


1. Collecting logs is disabled by default in the Datadog Agent, enable it in your `datadog.yaml` file:

    ```yaml
    logs_enabled: true
    ```

2. Edit this configuration block in your `nginx.d/conf.yaml` file to start collecting your Nginx logs:

    ```yaml
        logs:
          - type: file
            path: /var/log/nginx/access.log
            service: nginx
            source: nginx

          - type: file
            path: /var/log/nginx/error.log
            service: nginx
            source: nginx
      ```


    Change the `path` parameter value based on your environment. See the [sample conf.yaml][6] for all available configuration options.

3. [Restart the Agent][1].

See [Datadog's documentation][2] for additional information on how to configure the Agent for log collection in Kubernetes environments.

[1]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[2]: https://docs.datadoghq.com/agent/kubernetes/log/


<!-- xxx tabs xxx -->
<!-- xxx tab "Containerized" xxx -->

#### Containerized

For containerized environments, see the [Autodiscovery Integration Templates][8] for guidance on applying the parameters below.
[8]: https://docs.datadoghq.com/agent/kubernetes/integrations/


<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

#### Metric collection

| Parameter            | Value                                                      |
| -------------------- | ---------------------------------------------------------- |
| `<INTEGRATION_NAME>` | `nginx`                                                    |
| `<INIT_CONFIG>`      | blank or `{}`                                              |
| `<INSTANCE_CONFIG>`  | `{"nginx_status_url": "http://%%host%%:81/nginx_status/"}` |

**Note**: This `<INSTANCE_CONFIG>` configuration works only with NGINX Open Source. If you are using NGINX Plus, inline the corresponding instance configuration.


#### Log collection

_Available for Agent versions >6.0_

Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Kubernetes log collection documentation][9].

| Parameter      | Value                                     |
| -------------- | ----------------------------------------- |
| `<LOG_CONFIG>` | `{"source": "nginx", "service": "nginx"}` |

[9]: https://docs.datadoghq.com/agent/kubernetes/log/


### Validation

[Run the Agent's status subcommand][7] and look for `nginx` under the Checks section.

## Data Collected



### Metrics

See [metadata.csv][8] for a list of metrics provided by this check.

### Events

Nginx does not include any events.

### Service Checks

**nginx.can_connect**:<br>
Returns `CRITICAL` if the Agent cannot connect to NGINX to collect metrics, otherwise returns `OK`.


## Troubleshooting

Need help? Contact [Datadog support][9].

## Further Reading

Additional helpful documentation, links, and articles:

- [How to monitor NGINX][10]
- [How to collect NGINX metrics][11]
- [How to monitor NGINX with Datadog][12]

[1]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[2]: https://nginx.org/en/docs/http/ngx_http_stub_status_module.html
[3]: https://nginx.org/en/docs/http/ngx_http_status_module.html
[4]: #containerized
[5]: #metrics
[6]: https://github.com/DataDog/integrations-core/blob/master/nginx/datadog_checks/nginx/data/conf.yaml.example
[7]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[8]: https://github.com/DataDog/integrations-core/blob/master/rethinkdb/metadata.csv
[9]: https://docs.datadoghq.com/help/
[10]: https://www.datadoghq.com/blog/how-to-monitor-nginx
[11]: https://www.datadoghq.com/blog/how-to-collect-nginx-metrics/index.html
[12]: https://www.datadoghq.com/blog/how-to-monitor-nginx-with-datadog/index.html