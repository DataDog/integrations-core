# Agent Check: Varnish

![Varnish default dashboard][11]

## Overview

This check collects varnish metrics regarding:

* Clients: connections and requests
* Cache performance: hits, evictions, etc
* Threads: creation, failures, threads queued
* Backends: successful, failed, retried connections

It also submits service checks for the health of each backend.

## Setup
### Installation

The Varnish check is included in the [Datadog Agent][1] package, so you don't need to install anything else on your Varnish servers.

### Configuration

1. Edit the `varnish.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][12] to start collecting your Varnish [metrics](#metric-collection) and [logs](#log-collection).
  See the [sample varnish.d/conf.yaml][2] for all available configuration options.

2. [Restart the Agent][3]

#### Prepare Varnish

If you're running Varnish 4.1+, add the dd-agent system user to the Varnish group (e.g. `sudo usermod -G varnish -a dd-agent`).

#### Metric Collection

* Add this configuration block to your `varnish.d/conf.yaml` file to start gathering your [Varnish metrics](#metrics):

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

  See the [sample varnish.yaml][2] for all available configuration options.

* [Restart the Agent][3] to start sending Varnish metrics and service checks to Datadog.

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

* Add this configuration block to your `varnish.d/conf.yaml` file to start collecting your Varnish logs:

  ```
  logs:
    - type: file
       path: /var/log/varnish/varnishncsa.log
      source: varnish
      sourcecategory: http_web_access
      service: varnish
  ```
  Change the `path` and `service` parameter value and configure them for your environment.
  See the [sample varnish.yaml][2] for all available configuration options.

* [Restart the Agent][3].

**Learn more about log collection [in the log documentation][4]**

### Validation

[Run the Agent's `status` subcommand][5] and look for `varnish` under the Checks section.

## Data Collected
### Metrics
See [metadata.csv][6] for a list of metrics provided by this check.

### Events
The Varnish check does not include any events at this time.

### Service Checks
**varnish.backend_healthy**:

The Agent submits this service check if you configure `varnishadm`. It submits a service check for each Varnish backend, tagging each with `backend:<backend_name>`.

## Troubleshooting
Need help? Contact [Datadog Support][7].

## Further Reading

* [Top Varnish performance metrics][8]
* [How to collect Varnish metrics][9]
* [Monitor Varnish using Datadog][10]


[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://github.com/DataDog/integrations-core/blob/master/varnish/datadog_checks/varnish/data/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[4]: https://docs.datadoghq.com/logs
[5]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[6]: https://github.com/DataDog/integrations-core/blob/master/varnish/metadata.csv
[7]: https://docs.datadoghq.com/help/
[8]: https://www.datadoghq.com/blog/top-varnish-performance-metrics/
[9]: https://www.datadoghq.com/blog/how-to-collect-varnish-metrics/
[10]: https://www.datadoghq.com/blog/monitor-varnish-using-datadog/
[11]: https://raw.githubusercontent.com/DataDog/integrations-core/master/varnish/images/varnish.png
[12]: https://docs.datadoghq.com/agent/faq/agent-configuration-files/#agent-configuration-directory
