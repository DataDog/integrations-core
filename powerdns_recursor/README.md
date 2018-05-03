# PowerDNS Recursor Integration

## Overview

Track the performance of your PowerDNS recursors and monitor strange or worrisome traffic. This Agent check collects a wealth of metrics from your recursors, including those for:

* Query answer times — see how many responses take less than 1ms, 10ms, 100ms, 1s, and greater than 1s
* Query timeouts
* Cache hits and misses
* Answer rates by type — SRVFAIL, NXDOMAIN, NOERROR
* Ignored and dropped packets

And many more.

## Setup
### Installation

The PowerDNS Recursor check is packaged with the Agent, so simply [install the Agent][1] on your recursors.

### Configuration
#### Prepare PowerDNS

This check collects performance statistics via pdns_recursor's statistics API. Versions of pdns_recursor before 4.1 do not enable the stats API by default. If you're running an older version, enable it by adding the following to your recursor config file (e.g. /etc/powerdns/recursor.conf):

```
webserver=yes
api-key=changeme            # only available since ver 4.0
webserver-readonly=yes      # default no
# webserver-port=8081       # default 8082
# webserver-address=0.0.0.0 # default 127.0.0.1
```

If you're running pdns_recursor 3.x, prepend `experimental-` to these option names, e.g. `experimental-webserver=yes`.

If you're running pdns_recursor >= 4.1, just set `api-key`.

Restart the recursor to enable the statistics API.

#### Connect the Agent

Create a file `powerdns_recursor.yaml` in the Agent's `conf.d` directory. See the [sample powerdns_recursor.yaml][2] for all available configuration options:

```
init_config:

instances:
  - host: 127.0.0.1
    port: 8082
    api_key: changeme
    version: 4 # omit this line if you're running pdns_recursor version 3.x
```

[Restart the Agent][3] to begin sending PowerDNS Recursor metrics to Datadog.

### Validation

[Run the Agent's `status` subcommand][4] and look for `powerdns_recursor` under the Checks section.

## Data Collected
### Metrics
See [metadata.csv][5] for a list of metrics provided by this integration.

### Events
The PowerDns check does not include any event at this time.### Service Checks

### Service Checks
**`powerdns.recursor.can_connect`**:

Returns CRITICAL if the Agent is unable to connect to the recursor's statistics API, otherwise OK.

## Troubleshooting
Need help? Contact [Datadog Support][6].

## Further Reading
Learn more about infrastructure monitoring and all our integrations on [our blog][7]


[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://github.com/DataDog/integrations-core/blob/master/powerdns_recursor/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[4]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[5]: https://github.com/DataDog/integrations-core/blob/master/powerdns_recursor/metadata.csv
[6]: http://docs.datadoghq.com/help/
[7]: https://www.datadoghq.com/blog/
