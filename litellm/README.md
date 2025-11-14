# LiteLLM

## Overview

Monitor, troubleshoot, and evaluate your LLM-powered applications built using [LiteLLM][1]: a lightweight, open-source proxy and analytics layer for large language model (LLM) APIs. It enables unified access, observability, and cost control across multiple LLM providers.

Use LLM Observability to investigate the root cause of issues, monitor operational performance, and evaluate the quality, privacy, and safety of your LLM applications.

See the [LLM Observability tracing view video](https://imgix.datadoghq.com/video/products/llm-observability/expedite-troubleshooting.mp4?fm=webm&fit=max) for an example of how you can investigate a trace.

Get cost estimation, prompt and completion sampling, error tracking, performance metrics, and more out of [LiteLLM][1] Python library requests using Datadog metrics and APM.

Key metrics such as request/response counts, latency, error rates, token usage, and spend per provider or deployment are monitored. This data enables customers to track usage patterns, detect anomalies, control costs, and troubleshoot issues quickly, ensuring efficient and reliable LLM operations through LiteLLM's health check and Prometheus endpoints.

**Minimum Agent version:** 7.68.0

## Setup

You can configure this integration either as a standalone integration or as an agent check:

<!-- xxx tabs xxx -->
<!-- xxx tab "LLM Observability" xxx -->
Get end-to-end visibility into your LLM application using LiteLLM.

See the [LiteLLM integration docs][12] for details on how to get started with LLM Observability for LiteLLM.
<!-- xxz tab xxx -->

<!-- xxx tab "Agent Check: LiteLLM" xxx -->
Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][3] for guidance on applying these instructions.

#### Installation

Starting from Agent 7.68.0, the LiteLLM check is included in the [Datadog Agent][2] package. No additional installation is needed on your server.

#### Configuration

This integration collects metrics through the Prometheus endpoint exposed by the LiteLLM Proxy. This feature is only available for enterprise users of LiteLLM. By default, the metrics are exposed on the `/metrics` endpoint. If connecting locally, the default port is 4000. For more information, see the [LiteLLM Prometheus documentation][10].

Note: The listed metrics can only be collected if they are available. Some metrics are generated only when certain actions are performed. For example, the `litellm.auth.failed_requests.count` metric might only be exposed after an authentication failed request has occurred.

##### Host-based

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

##### Kubernetes-based

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

##### Logs

LiteLLM can send logs to Datadog through its callback system. You can configure various logging settings in LiteLLM to customize log formatting and delivery to Datadog for ingestion. For detailed configuration options and setup instructions, refer to the [LiteLLM Logging Documentation][11].

#### Validation

Run the Agent's status subcommand ([see documentation][6]) and look for `litellm` under the Checks section.

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

The LiteLLM integration does not include any events.

### Service Checks

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
[12]: https://docs.datadoghq.com/llm_observability/instrumentation/auto_instrumentation?tab=python#litellm
