# Agent Check: LiteLLM

## Overview

[LiteLLM][1] is a lightweight, open-source proxy and analytics layer for large language model (LLM) APIs. It enables unified access, observability, and cost control across multiple LLM providers.

This integration provides real-time monitoring, alerting, and analytics for all LLM API usage through LiteLLM, helping customers optimize performance, manage costs, and ensure reliability across their AI-powered applications.

Key metrics such as request/response counts, latency, error rates, token usage, and spend per provider or deployment are monitored. This data enables customers to track usage patterns, detect anomalies, control costs, and troubleshoot issues quickly, ensuring efficient and reliable LLM operations through LiteLLM's health check and Prometheus endpoints.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][3] for guidance on applying these instructions.

### Installation

Starting from Agent 7.68.0, the LiteLLM check is included in the [Datadog Agent][2] package. No additional installation is needed on your server.

### Configuration

This integration collects metrics through the Prometheus endpoint exposed by the LiteLLM Proxy. This feature is only available for enterprise users of LiteLLM. By default, the metrics are exposed on the `/metrics` endpoint. If connecting locally, the default port is 4000. For more information, see the [LiteLLM Prometheus documentation][10].

Note: The listed metrics can only be collected if they are available. Some metrics are generated only when certain actions are performed. For example, the `litellm.auth.failed_requests.count` metric might only be exposed after an authentication failed request has occurred.

#### Host-based

1. Edit the `litellm.d/conf.yaml` file in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your LiteLLM performance data. See the [sample litellm.d/conf.yaml][4] for all available configuration options. Example config:

```yaml
init_config:

instances:
  - openmetrics_endpoint: http://localhost:4000/metrics
    # If authorization is required to access the endpoint, use the settings below.
    # headers:
    #  Authorization: Bearer sk-1234
```

2. [Restart the Agent][5].

#### Kubernetes-based

For LiteLLM Proxy running on Kubernetes, configuration can be easily done via pod annotations. See the example below:

```yaml
apiVersion: v1
kind: Pod
# (...)
metadata:
  name: '<POD_NAME>'
  annotations:
    ad.datadoghq.com/<CONTAINER_NAME>.checks: | # <CONTAINER_NAME> must match the container name specified in the containers section below.
      {
        "litellm": {
          "init_config": {},
          "instances": [
            {
              "openmetrics_endpoint": "http://%%host%%:4000/metrics"
            }
          ]
        }
      }
    # (...)
spec:
  containers:
    - name: <CONTAINER_NAME>
# (...)
```

For more information and alternative ways to configure the check in Kubernetes-based environments, see the [Kubernetes Integration Setup documentation][3].

#### Logs

LiteLLM can send logs to Datadog through its callback system. You can configure various logging settings in LiteLLM to customize log formatting and delivery to Datadog for ingestion. For detailed configuration options and setup instructions, refer to the [LiteLLM Logging Documentation][11].

### Validation

Run the Agent's status subcommand ([see documentation][6]) and look for `litellm` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

The LiteLLM integration does not include any events.

### Service Checks

The LiteLLM integration does not include any service checks.

See [service_checks.json][8] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][9].


[1]: https://www.litellm.ai/
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[4]: https://github.com/DataDog/integrations-core/blob/master/litellm/datadog_checks/litellm/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/litellm/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/litellm/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
[10]: https://docs.litellm.ai/docs/proxy/prometheus
[11]: https://docs.litellm.ai/docs/proxy/logging
