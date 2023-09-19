# Network check

![Network Dashboard][1]

## Overview

The network check collects TCP/IP stats from the host operating system.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host.

### Installation

The network check is included in the [Datadog Agent][2] package, so you don't need to install anything else on your server.

To collect metrics with this integration, make sure the conntrack module is activated on your host. If it's not the case, run:

```shell
sudo modprobe nf_conntrack
sudo modprobe nf_conntrack_ipv4
sudo modprobe nf_conntrack_ipv6
```

*Note*: You may need to install the conntrack binary in the Agent image.

### Configuration

1. The Agent enables the network check by default, but if you want to configure the check yourself, edit file `network.d/conf.yaml`, in the `conf.d/` folder at the root of your [Agent's configuration directory][3]. See the [sample network.d/conf.yaml][4] for all available configuration options.

2. [Restart the Agent][5] to effect any configuration changes.

**Note**:

Some conntrack metrics require running conntrack with privileged access to be retrieved.

Linux: Configure the following sudoers rule for this to work:

```shell
dd-agent ALL=NOPASSWD: /usr/sbin/conntrack -S
```

#### Kubernetes  

Conntrack metrics are available by default in Kubernetes < v1.11 or when using the `host` networking mode in Kubernetes v1.11+.  

In order to collect [AWS ENA metrics][12]:

- Update `network` check to enable collection of AWS ENA metrics with `collect_aws_ena_metrics: true`.
- Update Agent containers to use `host` network mode and add `NET_ADMIN` capabilities. 

For Datadog [Helm Chart][11] deployment, update chart values with:

```yaml
datadog:
 # Enable AWS ENA metrics collection for network check
 confd:
   network.yaml: |-
     init_config:
     instances:
       - collect_aws_ena_metrics: true

# Have agent containers use host network with NET_ADMIN capability
agents:
  useHostNetwork: true
  containers:
    agent:
      securityContext:
        capabilities:
          add:
            - NET_ADMIN

```

For Agents manually deployed with DaemonSet, apply `datadog` DaemonSet patch:

```yaml
spec:
  template:
    spec:
      dnsPolicy: ClusterFirstWithHostNet
      hostNetwork: true
      containers:
        - name: agent
          ports:
          - containerPort: 8125
            hostPort: 8125
            name: dogstatsdport
            protocol: UDP
          securityContext:
            capabilities:
              add:
              - NET_ADMIN
```

**Note**: You may need to add `hostPort: 8125` for other containers in the DaemonSet as `hostNetwork: true` will apply to all containers.

### Validation

[Run the Agent's `status` subcommand][6] and look for `network` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

**Note**: `system.net.conntrack` metrics are available with Agent v6.12+. See the [CHANGELOG][8] for details.

### Events

The Network check does not include any events.

### Service Checks

The Network check does not include any service checks.

## Troubleshooting

- [Send TCP/UDP host metrics to the Datadog API][9]

## Further Reading

- [Build a network monitor on an HTTP check][10]

[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/network/images/netdashboard.png
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[4]: https://github.com/DataDog/integrations-core/blob/master/network/datadog_checks/network/data/conf.yaml.default
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/network/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/network/CHANGELOG.md#1110--2019-05-14
[9]: https://docs.datadoghq.com/integrations/guide/send-tcp-udp-host-metrics-to-the-datadog-api/
[10]: https://docs.datadoghq.com/monitors/monitor_types/network/
[11]: https://docs.datadoghq.com/containers/kubernetes/installation/?tab=helm#installation
[12]: https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/monitoring-network-performance-ena.html
