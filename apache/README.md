# Agent Check: Apache Web Server

## Overview

The Apache check tracks requests per second, bytes served, number of worker threads, service uptime, and more.

## Setup
### Installation

The Apache check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your Apache servers.

Install `mod_status` on your Apache servers and enable `ExtendedStatus`.

### Configuration

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

### Validation

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

## Compatibility

The Apache check is compatible with all major platforms.

## Data Collected
### Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/apache/metadata.csv) for a list of metrics provided by this check.

### Events
The Apache check does not include any event at this time.

### Service Checks

**apache.can_connect**:

Returns CRITICAL if the Agent cannot connect to the configured `apache_status_url`, otherwise OK.

## Troubleshooting
Need help? Contact [Datadog Support](http://docs.datadoghq.com/help/).

## Further Reading

* [Monitoring Apache web server performance](https://www.datadoghq.com/blog/monitoring-apache-web-server-performance/)
* [How to collect Apache performance metrics](https://www.datadoghq.com/blog/collect-apache-performance-metrics/)
* [How to monitor Apache web server with Datadog](https://www.datadoghq.com/blog/monitor-apache-web-server-datadog/)
