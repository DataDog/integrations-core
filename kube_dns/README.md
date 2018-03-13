# Kube-dns Integration

## Overview

Get metrics from kube-dns service in real time to:

* Visualize and monitor dns metrics collected via Kubernetes' kube-dns addon
  through Prometheus

See https://github.com/kubernetes/kubernetes/tree/master/cluster/addons/dns for
more informations about kube-dns

## Setup
### Installation

The Kube-dns check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your servers.

### Configuration

Edit the `kube_dns.yaml` file to point to your server and port, set the masters to monitor. See the [sample kube_dns.yaml](https://github.com/DataDog/integrations-core/blob/master/kube_dns/conf.yaml.example) for all available configuration options.

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

 - Notice the "dns-pod" tag that will keep track of the target dns
   pod IP. The other tags will be related to the dd-agent that is polling the
   informations using the service discovery.
 - The service discovery annotations need to be done on the pod. In case of a deployment,
   add the annotations to the metadata of the template's spec.


### Validation

[Run the Agent's `status` subcommand](https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information) and look for `kube_dns` under the Checks section:

    Checks
    ======

        kube_dns
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The kube_dns check is compatible with all major platforms

## Data Collected
### Metrics
See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/kube_dns/metadata.csv) for a list of metrics provided by this integration.

### Events
The Kube-DNS check does not include any event at this time.

### Service Checks
The Kube-DNS check does not include any service check at this time.

## Troubleshooting
Need help? Contact [Datadog Support](http://docs.datadoghq.com/help/).

## Further Reading
Learn more about infrastructure monitoring and all our integrations on [our blog](https://www.datadoghq.com/blog/)
