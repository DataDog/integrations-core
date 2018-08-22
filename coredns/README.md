# CoreDNS Integration

## Overview
Get metrics from CoreDNS in real time to:

* Visualize and monitor DNS failures and cache hits/misses
## Setup

### Installation
1. Download the Datadog Agent.
2. Download the `datadog_checks/coredns/coredns.py` file.
3. Place it in the Agent's checks.d directory.

### Configuration
1. Download the `datadog_checks/coredns/data/conf.yaml.example`
2. Place file in the Datadog Agent's `conf.d` directory.
3. Rename file to coredns.yaml
4. Edit file to point to your server and port.
5. [Restart the Agent][3] to begin sending CoreDNS metrics to Datadog.

### Validation

[Run the Agent's `status` subcommand][4] and look for `coredns` under the Checks section:

```
  Checks
  ======
    [...]

    coredns
    -------
      - instance #0 [OK]
      - Collected 26 metrics, 0 events & 1 service check

    [...]
```

## Compatibility

The check is compatible with Linux.

## Data Collected

### Metrics

See [metadata.csv][5] for a list of metrics provided by this integration.

### Events
The CoreDNS check does not include any event at this time.

### Service Checks
The CoreDNS check does not include any service checks at this time.

## Troubleshooting
Need help? Contact [Datadog Support][7].

## Development

Please refer to the [main documentation][6]
for more details about how to test and develop Agent based integrations.

[1]: https://raw.githubusercontent.com/DataDog/cookiecutter-datadog-check/master/%7B%7Bcookiecutter.check_name%7D%7D/images/snapshot.png
[2]: #metrics
[3]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[4]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[5]: https://github.com/DataDog/cookiecutter-datadog-check/blob/master/%7B%7Bcookiecutter.check_name%7D%7D/metadata.csv
[6]: https://docs.datadoghq.com/developers/
[7]: http://docs.datadoghq.com/help/