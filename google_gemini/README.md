# Google Gemini

## Overview

Monitor, troubleshoot, and evaluate your LLM-powered applications, such as chatbots or data extraction tools, using [Google Gemini](https://gemini.google.com/).

If you are building LLM applications, use LLM Observability to investigate the root cause of issues, monitor operational performance, and evaluate the quality, privacy, and safety of your LLM applications.

[LLM Obs tracing view video](https://imgix.datadoghq.com/video/products/llm-observability/expedite-troubleshooting.mp4?fm=webm&fit=max )

## Setup

### LLM Observability: Get end-to-end visibility into your LLM application using Google Gemini
You can enable LLM Observability in different environments. Follow the appropriate setup based on your scenario:

<!-- xxx tabs xxx -->
<!-- xxx tab "Python" xxx -->

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

2. If you haven't already, install the `ddtrace` package:

```shell
  pip install ddtrace
```

3. Start your application using the `ddtrace-run` command to automatically enable tracing:

```shell
   DD_SITE=<YOUR_DATADOG_SITE> DD_API_KEY=<YOUR_API_KEY> DD_LLMOBS_ENABLED=1 DD_LLMOBS_ML_APP=<YOUR_ML_APP_NAME> ddtrace-run python <your_app>.py
```

**Note**: If the Agent is running on a custom host or port, set `DD_AGENT_HOST` and `DD_TRACE_AGENT_PORT` accordingly.

##### If you are running LLM Observability in a serverless environment (AWS Lambda):
1. Install the **Datadog-Python** and **Datadog-Extension** Lambda layers as part of your AWS Lambda setup.
2. Enable LLM Observability by setting the following environment variables:

```shell
   DD_SITE=<YOUR_DATADOG_SITE> DD_API_KEY=<YOUR_API_KEY> DD_LLMOBS_ENABLED=1 DD_LLMOBS_ML_APP=<YOUR_ML_APP_NAME>
```

**Note**: In serverless environments, Datadog automatically flushes spans at the end of the Lambda function.

##### Automatic Google Gemini tracing

The Google Gemini integration provides automatic tracing for the Google AI Python SDK's content generation calls. This captures latency, errors, input/output messages, and token usage for Google Gemini operations.

The following methods are traced for both synchronous and asynchronous Google Gemini operations:
- Generating content (including streamed calls): `model.generate_content()`, `model.generate_content_async()`
- Chat messages: `chat.send_message()`, `chat.send_message_async()`

No additional setup is required for these methods.

##### Validation
Validate that LLM Observability is properly capturing spans by checking your application logs for successful span creation. You can also run the following command to check the status of the `ddtrace` integration:

```shell
ddtrace-run --info
```

Look for the following message to confirm the setup:

```shell
Agent error: None
```

##### Debugging
If you encounter issues during setup, enable debug logging by passing the `--debug` flag:

```shell
ddtrace-run --debug
```

This displays any errors related to data transmission or instrumentation, including issues with Google Gemini traces.

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

### APM: Get usage metrics for Python applications
If you haven't already, set up the [Microsoft Azure integration][1] first. There are no other installation steps.

## Data Collected

### Metrics

See [metadata.csv][2] for a list of metrics provided by this integration.

### Service Checks

The Azure OpenAI integration does not include any service checks.

### Events

The Azure OpenAI integration does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][3].

[1]: https://docs.datadoghq.com/integrations/azure/
[2]: https://github.com/DataDog/integrations-internal-core/blob/main/azure_openai/metadata.csv
[3]: https://docs.datadoghq.com/help/

