# Agent Check: Varnish
{{< img src="integrations/varnish/varnish.png" alt="Varnish default dashboard" responsive="true" popup="true">}}

## Overview

This check collects varnish metrics regarding:

* Clients: connections and requests
* Cache performance: hits, evictions, etc
* Threads: creation, failures, threads queued
* Backends: successful, failed, retried connections

It also submits service checks for the health of each backend.

## Setup
### Installation

The Varnish check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your Varnish servers.

If you need the newest version of the Varnish check, install the `dd-check-varnish` package; this package's check overrides the one packaged with the Agent. See the [integrations-core repository README.md for more details](https://github.com/DataDog/integrations-core#installing-the-integrations).

### Configuration

Create a `varnish.yaml` file in the Agent's `conf.d` directory

#### Prepare Varnish

If you're running Varnish 4.1+, add the dd-agent system user to the Varnish group (e.g. `sudo usermod -G varnish -a dd-agent`).

#### Metric Collection

* Add this configuration setup to your `varnish.yaml` file to start gathering your [Varnish metrics](#metrics):

  ```
  init_config:

  instances:
    - varnishstat: /usr/bin/varnishstat        # or wherever varnishstat lives
      varnishadm: <PATH_TO_VARNISHADM_BIN>     # to submit service checks for the health of each backend
  #   secretfile: <PATH_TO_VARNISH_SECRETFILE> # if you configured varnishadm and your secret file isn't /etc/varnish/secret
  #   tags:
  #     - instance:production
  ```

  If you don't set `varnishadm`, the Agent won't check backend health. If you do set it, the Agent needs privileges to execute the binary with root privileges. Add the following to your `/etc/sudoers` file:

  ```
  dd-agent ALL=(ALL) NOPASSWD:/usr/bin/varnishadm
  ```

  See the [sample varnish.yaml](https://github.com/DataDog/integrations-core/blob/master/varnish/conf.yaml.example) for all available configuration options.

* [Restart the Agent](https://docs.datadoghq.com/agent/faq/start-stop-restart-the-datadog-agent) to start sending Varnish metrics and service checks to Datadog.

#### Log Collection

**Available for Agent >6.0**

* To enable Varnish logging uncomment the following in `/etc/default/varnishncsa`:

```
VARNISHNCSA_ENABLED=1
```

  Add the following at the end of the same file:

```
LOG_FORMAT="{\"date_access\": \"%{%Y-%m-%dT%H:%M:%S%z}t\", \"network.client.ip\":\"%h\", \"http.auth\" : \"%u\", \"varnish.x_forwarded_for\" : \"%{X-Forwarded-For}i\", \"varnish.hit_miss\":  \"%{Varnish:hitmiss}x\", \"network.bytes_written\": %b, \"http.response_time\": %D, \"http.status_code\": \"%s\", \"http.url\": \"%r\", \"http.ident\": \"%{host}i\", \"http.method\": \"%m\", \"varnish.time_first_byte\" : %{Varnish:time_firstbyte}x, \"varnish.handling\" : \"%{Varnish:handling}x\", \"http.referer\": \"%{Referer}i\", \"http.useragent\": \"%{User-agent}i\" }"

DAEMON_OPTS="$DAEMON_OPTS -c -a -F '${LOG_FORMAT}'"
```

  Restart Varnishncsa to make sure the changes are taken into account.


*  Collecting logs is disabled by default in the Datadog Agent, you need to enable it in `datadog.yaml`:

  ```
  logs_enabled: true
  ```

* Add this configuration setup to your `varnish.yaml` file to start collecting your Varnish logs:

  ```
  logs:
    - type: file
       path: /var/log/varnish/varnishncsa.log
      source: varnish
      sourcecategory: http_web_access
      service: varnish
  ```
  Change the `path` and `service` parameter value and configure them for your environment.
  See the [sample varnish.yaml](https://github.com/DataDog/integrations-core/blob/master/varnish/conf.yaml.example) for all available configuration options.

* [Restart the Agent](https://docs.datadoghq.com/agent/faq/start-stop-restart-the-datadog-agent).

**Learn more about log collection [on the log documentation](https://docs.datadoghq.com/logs)**

### Validation

[Run the Agent's `status` subcommand](https://docs.datadoghq.com/agent/faq/agent-status-and-information/) and look for `varnish` under the Checks section:

```
Checks
======
  [...]

  varnish
  -------
    - instance #0 [OK]
    - Collected 26 metrics, 0 events & 1 service check

  [...]
```
## Compatibility

The Varnish check is compatible with all major platforms.

## Data Collected
### Metrics
See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/varnish/metadata.csv) for a list of metrics provided by this check.

### Events
The Varnish check does not include any event at this time.

### Service Checks
**varnish.backend_healthy**:

The Agent submits this service check if you configure `varnishadm`. It submits a service check for each Varnish backend, tagging each with `backend:<backend_name>`.

## Troubleshooting
Need help? Contact [Datadog Support](http://docs.datadoghq.com/help/).

## Further Reading

* [Top Varnish performance metrics](https://www.datadoghq.com/blog/top-varnish-performance-metrics/)
* [How to collect Varnish metrics](https://www.datadoghq.com/blog/how-to-collect-varnish-metrics/)
* [Monitor Varnish using Datadog](https://www.datadoghq.com/blog/monitor-varnish-using-datadog/)
