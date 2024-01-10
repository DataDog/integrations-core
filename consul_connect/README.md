# Agent Check: Consul Connect

## Overview

Monitor your [Consul Connect][1] Envoy sidecar proxies with the [Datadog Envoy Integration][2]. The Consul Connect integration only supports [Consul Connect configured with Envoy][3]. 

## Setup

### Installation

Install the [Datadog Agent][4] on your services running Consul Connect and follow the [Configuration](#configuration) instructions for your appropriate environment.

### Configuration
Follow the instructions below to configure this check for an Agent running on a host. For containerized environments, see the [Containerized](#containerized) section.

<!-- xxx tabs xxx -->
<!-- xxx tab "Host" xxx -->

#### Host

To configure this check for an Agent running on a host:

##### Metric collection
1. In Consul Connect, enable the config option [`-admin-bind`][5] to configure the port where the Envoy Admin API is exposed.

2. Enable the [Envoy integration][6] to configure metric collection.

##### Log collection

Follow the [Envoy host][7] instructions to configure log collection.  

<!-- xxz tab xxx -->
<!-- xxx tab "Containerized" xxx -->

#### Containerized

Follow the [Envoy containerized instructions][8] to configure your Datadog Agent for Envoy. 

##### Metric collection

1. In Consul Connect, enable the config option [`envoy_stats_bind_addr`][9] to ensure the `/stats` endpoint is exposed on the public network.

 2. Configure the [Envoy integration for containerized environments][10] to start collecting metrics. 

##### Log collection

Follow the [Envoy containerized instructions][11] to configure log collection.

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

### Validation

[Run the Agent's status subcommand][12] and look for `envoy` under the Checks section.

## Data Collected

### Metrics

See the [Envoy Integration documentation][13] for a list of metrics collected. 

### Service Checks

See the [Envoy Integration documentation][14] for the list of service checks collected. 

### Events

Consul Connect does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][15].

[1]: https://www.consul.io/docs/connect#connect
[2]: https://docs.datadoghq.com/integrations/envoy/
[3]: https://www.consul.io/docs/connect/proxies/envoy#envoy-integration
[4]: https://app.datadoghq.com/account/settings/agent/latest
[5]: https://www.consul.io/commands/connect/envoy#admin-bind
[6]: https://docs.datadoghq.com/integrations/envoy/?tab=host#metric-collection
[7]: https://docs.datadoghq.com/integrations/envoy/?tab=host#log-collection
[8]: https://docs.datadoghq.com/integrations/envoy/?tab=containerized#containerized
[9]: https://www.consul.io/docs/connect/proxies/envoy#envoy_stats_bind_addr
[10]: https://docs.datadoghq.com/integrations/envoy/?tab=containerized#metric-collection
[11]: https://docs.datadoghq.com/integrations/envoy/?tab=containerized#log-collection
[12]: https://docs.datadoghq.com/agent/guide/agent-commands/?#agent-status-and-information
[13]: https://docs.datadoghq.com/integrations/envoy/?tab=host#metrics
[14]: https://docs.datadoghq.com/integrations/envoy/?tab=host#service-checks
[15]: https://docs.datadoghq.com/help/
