# Marathon Integration

## Overview

The Agent's Marathon check lets you:

* Track the state and health of every application: see configured memory, disk, cpu, and instances; monitor the number of healthy and unhealthy tasks
* Monitor the number of queued applications and the number of deployments

## Setup
### Installation

The Marathon check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your Marathon master.

If you need the newest version of the Marathon check, install the `dd-check-marathon` package; this package's check overrides the one packaged with the Agent. See the [integrations-core repository README.md for more details](https://docs.datadoghq.com/agent/faq/install-core-extra/).

### Configuration

Create a file `marathon.yaml` in the Agent's `conf.d` directory. See the [sample marathon.yaml](https://github.com/DataDog/integrations-core/blob/master/marathon/conf.yaml.example) for all available configuration options:

```
init_config:

instances:
  - url: https://<server>:<port> # the API endpoint of your Marathon master; required
#   acs_url: https://<server>:<port> # if your Marathon master requires ACS auth
    user: <username> # the user for marathon API or ACS token authentication
    password: <password> # the password for marathon API or ACS token authentication
```

The function of `user` and `password` depends on whether or not you configure `acs_url`; If you do, the Agent uses them to request an authentication token from ACS, which it then uses to authenticate to the Marathon API. Otherwise, the Agent uses `user` and `password` to directly authenticate to the Marathon API.

[Restart the Agent](https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent) to begin sending Marathon metrics to Datadog.

### Validation

[Run the Agent's `status` subcommand](https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information) and look for `marathon` under the Checks section:

```
  Checks
  ======
    [...]

    marathon
    -------
      - instance #0 [OK]
      - Collected 26 metrics, 0 events & 1 service check

    [...]
```

## Compatibility

The marathon check is compatible with all major platforms.

## Data Collected
### Metrics
See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/marathon/metadata.csv) for a list of metrics provided by this integration.

### Events
The Marathon check does not include any event at this time.

### Service Checks

`marathon.can_connect`:

Returns CRITICAL if the Agent cannot connect to the Marathon API to collect metrics, otherwise OK.

## Troubleshooting
Need help? Contact [Datadog Support](http://docs.datadoghq.com/help/).

## Further Reading
Learn more about infrastructure monitoring and all our integrations on [our blog](https://www.datadoghq.com/blog/)
