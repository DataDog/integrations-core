# Lighttpd Check

# Overview

The Agent's lighttpd check tracks uptime, bytes served, requests per second, response codes, and more.

# Installation

The lighttpd check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your lighttpd servers. If you need the newest version of the check, install the `dd-check-lighttpd` package.

You'll also need to install `mod_status` on your Lighttpd servers.

# Configuration

Create a file `lighttpd.yaml` in the Agent's `conf.d` directory:

```
init_config:

instances:
# Each instance needs a lighttpd_status_url. Tags are optional.
- lighttpd_status_url: http://example.com/server-status?auto
  tags:
  - instance:foo
```

Restart the Agent to begin sending lighttpd metrics to Datadog.

# Validation

Run the Agent's `info` subcommand and look for `lighttpd` under the Checks section:

```
  Checks
  ======
    [...]

    lighttpd
    -------
      - instance #0 [OK]
      - Collected 30 metrics, 0 events & 1 service check

    [...]
```

# Compatibility

The lighttpd check is compatible with all major platforms.

# Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/lighttpd/metadata.csv) for a list of metrics provided by this check.

# Service Checks

`lighttpd.can_connect`:

Returns CRITICAL if the Agent cannot connect to lighttpd to collect metrics, otherwise OK.