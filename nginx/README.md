# NGINX check

![NGINX default dashboard][14]

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

The NGINX check is included in the [Datadog Agent][1] package, so you don't need to install anything else on your NGINX servers.

#### NGINX status module

The NGINX check pulls metrics from a local NGINX status endpoint, so your `nginx` binaries need to have been compiled with one of two NGINX status modules:

* [stub status module][2] - for open source NGINX
* [http status module][3] - only for NGINX Plus

NGINX Plus packages _always_ include the http status module, so if you're a Plus user, skip to **Configuration** now.
For NGINX Plus release 13 and above, the status module is deprecated and you should use the new Plus API instead. See [the announcement][4] for more information.

If you use open source NGINX, however, your instances may lack the stub status module. Verify that your `nginx` binary includes the module before proceeding to **Configuration**:

```
$ nginx -V 2>&1| grep -o http_stub_status_module
http_stub_status_module
```

If the command output does not include `http_stub_status_module`, you must install an NGINX package that includes the module. You _can_ compile your own NGINX-enabling the module as you compile it-but most modern Linux distributions provide alternative NGINX packages with various combinations of extra modules built in. Check your operating system's NGINX packages to find one that includes the stub status module.

### Configuration

Edit the `nginx.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][15] to start collecting your NGINX [metrics](#metric-collection) and [logs](#log-collection).
See the [sample nginx.d/conf.yaml][5] for all available configuration options.

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

NGINX Plus can also use `stub_status`, but since that module provides fewer metrics, you should use `status` if you're a Plus user.

You may optionally configure HTTP basic authentication in the server block, but since the service is only listening locally, it's not necessary.

Reload NGINX to enable the status endpoint. (There's no need for a full restart)

#### Metric Collection

* Add this configuration block to your `nginx.d/conf.yaml` file to start gathering your [NGINX metrics](#metrics):

  ```
  init_config:

  instances:
    - nginx_status_url: http://localhost:81/nginx_status/
    # If you configured the endpoint with HTTP basic authentication
    # user: <USER>
    # password: <PASSWORD>
  ```
  See the [sample nginx.d/conf.yaml][5] for all available configuration options.

* [Restart the Agent][6] to start sending NGINX metrics to Datadog.

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
  See the [sample nginx.d/conf.yaml][5] for all available configuration options.

* [Restart the Agent][6]

**Learn more about log collection [in the log documentation][7]**

### Validation

[Run the Agent's `status` subcommand][8] and look for `nginx` under the Checks section.

## Data Collected
### Metrics

See [metadata.csv][9] for a full list of provided metrics by this integration.

Not all metrics shown are available to users of open source NGINX. Compare the module reference for [stub status][2] (open source NGINX) and [http status][3] (NGINX Plus) to understand which metrics are provided by each module.

A few open-source NGINX metrics are named differently in NGINX Plus; they refer to the exact same metric, though:

| NGINX | NGINX Plus |
|-------------------|-------------------|
| nginx.net.connections | nginx.connections.active |
| nginx.net.conn_opened_per_s | nginx.connections.accepted |
| nginx.net.conn_dropped_per_s | nginx.connections.dropped |
| nginx.net.request_per_s | nginx.requests.total |

These metrics don't refer exactly to the same metric, but they are somewhat related:

| NGINX | NGINX Plus |
|-------------------|-------------------|
| nginx.net.waiting | nginx.connections.idle|

Finally, these metrics have no good equivalent:

|||
|-------------------|-------------------|
| nginx.net.reading | The current number of connections where nginx is reading the request header. |
| nginx.net.writing | The current number of connections where nginx is writing the response back to the client. |

### Events
The NGINX check does not include any events at this time.

### Service Checks

`nginx.can_connect`:

Returns CRITICAL if the Agent cannot connect to NGINX to collect metrics, otherwise OK.

## Troubleshooting
You may observe one of these common problems in the output of the Datadog Agent's info subcommand.

### Agent cannot connect
```
  Checks
  ======

    nginx
    -----
      - instance #0 [ERROR]: "('Connection aborted.', error(111, 'Connection refused'))"
      - Collected 0 metrics, 0 events & 1 service check
```

Either NGINX's local status endpoint is not running, or the Agent is not configured with correct connection information for it.

Check that the main `nginx.conf` includes a line like the following:

```
http{

  ...

  include <directory_that_contains_status.conf>/*.conf;
  # e.g.: include /etc/nginx/conf.d/*.conf;
}
```

Otherwise, review the **Configuration** section.

## Further Reading
### Knowledge Base
The data pulled from the NGINX Plus status page are described in the [NGINX docs][10].

### Datadog Blog
Learn more about how to monitor NGINX performance metrics thanks to [our series of posts][11]. We detail the key performance metrics, [how to collect them][12], and [how to use Datadog to monitor NGINX][13].


[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://nginx.org/en/docs/http/ngx_http_stub_status_module.html
[3]: https://nginx.org/en/docs/http/ngx_http_status_module.html
[4]: https://www.nginx.com/blog/nginx-plus-r13-released/
[5]: https://github.com/DataDog/integrations-core/blob/master/nginx/datadog_checks/nginx/data/conf.yaml.example
[6]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[7]: https://docs.datadoghq.com/logs
[8]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[9]: https://github.com/DataDog/integrations-core/blob/master/nginx/metadata.csv
[10]: https://nginx.org/en/docs/http/ngx_http_status_module.html#data
[11]: https://www.datadoghq.com/blog/how-to-monitor-nginx/
[12]: https://www.datadoghq.com/blog/how-to-collect-nginx-metrics/index.html
[13]: https://www.datadoghq.com/blog/how-to-monitor-nginx-with-datadog/index.html
[14]: https://raw.githubusercontent.com/DataDog/integrations-core/master/nginx/images/nginx_dashboard.png
[15]: https://docs.datadoghq.com/agent/faq/agent-configuration-files/#agent-configuration-directory
