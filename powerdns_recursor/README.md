# PowerDNS Recursor Integration

# Overview



# Installation

The PowerDNS Recursor check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your recursors. If you need the newest version of the check, install the `dd-check-powerdns-recursor` package; this package's check will override the one packaged with the Agent. See the [integrations-core](https://github.com/DataDog/integrations-core#installing-the-integrations) repository for more details.

# Configuration

## Prepare PowerDNS

This check collects performance statistics via pdns_recursor's statistics API. Versions of pdns_recursor before 4.1 do not enable the stats API by default. If you're running an older version, enable it by adding the following to your recursor config file (e.g. /etc/powerdns/recursor.conf):

```
webserver=yes
api-key=changeme            # only available since ver 4.0
webserver-readonly=yes    # default no
# webserver-port=8081       # default 8082
# webserver-address=0.0.0.0 # default 127.0.0.1
```

If you're running pdns_recursor 3.x, prepend `experimental-` to these option names, e.g. `experimental-webserver=yes`.

If you're running pdns_recursor >= 4.1, simply set an `api-key` in the recursor config.

Restart the recursor to enable the statistics API.

## Connect the Agent

Create a file `powerdns_recursor.yaml` in the Agent's `conf.d` directory:

```
init_config:

instances:
  - host: 127.0.0.1
    port: 8082
    api_key: changeme
    version: 4 # omit this option if you're running pdns_recursor 3.x
```

Restart the Agent to begin sending PowerDNS metrics to Datadog.

# Validation

Run the Agent's `info` subcommand and look for `powerdns_recursor` under the Checks section:

```
  Checks
  ======
    [...]

    powerdns_recursor
    -------
      - instance #0 [OK]
      - Collected 8 metrics, 0 events & 1 service check

    [...]
```

# Troubleshooting

# Compatibility

The PowerDNS Recursor check is compatible with all major platforms.

# Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/powerdns_recursor/metadata.csv) for a list of metrics provided by this integration.

# Service Checks

**`powerdns.recursor.can_connect`**:

Returns CRITICAL if the Agent is unable to connect to the recursor's statistics API, otherwise OK.
