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
    # tcp_method: syn # traceroute method, default is syn

  - hostname: <another_endpoint>
    protocol: UDP
    port: 53
    tags:
      - "tag_key:tag_value"
      - "tag_key2:tag_value2"
```
#### Note for Windows hosts
Windows Server supports tcp_methods syn, and syn_socket (syn is recomended).

Windows Client OS only supports syn_socket as raw sockets are not supported on Windows Clients. 



## Data Collected

### Metrics

Metrics are listed in `metadata.csv`.

### Service Checks

Network Path does not include any service checks.

### Events

Network Path does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][2].

[1]: /account/settings/agent/latest

[2]: https://docs.datadoghq.com/help/

