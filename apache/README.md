# Overview

Get metrics from Apache in real time; graph them and correlate them with other relevant system metrics and events.

  * Visualize your web server performance
  * Correlate the performance of Apache with the rest of your applications

# Installation

The Apache check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your Apache servers.

Install `mod_status` on your Apache servers and enable `ExtendedStatus`.

# Configuration

Create a file `apache.yaml` in the Agent's `conf.d` directory:

```
        init_config:

        instances:
          - apache_status_url: http://example.com/server-status?auto
            # apache_user: example_user
            # apache_password: example_password
            tags:
              - instance:foo
            disable_ssl_validation: true # if you want to disable SSL cert validation
```

Restart the Agent to begin sending Apache metrics to Datadog.

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

# Troubleshooting

# Compatibility

The Apache check is compatible with all major platforms.

# Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/apache/metadata.csv) for a list of metrics provided by this integration.

# Events

# Service Checks
