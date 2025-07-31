# Agent Check: LiteLLM

## Overview

Monitor, troubleshoot, and evaluate your LLM-powered applications built using [LiteLLM][1]: a lightweight, open-source proxy and analytics layer for large language model (LLM) APIs. It enables unified access, observability, and cost control across multiple LLM providers.

Use LLM Observability to investigate the root cause of issues, monitor operational performance, and evaluate the quality, privacy, and safety of your LLM applications.

See the [LLM Observability tracing view video](https://imgix.datadoghq.com/video/products/llm-observability/expedite-troubleshooting.mp4?fm=webm&fit=max) for an example of how you can investigate a trace.

Integrating with Datadog Metrics provides real-time monitoring, alerting, and analytics for all LLM API usage through LiteLLM, helping customers optimize performance, manage costs, and ensure reliability across their AI-powered applications.

Key metrics such as request/response counts, latency, error rates, token usage, and spend per provider or deployment are monitored. This data enables customers to track usage patterns, detect anomalies, control costs, and troubleshoot issues quickly, ensuring efficient and reliable LLM operations through LiteLLM's health check and Prometheus endpoints.

## Setup

### LLM Observability: Get end-to-end visibility into your LLM application using LiteLLM
You can enable LLM Observability in different environments. Follow the appropriate setup based on your scenario:

#### Installation for Python

##### If you do not have the Datadog Agent:
1. Install the `ddtrace` package:

   ```shell
   pip install ddtrace
   ```

2. Start your application with the following command, enabling Agentless mode:

   ```shell
    DD_SITE=<YOUR_DATADOG_SITE> DD_API_KEY=<YOUR_API_KEY> DD_LLMOBS_ENABLED=1 DD_LLMOBS_AGENTLESS_ENABLED=1 DD_LLMOBS_ML_APP=<YOUR_ML_APP_NAME> ddtrace-run python <YOUR_APP>.py
   ```
  
##### If you already have the Datadog Agent installed:
1. Make sure the Agent is running and that APM and StatsD are enabled. For example, use the following command with Docker:

   ```shell
   docker run -d \
     --cgroupns host \
     --pid host \
     -v /var/run/docker.sock:/var/run/docker.sock:ro \
     -v /proc/:/host/proc/:ro \
     -v /sys/fs/cgroup/:/host/sys/fs/cgroup:ro \
     -e DD_API_KEY=<DATADOG_API_KEY> \
     -p 127.0.0.1:8126:8126/tcp \
     -p 127.0.0.1:8125:8125/udp \
     -e DD_DOGSTATSD_NON_LOCAL_TRAFFIC=true \
     -e DD_APM_ENABLED=true \
     gcr.io/datadoghq/agent:latest
   ```

2. Install the `ddtrace` package if it isn't installed yet:

   ```shell
   pip install ddtrace
   ```

3. Start your application using the `ddtrace-run` command to automatically enable tracing:

   ```shell
     DD_SITE=<YOUR_DATADOG_SITE> DD_API_KEY=<YOUR_API_KEY> DD_LLMOBS_ENABLED=1 DD_LLMOBS_ML_APP=<YOUR_ML_APP_NAME> ddtrace-run python <YOUR_APP>.py
   ```

**Note**: If the Agent is running on a custom host or port, set `DD_AGENT_HOST` and `DD_TRACE_AGENT_PORT` accordingly.

##### If you are running LLM Observability in a serverless environment (AWS Lambda):
1. Install the **Datadog-Python** and **Datadog-Extension** Lambda layers as part of your AWS Lambda setup.
2. Enable LLM Observability by setting the following environment variables:

   ```shell
    DD_SITE=<YOUR_DATADOG_SITE> DD_API_KEY=<YOUR_API_KEY> DD_LLMOBS_ENABLED=1 DD_LLMOBS_ML_APP=<YOUR_ML_APP_NAME>
   ```

**Note**: In serverless environments, Datadog automatically flushes spans when the Lambda function finishes running.

##### Automatic LiteLLM Tracing

The LiteLLM integration is automatically enabled when LLM Observability is configured. This captures latency, errors, input/output messages, and token usage for LiteLLM operations.

The following LiteLLM methods are traced:

- Chat Completions: `litellm.completion()`, `litellm.acompletion()`
- Completions: `litellm.text_completion()`, `litellm.atext_completion()`
- Router Chat Completions: `router.Router.completion()`, `router.Router.acompletion()`
- Router Completions: `router.Router.text_completion()`, `router.Router.atext_completion()`

No additional setup is required for these methods.

##### Validation

Validate that LLM Observability is properly capturing spans by checking your application logs for successful span creation. You can also run the following command to check the status of the `ddtrace` integration:

   ```shell
   ddtrace-run --info
   ```

Look for the following message to confirm the setup:

   ```
   Agent error: None
   ```

##### Debugging
If you encounter issues during setup, enable debug logging by passing the `--debug` flag:

   ```shell
   ddtrace-run --debug
   ```

This will display any errors related to data transmission or instrumentation, including issues with LiteLLM traces.


### Datadog Metrics
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

#### Data Collected

##### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

##### Events

The LiteLLM integration does not include any events.

##### Service Checks

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
