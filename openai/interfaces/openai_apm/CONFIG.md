### APM Configuration

Collect request duration, token usage, and error metrics from your OpenAI calls with a Datadog APM tracing library. Python, Node.js, and PHP are supported.

**Note**: This setup method does not collect `openai.api.usage.*` metrics. To collect those, also configure the API key interface.

**Step 1: Enable APM and StatsD in the Datadog Agent**

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

**Step 2: Install the tracing library and instrument your application**

For Python, install `ddtrace` and prefix your application command with `ddtrace-run`:

```shell
pip install ddtrace
DD_SERVICE="my-service" DD_ENV="staging" ddtrace-run python <YOUR_APP>.py
```

For Node.js and PHP, follow the corresponding [tracing library setup][1].

**Notes**:

- Non-US1 customers must set `DD_SITE` on the application command to the correct [Datadog site][2] parameter.
- If the Agent uses a non-default hostname or port, also set `DD_AGENT_HOST`, `DD_TRACE_AGENT_PORT`, or `DD_DOGSTATSD_PORT`.

### Validation

Confirm the tracing library can reach your Agent:

```shell
ddtrace-run --info
```

Look for `Agent error: None` in the output.

### Troubleshooting

Pass the `--debug` flag to `ddtrace-run` to enable debug logging and surface errors sending data.

[1]: https://docs.datadoghq.com/tracing/trace_collection/dd_libraries/
[2]: https://docs.datadoghq.com/getting_started/site/
