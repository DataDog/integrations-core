### Agent Observability Configuration

Get end-to-end visibility into your LLM application's calls to OpenAI with [LLM Observability][1]. Choose the setup that matches your application's language and environment.

[1]: https://docs.datadoghq.com/llm_observability/setup/sdk/

<!-- xxx tabs xxx -->
<!-- xxx tab "Python" xxx -->

#### If you do not have the Datadog Agent

1. Install the `ddtrace` package:

   ```shell
   pip install ddtrace
   ```

2. Start your application with agentless mode enabled:

   ```shell
   DD_SITE=<YOUR_DATADOG_SITE> DD_API_KEY=<YOUR_API_KEY> DD_LLMOBS_ENABLED=1 DD_LLMOBS_AGENTLESS_ENABLED=1 DD_LLMOBS_ML_APP=<YOUR_ML_APP_NAME> ddtrace-run python <YOUR_APP>.py
   ```

#### If you already have the Datadog Agent installed

1. Make sure the Agent is running and that APM and StatsD are enabled. For example, with Docker:

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
     registry.datadoghq.com/agent:latest
   ```

2. Install the `ddtrace` package if it isn't installed yet:

   ```shell
   pip install ddtrace
   ```

3. Start your application with `ddtrace-run` to automatically enable tracing:

   ```shell
   DD_SITE=<YOUR_DATADOG_SITE> DD_API_KEY=<YOUR_API_KEY> DD_LLMOBS_ENABLED=1 DD_LLMOBS_ML_APP=<YOUR_ML_APP_NAME> ddtrace-run python <YOUR_APP>.py
   ```

**Note**: If the Agent is running on a custom host or port, set `DD_AGENT_HOST` and `DD_TRACE_AGENT_PORT` accordingly.

#### If you are running in a serverless environment (AWS Lambda)

1. Install the **Datadog-Python** and **Datadog-Extension** Lambda layers as part of your AWS Lambda setup.
2. Enable LLM Observability by setting the following environment variables:

   ```shell
   DD_SITE=<YOUR_DATADOG_SITE> DD_API_KEY=<YOUR_API_KEY> DD_LLMOBS_ENABLED=1 DD_LLMOBS_ML_APP=<YOUR_ML_APP_NAME>
   ```

**Note**: In serverless environments, Datadog automatically flushes spans when the Lambda function finishes running.

#### Automatic OpenAI tracing

The following OpenAI methods are traced automatically, capturing latency, input and output messages, and token usage without manual instrumentation:

- `OpenAI().completions.create()`, `OpenAI().chat.completions.create()`
- For async calls: `AsyncOpenAI().completions.create()`, `AsyncOpenAI().chat.completions.create()`

#### Validation

Check your application logs for successful span creation, or confirm the status of the `ddtrace` integration:

```shell
ddtrace-run --info
```

Look for `Agent error: None` in the output.

#### Troubleshooting

Pass the `--debug` flag to `ddtrace-run` to enable debug logging and display detailed information about tracing errors:

```shell
ddtrace-run --debug
```

<!-- xxz tab xxx -->
<!-- xxx tab "Node.js" xxx -->

#### If you do not have the Datadog Agent

1. Install the `dd-trace` package:

   ```shell
   npm install dd-trace
   ```

2. Start your application with agentless mode enabled:

   ```shell
   DD_SITE=<YOUR_DATADOG_SITE> DD_API_KEY=<YOUR_API_KEY> DD_LLMOBS_ENABLED=1 DD_LLMOBS_AGENTLESS_ENABLED=1 DD_LLMOBS_ML_APP=<YOUR_ML_APP_NAME> node -r 'dd-trace/init' <YOUR_APP>.js
   ```

#### If you already have the Datadog Agent installed

1. Make sure the Agent is running and that APM and StatsD are enabled. For example, with Docker:

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
     registry.datadoghq.com/agent:latest
   ```

2. Install the `dd-trace` package:

   ```shell
   npm install dd-trace
   ```

3. Start your application with `-r dd-trace/init` or `NODE_OPTIONS='--require dd-trace/init'` to automatically enable tracing:

   ```shell
   DD_SITE=<YOUR_DATADOG_SITE> DD_API_KEY=<YOUR_API_KEY> DD_LLMOBS_ENABLED=1 DD_LLMOBS_ML_APP=<YOUR_ML_APP_NAME> node -r 'dd-trace/init' <YOUR_APP>.js
   ```

**Note**: If the Agent is running on a custom host or port, set `DD_AGENT_HOST` and `DD_TRACE_AGENT_PORT` accordingly.

#### If you are running in a serverless environment (AWS Lambda)

1. Enable LLM Observability by setting the following environment variables:

   ```shell
   DD_SITE=<YOUR_DATADOG_SITE> DD_API_KEY=<YOUR_API_KEY> DD_LLMOBS_ENABLED=1 DD_LLMOBS_ML_APP=<YOUR_ML_APP_NAME>
   ```

2. Call `llmobs.flush()` before the Lambda function finishes:

   ```js
   const llmobs = require('dd-trace').llmobs;
   // or, if dd-trace was not initialized through NODE_OPTIONS
   const llmobs = require('dd-trace').init({
     llmobs: {
       mlApp: <YOUR_ML_APP>,
     }
   }).llmobs; // with DD_API_KEY and DD_SITE set at the environment level

   async function handler (event, context) {
     ...
     llmobs.flush()
     return ...
   }
   ```

#### Automatic OpenAI tracing

The following OpenAI methods are traced automatically, capturing latency, input and output messages, and token usage without manual instrumentation:

- `client.completions.create()`, `client.chat.completions.create()`, `client.embeddings.create()` (where `client` is an instance of `OpenAI`)

#### Troubleshooting

Set `DD_TRACE_DEBUG=1` to enable debug logging and display detailed information about tracing errors.

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->
