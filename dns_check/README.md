# DNS Integration

## Overview

Monitor the resolvability of and lookup times for any DNS records using nameservers of your choosing.

## Installation

The DNS check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on any host from which you want to probe your DNS servers. Though many metrics-oriented checks are best run on the same host(s) as the monitored service, you may want to run this status-oriented check from hosts that do not run the monitored DNS services.

If you need the newest version of the DNS check, install the `dd-check-dns` package; this package's check will override the one packaged with the Agent. See the [integrations-core](https://github.com/DataDog/integrations-core#installing-the-integrations) repository for more details.

## Configuration

Create a file `dns_check.yaml` in the Agent's `conf.d` directory:

```
init_config:

instances:
  - name: Example (com)
    # nameserver: 8.8.8.8   # The nameserver to query, this must be an IP address
    hostname: example.com # the record to fetch
    # record_type: AAAA   # default is A
  - name: Example (org)
    hostname: example.org
```

If you omit the `nameserver` option, the check will use whichever nameserver is configured in local network settings.

Restart the Agent to begin sending DNS service checks and response times to Datadog.

## Validation

Run the Agent's `info` subcommand and look for `dns_check` under the Checks section:

```
  Checks
  ======
    [...]

    dns_check
    ---------
      - instance #0 [OK]
      - instance #1 [OK]
      - Collected 2 metrics, 0 events & 2 service checks

    [...]
```

## Troubleshooting

## Compatibility

The DNS check is compatible with all major platforms.

## Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/dns_check/metadata.csv) for a list of metrics provided by this integration.

## Events

## Service Checks

`dns.can_resolve`:

Returns CRITICAL if the Agent fails to resolve the request, otherwise returns UP.

Tagged by `hostname` and `record_type`.

## Further Reading
