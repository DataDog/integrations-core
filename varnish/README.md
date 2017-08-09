# Agent Check: Varnish

# Overview

This check collects varnish metrics regarding:

* Clients: connections and requests
* Cache performance: hits, evictions, etc
* Threads: creation, failures, threads queued
* Backends: successful, failed, retried connections

It also submits service checks for the health of each backend.

# Installation

The varnish check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your varnish servers. If you need the newest version of the check, install the `dd-check-varnish` package.

# Configuration

If you're running Varnish 4.1+, add the dd-agent system user to the varnish group (e.g. `sudo usermod -G varnish -a dd-agent`).

Then, create a file `varnish.yaml` in the Agent's `conf.d` directory:

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

Restart the Agent to start sending varnish metrics and service checks to Datadog.

# Validation

Run the Agent's `info` subcommand and look for `varnish` under the Checks section:

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
# Compatibility

The Varnish check is compatible with all major platforms.

# Service Checks

**varnish.backend_healthy**:

The Agent submits this service check if you configure `varnishadm`. It submits a service check for each varnish backend, tagging each with `backend:<backend_name>`.

# Further Reading

See our [series of blog posts](https://www.datadoghq.com/blog/top-varnish-performance-metrics/) about monitoring varnish with Datadog.

# Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/varnish/metadata.csv) for a list of metrics provided by this check.
