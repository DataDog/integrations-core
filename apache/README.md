# Agent Check: Apache Web Server

# Overview

The Apache check tracks requests per second, bytes served, number of worker threads, service uptime, and more.

# Installation

The Apache check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your Apache servers.

Install `mod_status` on your Apache servers and enable `ExtendedStatus`.

# Configuration

Create a file `apache.yaml` in the Agent's `conf.d` directory:

```
init_config:

instances:
  - apache_status_url: http://example.com/server-status?auto
#   apache_user: example_user # if apache_status_url needs HTTP basic auth
#   apache_password: example_password
#   disable_ssl_validation: true # if you need to disable SSL cert validation, i.e. for self-signed certs
```

Restart the Agent to start sending Apache metrics to Datadog.

# Validation

Run the Agent's `info` subcommand and look for `apache` under the Checks section:

```
  Checks
  ======
    [...]

    apache
    -------
      - instance #0 [OK]
      - Collected 26 metrics, 0 events & 1 service check

    [...]
```

# Compatibility

The Apache check is compatible with all major platforms.

# Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/apache/metadata.csv) for a list of metrics provided by this check.

# Service Checks

**apache.can_connect**:

Returns CRITICAL if the Agent cannot connect to the configured `apache_status_url`, otherwise OK.
