# KyotoTycoon Integration

## Overview

The Agent's KyotoTycoon check tracks get, set, and delete operations, and lets you monitor replication lag.

## Setup
### Installation

The KyotoTycoon check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your KyotoTycoon servers.
If you need the newest version of the KyotoTycoon check, install the `dd-check-kyototycoon` package; this package's check overrides the one packaged with the Agent. See the [integrations-core repository README.md for more details](https://github.com/DataDog/integrations-core#installing-the-integrations).

### Configuration

Create a file `kyototycoon.yaml` in the Agent's `conf.d` directory. See the [sample kyototycoon.yaml](https://github.com/DataDog/integrations-core/blob/master/kyototycoon/conf.yaml.example) for all available configuration options:

```
init_config:

instances:
#  Each instance needs a report URL.
#  name, and optionally tags keys. The report URL should
#  be a URL to the Kyoto Tycoon "report" RPC endpoint.
#
#  Complete example:
#
- report_url: http://localhost:1978/rpc/report
#   name: my_kyoto_instance
#   tags:
#     foo: bar
#     baz: bat
```

### Validation

[Run the Agent's `status` subcommand](https://docs.datadoghq.com/agent/faq/agent-status-and-information/) and look for `kyototycoon` under the Checks section:

```
  Checks
  ======
    [...]

    kyototycoon
    -------
      - instance #0 [OK]
      - Collected 26 metrics, 0 events & 1 service check

    [...]
```

## Compatibility

The KyotoTycoon check is compatible with all major platforms.

## Data Collected
### Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/kyototycoon/metadata.csv) for a list of metrics provided by this check.

### Events
The KyotoTycoon check does not include any event at this time.

### Service Checks

`kyototycoon.can_connect`:

Returns CRITICAL if the Agent cannot connect to KyotoTycoon to collect metrics, otherwise OK.

## Troubleshooting
Need help? Contact [Datadog Support](http://docs.datadoghq.com/help/).

## Further Reading
Learn more about infrastructure monitoring and all our integrations on [our blog](https://www.datadoghq.com/blog/)
