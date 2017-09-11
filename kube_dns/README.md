# Kube-dns Integration

## Overview

Get metrics from kube-dns service in real time to:

* Visualize and monitor dns metrics collected via Kubernetes' kube-dns addon
  through Prometheus

See https://github.com/kubernetes/kubernetes/tree/master/cluster/addons/dns for
more informations about kube-dns

## Setup
### Installation

Install the `dd-check-kube_dns` package manually or with your favorite configuration manager

### Configuration

Edit the `kube_dns.yaml` file to point to your server and port, set the masters to monitor

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

When you run `datadog-agent info` you should see something like the following:

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