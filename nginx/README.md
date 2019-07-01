# NGINX check

![NGINX default dashboard][1]

## Overview

The Datadog Agent can collect many metrics from NGINX instances, including (but not limited to)::

* Total requests
* Connections (e.g. accepted, handled, active)

For users of NGINX Plus, the commercial version of NGINX, the Agent can collect the significantly more metrics that NGINX Plus provides, like:

* Errors (e.g. 4xx codes, 5xx codes)
* Upstream servers (e.g. active connections, 5xx codes, health checks, etc.)
* Caches (e.g. size, hits, misses, etc.)
* SSL (e.g. handshakes, failed handshakes, etc.)

## Setup

### Installation

The NGINX check is included in the [Datadog Agent][2] package, so you don't need to install anything else on your NGINX servers.

### Configuration

The NGINX check pulls metrics from a local NGINX status endpoint, so your `nginx` binaries need to have been compiled with one of two NGINX status modules:

* [stub status module][3] - for open source NGINX
* [http status module][4] - only for NGINX Plus

#### NGINX Open Source

If you use open source NGINX, your instances may lack the stub status module. Verify that your `nginx` binary includes the module before proceeding to **Configuration**:

```
$ nginx -V 2>&1| grep -o http_stub_status_module
http_stub_status_module
```

If the command output does not include `http_stub_status_module`, you must install an NGINX package that includes the module. You _can_ compile your own NGINX-enabling the module as you compile it-but most modern Linux distributions provide alternative NGINX packages with various combinations of extra modules built in. Check your operating system's NGINX packages to find one that includes the stub status module.

#### NGINX Plus 

NGINX Plus packages prior to release 13 include the http status module. For NGINX Plus release 13 and above, the status module is deprecated and you must use the new Plus API instead. See [the announcement][5] for more information.

#### Prepare NGINX

On each NGINX server, create a `status.conf` file in the directory that contains your other NGINX configuration files (e.g. `/etc/nginx/conf.d/`).

```
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
  }
}
```

**NGINX Plus**

NGINX Plus users can also utilize `stub_status`, but since that module provides fewer metrics, Datadog recommends using `status`.

For NGINX Plus releases 15+, the `status` module is deprecated. Use the [http_api_module][15] instead. For example, enable the `/api` endpoint in your main NGINX configuration file (`/etc/nginx/conf.d/default.conf`):
  
  ```
  server { 
    listen 8080; 
    location /api { 
    api write=on; 
  } 
  ```


Reload NGINX to enable the status or API endpoint. There's no need for a full restart.

```
sudo nginx -t && sudo nginx -s reload
```


#### Metric Collection

1. Set the `nginx_status_url` parameter to `http://localhost:81/nginx_status/` in your `nginx.d/conf.yaml` file to start gathering your [NGINX metrics](#metrics). See the [sample nginx.d/conf.yaml][6] for all available configuration options.

**NGINX Plus**

* For NGINX Plus releases 13+, set the parameter `use_plus_api` to `true` in your `nginx.d/conf.yaml` configuration file. 
* If you are using `http_api_module`, set the parameter `nginx_status_url` to the server's `/api` location in your `nginx.d/conf.yaml` configuration file, for example:

  ```
  nginx_status_url: http://localhost:8080/api
  ```

2. Optional - If you are using the NGINX `vhost_traffic_status module`, set the parameter `use_vts` to `true` in your `nginx.d/conf.yaml` configuration file.

3. [Restart the Agent][7] to start sending NGINX metrics to Datadog.

#### Log Collection

**Available for Agent >6.0**

* Collecting logs is disabled by default in the Datadog Agent, you need to enable it in `datadog.yaml`:

  ```
  logs_enabled: true
  ```

*  Add this configuration block to your `nginx.d/conf.yaml` file to start collecting your NGINX Logs:

  ```
  logs:
    - type: file
      path: /var/log/nginx/access.log
      service: nginx
      source: nginx
      sourcecategory: http_web_access

    - type: file
      path: /var/log/nginx/error.log
      service: nginx
      source: nginx
      sourcecategory: http_web_access
  ```
  Change the `service` and `path` parameter values and configure them for your environment.
  See the [sample nginx.d/conf.yaml][6] for all available configuration options.

* [Restart the Agent][7]

**Learn more about log collection [in the log documentation][8]**

### Validation

[Run the Agent's `status` subcommand][9] and look for `nginx` under the Checks section.

## Data Collected
### Metrics

See [metadata.csv][10] for a full list of provided metrics by this integration.

Not all metrics shown are available to users of open source NGINX. Compare the module reference for [stub status][3] (open source NGINX) and [http status][4] (NGINX Plus) to understand which metrics are provided by each module.

A few open-source NGINX metrics are named differently in NGINX Plus; they refer to the exact same metric, though:

| NGINX                        | NGINX Plus                 |
| -------------------          | -------------------        |
| nginx.net.connections        | nginx.connections.active   |
| nginx.net.conn_opened_per_s  | nginx.connections.accepted |
| nginx.net.conn_dropped_per_s | nginx.connections.dropped  |
| nginx.net.request_per_s      | nginx.requests.total       |

These metrics don't refer exactly to the same metric, but they are somewhat related:

| NGINX               | NGINX Plus             |
| ------------------- | -------------------    |
| nginx.net.waiting   | nginx.connections.idle |

Finally, these metrics have no good equivalent:

|                     |                                                                                           |
| ------------------- | -------------------                                                                       |
| nginx.net.reading   | The current number of connections where nginx is reading the request header.              |
| nginx.net.writing   | The current number of connections where nginx is writing the response back to the client. |

### Events
The NGINX check does not include any events.

### Service Checks

`nginx.can_connect`:

Returns CRITICAL if the Agent cannot connect to NGINX to collect metrics, otherwise OK.

## Troubleshooting
Need help? Contact [Datadog support][11].

## Further Reading

Learn more about how to monitor NGINX performance metrics thanks to [our series of posts][12]. We detail the key performance metrics, [how to collect them][13], and [how to use Datadog to monitor NGINX][14].


[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/nginx/images/nginx_dashboard.png
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://nginx.org/en/docs/http/ngx_http_stub_status_module.html
[4]: https://nginx.org/en/docs/http/ngx_http_status_module.html
[5]: https://www.nginx.com/blog/nginx-plus-r13-released
[6]: https://github.com/DataDog/integrations-core/blob/master/nginx/datadog_checks/nginx/data/conf.yaml.example
[7]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#start-stop-and-restart-the-agent
[8]: https://docs.datadoghq.com/logs
[9]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#agent-status-and-information
[10]: https://github.com/DataDog/integrations-core/blob/master/nginx/metadata.csv
[11]: https://docs.datadoghq.com/help
[12]: https://www.datadoghq.com/blog/how-to-monitor-nginx
[13]: https://www.datadoghq.com/blog/how-to-collect-nginx-metrics/index.html
[14]: https://www.datadoghq.com/blog/how-to-monitor-nginx-with-datadog/index.html
[15]: https://nginx.org/en/docs/http/ngx_http_api_module.html
