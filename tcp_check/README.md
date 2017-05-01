# TCP Integration

# Overview

Monitor TCP connectivity and response time for any host and port.

# Installation

The TCP check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on any host from which you want to probe TCP ports. Though many metrics-oriented checks are best run on the same host(s) as the monitored service, you may want to run this status-oriented check from hosts that do not run the monitored TCP services, i.e. to test remote connectivity.

If you need the newest version of the TCP check, install the `dd-check-tcp` package; this package's check will override the one packaged with the Agent. See the [integrations-core](https://github.com/DataDog/integrations-core#installing-the-integrations) repository for more details.

# Configuration

Create a file `tcp_check.yaml` in the Agent's `conf.d` directory:

```
init_config:

instances:
  - name: SSH check
    host: jumphost.example.com # or IPv4/IPv6 address
    port: 22           
    skip_event: true # Default is false, i.e. emit events instead of service checks. Recommend to set to true.
    collect_response_time: true # to collect network.tcp.response_time. Default is false.
```

Restart the Agent to start sending TCP service checks and response times to Datadog.

# Validation

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

# Troubleshooting

# Compatibility

The TCP check is compatible with all major platforms.

# Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/tcp_check/metadata.csv) for a list of metrics provided by this integration.

# Events

Older versions of the TCP check only emitted events to reflect site status, but now the check supports service checks, too. However, events are still the default behavior. Set `skip_event` to true for all configured instances to submit service checks instead of events. The Agent will soon deprecate `skip_event`, i.e. the TCP check's default be will only support service checks.

# Service Checks

To create alert conditions on this service checks in Datadog, select 'Network' on the [Create Monitor](https://app.datadoghq.com/monitors#/create) page, not 'Integration'.

**`tcp.can_connect`**:

Returns DOWN if the Agent cannot connect to the configured `host` and `port`, otherwise UP.

# Further Reading
