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

The varnish check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your varnish servers. If you need the newest version of the check, install the `dd-check-varnish` package.

### Configuration

If you're running Varnish 4.1+, add the dd-agent system user to the varnish group (e.g. `sudo usermod -G varnish -a dd-agent`).

Then, create a file `varnish.yaml` in the Agent's `conf.d` directory. See the [sample varnish.yaml](https://github.com/DataDog/integrations-core/blob/master/varnish/conf.yaml.example) for all available configuration options:

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

[Restart the Agent](https://docs.datadoghq.com/agent/faq/start-stop-restart-the-datadog-agent) to start sending varnish metrics and service checks to Datadog.

### Validation

[Run the Agent's `info` subcommand](https://docs.datadoghq.com/agent/faq/agent-status-and-information/) and look for `varnish` under the Checks section:

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

The Agent submits this service check if you configure `varnishadm`. It submits a service check for each varnish backend, tagging each with `backend:<backend_name>`.

## Troubleshooting
Need help? Contact [Datadog Support](http://docs.datadoghq.com/help/).

## Further Reading

* [Top Varnish performance metrics](https://www.datadoghq.com/blog/top-varnish-performance-metrics/)
* [How to collect Varnish metrics](https://www.datadoghq.com/blog/how-to-collect-varnish-metrics/)
* [Monitor Varnish using Datadog](https://www.datadoghq.com/blog/monitor-varnish-using-datadog/)