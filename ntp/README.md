# NTP check

# Overview

Get alerts when your hosts drift out of sync with your chosen NTP server.

# Installation

The NTP check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) wherever you'd like to run the check. If you need the newest version of the check, install the `dd-check-ntp` package.

# Configuration

The Agent enables the NTP check by default, but if you want to configure the check yourself, create a file `ntp.yaml` in the Agent's `conf.d` directory:

```
init_config:

instances:
  - offset_threshold: 60 # seconds difference between local clock and NTP server when ntp.in_sync service check becomes CRITICAL; default is 60
#   host: pool.ntp.org # set to use an NTP server of your choosen
#   port: 1234         # set along with host
#   version: 3         # to use a specific NTP version
#   timeout: 5         # seconds to wait for a response from the NTP server
```

Restart the Agent to effect any configuration changes.

# Validation

Run the Agent's `info` subcommand and look for `ntp` under the Checks section:

```
  Checks
  ======
    [...]

    ntp
    -------
      - instance #0 [OK]
      - Collected 1 metrics, 0 events & 0 service checks

    [...]
```

# Compatibility

The NTP check is compatible with all major platforms.

# Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/ntp/metadata.csv) for a list of metrics provided by this check.

# Service Checks

`ntp.in_sync`:

Returns CRITICAL if the NTP offset is greater than the threshold specified in `ntp.yaml`, otherwise OK.
