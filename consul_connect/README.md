# Agent Check: Consul Connect

## Overview

Monitor your [Consul Connect][1] Envoy sidecar proxies with the Datadog [Envoy Integration][2].

## Setup

### Installation

Follow the [Envoy Integration installation][3] steps to monitor your Consul Connect sidecar proxies.

### Configuration

[Configure the Envoy Integration][4] to monitor your Consul Connect Envoy sidecar proxies and collect Envoy metrics.

### Validation

[Run the Agent's status subcommand][6] and look for `envoy` under the Checks section.

## Data Collected

### Metrics

See the [Envoy Integration documentation][7] for a list of metrics collected. 

### Service Checks

See the [Envoy Integration documentation][8] for the list of service checks collected. 

### Events

Consul Connect does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][5].

[1]: https://docs.datadoghq.com/integrations/consul_connect/
[2]: https://docs.datadoghq.com/integrations/envoy/
[3]: https://docs.datadoghq.com/integrations/envoy/?tab=host#installation
[4]: https://docs.datadoghq.com/integrations/envoy/?tab=host#configuration
[5]: https://docs.datadoghq.com/help/
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/?#agent-status-and-information
[7]: https://docs.datadoghq.com/integrations/envoy/?tab=host#metrics
[8]: https://docs.datadoghq.com/integrations/envoy/?tab=host#service-checks