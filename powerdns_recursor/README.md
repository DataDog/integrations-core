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

The PowerDNS Recursor check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your recursors.

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

Create a file `powerdns_recursor.yaml` in the Agent's `conf.d` directory:

```
init_config:

instances:
  - host: 127.0.0.1
    port: 8082
    api_key: changeme
    version: 4 # omit this line if you're running pdns_recursor version 3.x
```

Restart the Agent to begin sending PowerDNS Recursor metrics to Datadog.

### Validation
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

## Compatibility

The PowerDNS Recursor check is compatible with all major platforms.

## Data Collected
### Metrics
See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/powerdns_recursor/metadata.csv) for a list of metrics provided by this integration.

### Events
The PowerDns check does not include any event at this time.### Service Checks

### Service Checks
**`powerdns.recursor.can_connect`**:

Returns CRITICAL if the Agent is unable to connect to the recursor's statistics API, otherwise OK.

## Troubleshooting

If you have any questions about Datadog or a use case our [Docs](https://docs.datadoghq.com/) didn’t mention, we’d love to help! Here’s how you can reach out to us:

### Visit the Knowledge Base

Learn more about what you can do in Datadog on the [Support Knowledge Base](https://datadog.zendesk.com/agent/).

### Web Support

Messages in the [event stream](https://app.datadoghq.com/event/stream) containing **@support-datadog** will reach our Support Team. This is a convenient channel for referencing graph snapshots or a particular event. In addition, we have a livechat service available during the day (EST) from any page within the app.

### By Email

You can also contact our Support Team via email at [support@datadoghq.com](mailto:support@datadoghq.com).

### Over Slack

Reach out to our team and other Datadog users on [Slack](http://chat.datadoghq.com/).

## Further Reading
### Blog Article
Learn more about infrastructure monitoring and all our integrations on [our blog](https://www.datadoghq.com/blog/)