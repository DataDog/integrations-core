### APM Configuration

Collect request duration, token usage, and error metrics from your OpenAI calls with a Datadog APM tracing library.

**Note**: This setup method does not collect `audio_speeches`, `audio_transcriptions`, `code_interpreter_sessions`, `completions`, `embeddings`, `images`, `moderations`, and `vector_stores` usage metrics. To collect these metrics, also configure the **Usage and Cost** interface.

#### Step 1: Enable APM and StatsD in the Datadog Agent

For example, with Docker:

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

#### Step 2: Install the tracing library and instrument your application

<!-- xxx tabs xxx -->
<!-- xxx tab "Python" xxx -->

1. Install the Datadog APM Python library:

   ```shell
   pip install ddtrace
   ```

2. Prefix your OpenAI Python application command with `ddtrace-run` and the following environment variables:

   ```shell
   DD_SERVICE="my-service" DD_ENV="staging" ddtrace-run python <YOUR_APP>.py
   ```

**Notes**:

- Non-US1 customers must set `DD_SITE` on the application command to the correct [Datadog site][1] parameter (for example, `datadoghq.eu` for EU1 customers).
- If the Agent uses a non-default hostname or port, also set `DD_AGENT_HOST`, `DD_TRACE_AGENT_PORT`, or `DD_DOGSTATSD_PORT`.

See the [APM Python library documentation][2] for more advanced usage, and the [OpenAI integration documentation][3] for all the available configuration options.

#### Validation

Validate that the APM Python library can communicate with your Agent:

```shell
ddtrace-run --info
```

Look for `Agent error: None` in the output.

#### Troubleshooting

Pass the `--debug` flag to `ddtrace-run` to enable debug logging:

```shell
ddtrace-run --debug
```

This displays any errors sending data, for example:

```
ERROR:ddtrace.internal.writer.writer:failed to send, dropping 1 traces to intake at http://localhost:8126/v0.5/traces after 3 retries ([Errno 61] Connection refused)
```

[1]: https://docs.datadoghq.com/getting_started/site/#access-the-datadog-site
[2]: https://ddtrace.readthedocs.io/en/stable/installation_quickstart.html
[3]: https://ddtrace.readthedocs.io/en/stable/integrations.html#openai

<!-- xxz tab xxx -->
<!-- xxx tab "Node.js" xxx -->

1. Install the Datadog APM Node.js library:

   ```shell
   npm install dd-trace
   ```

2. Inject the library into your OpenAI Node.js application:

   ```shell
   DD_TRACE_DEBUG=1 DD_TRACE_BEAUTIFUL_LOGS=1 DD_SERVICE="my-service" \
     DD_ENV="staging" DD_API_KEY=<DATADOG_API_KEY> \
     NODE_OPTIONS='-r dd-trace/init' node <YOUR_APP>.js
   ```

**Notes**:

- Non-US1 customers must set `DD_SITE` on the application command to the correct [Datadog site][1] parameter (for example, `datadoghq.eu` for EU1 customers).
- If the Agent uses a non-default hostname or port, also set `DD_AGENT_HOST`, `DD_TRACE_AGENT_PORT`, or `DD_DOGSTATSD_PORT`.

See the [APM Node.js OpenAI documentation][2] for more advanced usage, and the [APM Node.js library documentation][3] for all the available configuration options.

#### Validation

Validate that the APM Node.js library can communicate with your Agent by examining the debugging output from the application process. Within the section titled "Encoding payload," you should see an entry with a `name` field and a correlating value of `openai.request`. For example (truncated):

```json
{
  "name": "openai.request",
  "resource": "listModels",
  "meta": {
    "component": "openai",
    "span.kind": "client",
    "openai.api_base": "https://api.openai.com/v1",
    "openai.request.endpoint": "/v1/models",
    "openai.request.method": "GET",
    "language": "javascript"
  },
  "metrics": {
    "openai.response.count": 106
  },
  "service": "my-service",
  "type": "openai"
}
```

[1]: https://docs.datadoghq.com/getting_started/site/#access-the-datadog-site
[2]: https://datadoghq.dev/dd-trace-js/interfaces/plugins.openai.html
[3]: https://github.com/DataDog/dd-trace-js

<!-- xxz tab xxx -->
<!-- xxx tab "PHP" xxx -->

1. [Install the Datadog APM PHP library][1].
2. The library is automatically injected into your OpenAI PHP application.

**Notes**:

- Non-US1 customers must set `DD_SITE` to the correct [Datadog site][2] parameter (for example, `datadoghq.eu` for EU1 customers).
- If the Agent uses a non-default hostname or port, also set `DD_AGENT_HOST`, `DD_TRACE_AGENT_PORT`, or `DD_DOGSTATSD_PORT`.

See the [APM PHP library documentation][3] for more advanced usage and all the available configuration options.

#### Validation

Examine the `phpinfo` output of your service. Under the `ddtrace` section, `Diagnostic checks` should be `passed`.

[1]: https://docs.datadoghq.com/tracing/trace_collection/automatic_instrumentation/dd_libraries/php/#install-the-extension
[2]: https://docs.datadoghq.com/getting_started/site/#access-the-datadog-site
[3]: https://docs.datadoghq.com/tracing/trace_collection/library_config/php/

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->
