# PowerDNS Recursor Integration

## Overview

Track the performance of your PowerDNS Recursor and monitor strange or worrisome traffic. This Agent check collects a variety of metrics from your recursors, including those for:

- Query answer times—see how many responses take less than 1ms, 10ms, 100ms, 1s, or greater than 1s.
- Query timeouts.
- Cache hits and misses.
- Answer rates by type: SRVFAIL, NXDOMAIN, NOERROR.
- Ignored and dropped packets.

And many more.

## Setup

### Installation

The PowerDNS Recursor check is included in the [Datadog Agent][1] package, so you don't need to install anything else on your recursors.

### Configuration

#### Prepare PowerDNS

This check collects performance statistics via PowerDNS Recursor's statistics API. Versions of pdns_recursor before 4.1 do not enable the stats API by default. If you're running an older version, enable it by adding the following to your recursor config file (e.g. `/etc/powerdns/recursor.conf`):

```conf
webserver=yes
api-key=changeme             # only available since ver 4.0
webserver-readonly=yes       # default no
#webserver-port=8081         # default 8082
#webserver-address=0.0.0.0   # default 127.0.0.1
```

If you're running pdns_recursor 3.x, prepend `experimental-` to these option names, e.g. `experimental-webserver=yes`.

If you're running pdns_recursor >= 4.1, just set `api-key`.

Restart the recursor to enable the statistics API.

#### Host

Follow the instructions below to configure this check for an Agent running on a host. For containerized environments, see the [Containerized](#containerized) section.

1. Edit the `powerdns_recursor.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][2]. See the [sample powerdns_recursor.d/conf.yaml][3] for all available configuration options:

   ```yaml
   init_config:

   instances:
     ## @param host - string - required
     ## Host running the recursor.
     #
     - host: 127.0.0.1

       ## @param port - integer - required
       ## Recursor web server port.
       #
       port: 8082

       ## @param api_key - string - required
       ## Recursor web server api key.
       #
       api_key: "<POWERDNS_API_KEY>"

       ## @param version - integer - required - default: 3
       ## Version 3 or 4 of PowerDNS Recursor to connect to.
       ## The PowerDNS Recursor in v4 has a production ready web server that allows for
       ## statistics gathering. In version 3.x the server was marked as experimental.
       ##
       ## As the server was marked as experimental in version 3 many of the metrics have
       ## changed names and the API structure (paths) have also changed. With these changes
       ## there has been a need to separate the two concerns. The check now has a key value
       ## version: which if set to version 4 queries with the correct API path on the
       ## non-experimental web server.
       ##
       ## https://doc.powerdns.com/md/httpapi/api_spec/#url-apiv1serversserver95idstatistics
       #
       version: 3
   ```

2. [Restart the Agent][4].

#### Containerized

For containerized environments, see the [Autodiscovery Integration Templates][5] for guidance on applying the parameters below.

| Parameter            | Value                                                                            |
| -------------------- | -------------------------------------------------------------------------------- |
| `<INTEGRATION_NAME>` | `powerdns_recursor`                                                              |
| `<INIT_CONFIG>`      | blank or `{}`                                                                    |
| `<INSTANCE_CONFIG>`  | `{"host":"%%host%%", "port":8082, "api_key":"<POWERDNS_API_KEY>", "version": 3}` |

### Validation

[Run the Agent's `status` subcommand][6] and look for `powerdns_recursor` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

The PowerDNS Recursor check does not include any events.

### Service Checks

**`powerdns.recursor.can_connect`**:

Returns CRITICAL if the Agent is unable to connect to the recursor's statistics API, otherwise OK.

## Troubleshooting

Need help? Contact [Datadog support][8].

[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[3]: https://github.com/DataDog/integrations-core/blob/master/powerdns_recursor/datadog_checks/powerdns_recursor/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[5]: https://docs.datadoghq.com/agent/autodiscovery/integrations/
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/powerdns_recursor/metadata.csv
[8]: https://docs.datadoghq.com/help
