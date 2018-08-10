# Agent Check: TCP RTT (go-metro)

## Overview

The TCP RTT check reports on roundtrip times between the host the agent is running on and any host it is communicating with. This check is passive and will only report RTT times for packets being sent and received from outside the check. The check itself will not send any packets.

This check is only shipped in the 64-bit DEB and RPM Datadog Agent v5 packages. The check is currently _not_ available with Datadog Agent v6.

## Setup
### Installation

The TCP RTT check-also known as [go-metro][1]-is packaged with the Agent, but requires additional system libraries. The check uses timestamps provided by the PCAP library to compute the time between any outgoing packet and the corresponding TCP acknowledgement. As such, PCAP must be installed and configured.

Debian-based systems should use one of the following:

```bash
$ sudo apt-get install libcap
$ sudo apt-get install libcap2-bin
```

Redhat-based systems should use one of these:

```bash
$ sudo yum install libcap
$ sudo yum install compat-libcap1
```

Finally, configure PCAP:

```bash
$ sudo setcap cap_net_raw+ep /opt/datadog-agent/bin/go-metro
```

### Configuration

Edit the ```go-metro.yaml``` file in your agent's ```conf.d``` directory. See the [sample go-metro.yaml][2] for all available configuration options. The following is an example file that will show the TCP RTT times for app.datadoghq.com and 192.168.0.22:

  ```yaml
    init_config:
      snaplen: 512
      idle_ttl: 300
      exp_ttl: 60
      statsd_ip: 127.0.0.1
      statsd_port: 8125
      log_to_file: true
      log_level: info
    instances:
      - interface: eth0
        tags:
          - env:prod
        ips:
          - 45.33.125.153
        hosts:
          - app.datadoghq.com
  ```

### Validation

To validate that the check is running correctly, you should see `system.net.tcp.rtt` metrics showing in the Datadog interface. Also, if you [Run the Agent's `status` subcommand][6], you should see something similar to the following:

```
● datadog-agent.service - "Datadog Agent"
    Loaded: loaded (/lib/...datadog-agent.service; enabled; vendor preset: enabled)
    Active: active (running) since Thu 2016-03-31 20:35:27 UTC; 42min ago
  Process: 10016 ExecStop=/opt/.../supervisorctl -c /etc/dd-....conf shutdown (code=exited, status=0/SUCCESS)
  Process: 10021 ExecStart=/opt/.../start_agent.sh (code=exited, status=0/SUCCESS)
  Main PID: 10025 (supervisord)
    CGroup: /system.slice/datadog-agent.service
            ├─10025 /opt/datadog-...python /opt/datadog-agent/bin/supervisord -c /etc/dd-agent/supervisor.conf
            ├─10043 /opt/datadog-...python /opt/datadog-agent/agent/dogstatsd.py --use-local-forwarder
            ├─10044 /opt/datadog-agent/bin/go-metro -cfg=/etc/dd-agent/conf.d/go-metro.yaml
            ├─10046 /opt/datadog-.../python /opt/datadog-agent/agent/ddagent.py
            └─10047 /opt/datadog-.../python /opt/datadog-agent/agent/agent.py foreground --use-local-forwarder
```

If the TCP RTT check has started you should see something similar to the go-metro line above.

**This is a passive check, so unless there are packets actively being sent to the hosts mentioned in the yaml file, the metrics are not reported.**

## Data Collected
### Metrics

See [metadata.csv][3] for a list of metrics provided by this check.

### Events
The Go-metro check does not include any events at this time.

### Service Checks
The Go-metro check does not include any service checks at this time.

## Troubleshooting
Need help? Contact [Datadog Support][4].

[1]: https://github.com/DataDog/go-metro
[2]: https://github.com/DataDog/integrations-core/blob/master/go-metro/conf.yaml.example
[3]: https://github.com/DataDog/integrations-core/blob/master/go-metro/metadata.csv
[4]: https://docs.datadoghq.com/help/
[6]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
