# External DNS Integration

## Overview

Get metrics from the external DNS service in real time to visualize and monitor DNS metrics collected with the Kubernetes external DNS Prometheus add on.

For more information about external DNS, see the [Github repo][1].

## Setup

### Installation

The external DNS check is included in the [Datadog Agent][2] package, so you don't need to install anything else on your servers.

### Configuration

Edit the `external_dns.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][3], to point to your server and port, and to set the masters to monitor. See the [sample external_dns.d/conf.yaml][4] for all available configuration options.

#### Using with service discovery

If you are using one Datadog Agent pod per Kubernetes worker node, use these example annotations on your external-dns pod to retrieve the data automatically:

```yaml
apiVersion: v1
kind: Pod
metadata:
  annotations:
    ad.datadoghq.com/external-dns.check_names: '["external_dns"]'
    ad.datadoghq.com/external-dns.init_configs: '[{}]'
    ad.datadoghq.com/external-dns.instances: '[{"prometheus_url":"http://%%host%%:7979/metrics", "tags":["externaldns-pod:%%host%%"]}]'
```

- The `externaldns-pod` tag keeps track of the target DNS pod IP. The other tags are related to the Datadog Agent that is polling the information using the autodiscovery.
- The autodiscovery annotations are done on the pod. To deploy, add the annotations to the metadata of the template's specification.

### Validation

[Run the Agent's `status` subcommand][5] and look for `external_dns` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][6] for a list of metrics provided by this integration.

### Events

The external DNS check does not include any events.

### Service Checks

See [service_checks.json][7] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][8].

[1]: https://github.com/kubernetes-incubator/external-dns
[2]: /account/settings/agent/latest
[3]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[4]: https://github.com/DataDog/integrations-core/blob/master/external_dns/datadog_checks/external_dns/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[6]: https://github.com/DataDog/integrations-core/blob/master/external_dns/metadata.csv
[7]: https://github.com/DataDog/integrations-core/blob/master/external_dns/assets/service_checks.json
[8]: https://docs.datadoghq.com/help/
