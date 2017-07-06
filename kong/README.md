# Kong Integration

# Overview

The Agent's Kong check tracks total requests, response codes, client connections, and more.

# Installation

The Kong check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your Kong servers. If you need the newest version of the check, install the `dd-check-kong` package.

# Configuration

Create a `kong.yaml` in the Datadog Agent's `conf.d` directory:

```
init_config:

instances:
# Each instance needs a `kong_status_url`. Tags are optional.
-   kong_status_url: http://example.com:8001/status/
    tags:
    - instance:foo
#-   kong_status_url: http://example2.com:8001/status/
#    tags:
#    - instance:bar
```

Restart the Agent to begin sending Kong metrics to Datadog.

# Validation

Run the Agent's `info` subcommand and look for kong` under the Checks section:

```
  Checks
  ======
    [...]

    kong
    -------
      - instance #0 [OK]
      - Collected 26 metrics, 0 events & 1 service check

    [...]
```

# Compatibility

The kong check is compatible with all major platforms.

# Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/kong/metadata.csv) for a list of metrics provided by this check.
