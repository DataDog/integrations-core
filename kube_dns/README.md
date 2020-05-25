# Kube-dns Integration

## Overview

Get metrics from kube-dns service in real time to:

- Visualize and monitor dns metrics collected via Kubernetes' kube-dns addon
  through Prometheus

See https://github.com/kubernetes/kubernetes/tree/master/cluster/addons/dns for
more informations about kube-dns

## Setup

### Installation

The Kube-dns check is included in the [Datadog Agent][1] package, so you don't need to install anything else on your servers.

### Configuration

Edit the `kube_dns.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][2], to point to your server and port, set the masters to monitor. See the [sample kube_dns.d/conf.yaml][3] for all available configuration options.

#### Using with service discovery

If you are using 1 dd-agent pod per kubernetes worker nodes, you could use the
following annotations on your kube-dns pod to get the data retrieve
automatically.

```yaml
apiVersion: v1
kind: Pod
metadata:
  annotations:
    service-discovery.datadoghq.com/kubedns.check_names: '["kube_dns"]'
    service-discovery.datadoghq.com/kubedns.init_configs: '[{}]'
    service-discovery.datadoghq.com/kubedns.instances: '[[{"prometheus_endpoint":"http://%%host%%:10055/metrics", "tags":["dns-pod:%%host%%"]}]]'
```

**Remarks:**

- Notice the "dns-pod" tag that will keep track of the target dns pod IP. The other tags will be related to the dd-agent that is polling the informations using the service discovery.
- The service discovery annotations need to be done on the pod. In case of a deployment, add the annotations to the metadata of the template's spec.

### Validation

[Run the Agent's `status` subcommand][4] and look for `kube_dns` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][5] for a list of metrics provided by this integration.

### Events

The Kube-DNS check does not include any events.

### Service Checks

The Kube-DNS check does not include any service checks.

## Troubleshooting

Need help? Contact [Datadog support][6].

[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[3]: https://github.com/DataDog/integrations-core/blob/master/kube_dns/datadog_checks/kube_dns/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[5]: https://github.com/DataDog/integrations-core/blob/master/kube_dns/metadata.csv
[6]: https://docs.datadoghq.com/help/
