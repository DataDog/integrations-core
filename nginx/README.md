# NGINX Integration

# Overview

The Datadog Agent can collect many metrics from NGINX instances, including those for:

* Total requests
* Connections (accepted, handled, active)

For users of NGINX Plus, the commercial version of NGINX, the Agent can collect the significantly more metrics that NGINX Plus provides, like those for:

* Errors (4xx codes, 5xx codes)
* Upstream servers (active connections, 5xx codes, health checks, etc)
* Caches (size, hits, misses, etc)
* SSL (handshakes, failed handshakes, etc)

And many more.

The Agent sends one NGINX-related service check: whether or not the Agent is successfully collecting NGINX metrics.

The Agent does not send anything NGINX-related to your events stream.

# Installation

The NGINX integration - also known as the NGINX check - is included in the Datadog Agent package, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your NGINX servers. If you need the newest version of the NGINX check, install the `dd-check-nginx` package; this package's check will override the one packaged with the Agent. See the [integrations-core](https://github.com/DataDog/integrations-core#installing-the-integrations) repository for more details.

### NGINX status module

The NGINX check pulls metrics from a local NGINX status endpoint, so your `nginx` binaries need to have been compiled with one of two NGINX status modules:

* [stub status module](http://nginx.org/en/docs/http/ngx_http_stub_status_module.html) - for open source NGINX
* [http status module](http://nginx.org/en/docs/http/ngx_http_status_module.html) - only for NGINX Plus

NGINX Plus packages _always_ include the http status module, so if you're a Plus user, skip to the Configuration section now.

If you use open source NGINX, however, your instances may lack the stub status module. Verify that your `nginx` binary includes the module before proceeding to Configuration:

```
$ nginx -V 2>&1| grep -o http_stub_status_module
http_stub_status_module
```

If the command output does not include `http_stub_status_module`, you must install an NGINX package that includes the module. You _can_ compile your own NGINX (enabling the module as you compile it), but most modern Linux distributions provide alternative NGINX packages with various combinations of extra modules built in. Check your operating system's NGINX packages to find one that includes the stub status module.

# Configuration

### Prepare NGINX

On each NGINX server, create a `status.conf` in the directory that contains other NGINX configuration files (e.g. `/etc/nginx/conf.d/`):

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

    # available only with NGINX Plus
    # status;
  }
}
```

NGINX Plus can also use `stub_status`, but since that module provides fewer metrics, Plus users should use `status`.

You may optionally configure HTTP basic authentication in the server block, but since the service is only listening locally, it's not necessary.

Reload NGINX to enable the status endpoint. There's no need for a full restart.

### Connect the Agent

Create an `nginx.yaml` in the Agent's `conf.d` directory to connect the Agent to the NGINX status endpoint:

```
init_config:

instances:
  - nginx_status_url: http://localhost:81/nginx_status/
  # If you configured the endpoint with HTTP basic authentication
  # user: <USER>
  # password: <PASSWORD>
```

Restart the Agent to start sending NGINX metrics to Datadog.

# Validation

Run the Agent's `info` subcommand and look for `nginx` under the Checks section:

```
  Checks
  ======
    [...]

    nginx
    -----
      - instance #0 [OK]
      - Collected 7 metrics, 0 events & 1 service check

    [...]
```

See the Troubleshooting section if the status is not OK.

# Troubleshooting

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

Otherwise, review the Configuration section.

# Compatibility

The NGINX check is compatible with all major platforms.

# Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/nginx/metadata.csv) for a full list of provided metrics.

Not all metrics shown are available to users of open source NGINX. Compare the module reference for [stub status](http://nginx.org/en/docs/http/ngx_http_stub_status_module.html) (open source NGINX) and [http status](http://nginx.org/en/docs/http/ngx_http_status_module.html) (NGINX Plus) to understand which metrics are provided by each module.
