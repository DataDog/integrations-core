# Agent Check: Network Path

## Overview

Network Path integration collects traceroute data.

## Setup

### Installation

The Network Path check is included in the [Datadog Agent][1] package.
No additional installation is needed.

### Configuration

Example configuration:

```yaml
instances:
  - hostname: example.com # endpoint hostname or IP
    protocol: TCP
    port: 443
    tags:
      - "tag_key:tag_value"
      - "tag_key2:tag_value2"

    ## optional configs:
    # max_ttl: 30 # max traderoute TTL, default is 30
    # timeout: 10 # timeout in seconds of traceroute calls, default is 10s

  - hostname: <another_endpoint>
    protocol: UDP
    port: 53
    tags:
      - "tag_key:tag_value"
      - "tag_key2:tag_value2"
```

## Data Collected

### Metrics

Metrics are listed in `metadata.csv`.

### Service Checks

Network Path does not include any service checks.

### Events

Network Path does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][2].

[1]: https://app.datadoghq.com/account/settings/agent/latest

[2]: https://docs.datadoghq.com/help/

