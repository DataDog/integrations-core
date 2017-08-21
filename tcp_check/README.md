# Agent Check: TCP connectivity

## Overview

Monitor TCP connectivity and response time for any host and port.

## Setup
### Installation

The TCP check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on any host from which you want to probe TCP ports. Though many metrics-oriented checks are best run on the same host(s) as the monitored service, you'll probably want to run this check from hosts that do not run the monitored TCP services, i.e. to test remote connectivity.

If you need the newest version of the TCP check, install the `dd-check-tcp` package.

### Configuration

Create a file `tcp_check.yaml` in the Agent's `conf.d` directory:

```
init_config:

instances:
  - name: SSH check
    host: jumphost.example.com # or an IPv4/IPv6 address
    port: 22           
    skip_event: true # if false, the Agent will emit both events and service checks for this port; recommended true (i.e. only submit service checks)
    collect_response_time: true # to collect network.tcp.response_time. Default is false.
```

Restart the Agent to start sending TCP service checks and response times to Datadog.

### Validation

Run the Agent's `info` subcommand and look for `tcp_check` under the Checks section:

```
  Checks
  ======
    [...]

    tcp_check
    ----------
      - instance #0 [OK]
      - Collected 1 metric, 0 events & 1 service check

    [...]
```

## Compatibility

The TCP check is compatible with all major platforms.

## Data Collected
### Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/tcp_check/metadata.csv) for a list of metrics provided by this check.

### Events
The TCP check does not include any event at this time.

### Service Checks

**`tcp.can_connect`**:

Returns DOWN if the Agent cannot connect to the configured `host` and `port`, otherwise UP.

Older versions of the TCP check only emitted events to reflect changes in connectivity. This was eventually deprecated in favor of service checks, but you can still have the check emit events by setting `skip_event: false`.

To create alert conditions on this service check in the Datadog app, click **Network** on the [Create Monitor](https://app.datadoghq.com/monitors#/create) page, not **Integration**.
