# Marathon Integration

# Overview

The Agent's Marathon check lets you:

* Track the state and health of every application: see configured memory, disk, cpu, and instances; monitor the number of healthy and unhealthy tasks
* Monitor the number of queued applications and the number of deployments

# Installation

The Marathon check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your Marathon master. If you need the newest version of the check, install the `dd-check-marathon` package.

# Configuration

Create a file `marathon.yaml` in the Agent's `conf.d` directory:

```
init_config:
  - default_timeout: 5 # how many seconds to wait for Marathon API response

instances:
  - url: https://<server>:<port> # the API endpoint of your Marathon master; required
    #acs_url: https://<server>:<port> # if your Marathon master requires ACS auth
	user: <username> # the user for marathon API or ACS token authentication
	password: <password> # the password for marathon API or ACS token authentication
```

The function of `user` and `password` depends on whether or not you configure `acs_url`. If you do, set `user` and `password` to whatever credentials will let the Agent request an authentication token from ACS. Otherwise, set them to whatever credentials will let the Agent authenticate (HTTP basic auth) to the Marathon API.

Restart the Agent to begin sending Marathon metrics to Datadog.

# Validation

Run the Agent's `info` subcommand and look for `marathon` under the Checks section:

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

# Compatibility

The marathon check is compatible with all major platforms.

# Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/marathon/metadata.csv) for a list of metrics provided by this check.

# Service Checks

`marathon.can_connect`:

Returns CRITICAL if the Agent cannot connect to Marathon to collect metrics, otherwise OK.
