# CoreDNS Integration

## Overview
Get metrics from CoreDNS in real time to visualize and monitor DNS failures and cache hits/misses.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][7] for guidance on applying these instructions.

### Installation

The CoreDNS check is included in the [Datadog Agent][1] package, so you don't need to install anything else on your servers.

### Configuration

Edit the `coredns.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][2], to point to your server and port and set the masters to monitor. See the [sample coredns.d/conf.yaml][3] for all available configuration options.

#### Using with service discovery

If you are using one dd-agent pod (daemon set) per kubernetes worker nodes, use the following annotations on your core-dns pod to retrieve the data automatically.

```yaml
metadata:
  annotations:
    ad.datadoghq.com/coredns.check_names: '["coredns"]'
    ad.datadoghq.com/coredns.init_configs: '[{}]'
    ad.datadoghq.com/coredns.instances: '[{"prometheus_url":"http://%%host%%:9153/metrics", "tags":["dns-pod:%%host%%"]}]'
```

**Note:**

 * The `dns-pod` tag keeps track of the target dns pod IP. The other tags are related to the dd-agent that is polling the information using the service discovery.
 * The service discovery annotations need to be done on the pod. In case of a deployment, add the annotations to the metadata of the template's specifications. Do not add it at the outer specification level.


### Validation

[Run the Agent's `status` subcommand][4] and look for `coredns` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][5] for a list of metrics provided by this integration.

### Events

The CoreDNS check does not include any events.

### Service Checks

`coredns.prometheus.health`:

Returns `CRITICAL` if the Agent cannot reach the metrics endpoints.

## Troubleshooting

Need help? Contact [Datadog support][6].

## Development

See the [main documentation][2]
for more details about how to test and develop Agent based integrations.

[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://docs.datadoghq.com/developers
[3]: https://github.com/DataDog/integrations-core/blob/master/coredns/datadog_checks/coredns/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[5]: https://github.com/DataDog/integrations-core/blob/master/coredns/metadata.csv
[6]: http://docs.datadoghq.com/help
[7]: https://docs.datadoghq.com/agent/autodiscovery/integrations
