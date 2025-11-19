# CrewAI

## Overview
Use the CrewAI integration to monitor, troubleshoot, and evaluate your applications based on [CrewAI][1]'s framework.

**Note**: Requires Python.

**Minimum Agent version:** 7.64.3

## Setup

#### Installation

##### If you do not have the Datadog Agent:
1. Install the `ddtrace` package:

  ```shell
    pip install ddtrace
  ```

2.  Start your application using the following command to enable Agentless mode:

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

3. To automatically enable tracing, start your application using the `ddtrace-run` command:

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

##### Automatic CrewAI tracing

The CrewAI integration allows for automatic tracing of Crew kickoffs, including task/agent/tool invocations, made through [CrewAI's Python SDK][1]. The CrewAI integration also captures latency, errors, input/output messages, and directional data flow linking during Crew executions.

The following CrewAI methods are traced:
- [Crew Kickoff][2]:
  - `crew.kickoff()`
  - `crew.kickoff_async()`
  - `crew.kickoff_for_each()`
  - `crew.kickoff_for_each_async()`

- [Task Execution][3]:
  - `task.execute_sync()`
  - `task.execute_async()`

- [Agent Execution][4]:
  - `agent.execute_task()`

- [Tool Invocation][5]:
  - `tool.invoke()`

No additional setup is required for these methods.

##### Validation

Validate that LLM Observability is properly capturing spans by checking your application logs for successful span creation. You can also run the following command to check the status of the `dd-trace` integration:

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

This displays any errors related to data transmission or instrumentation, including issues with CrewAI traces.

## Data Collected

### Metrics

The CrewAI integration does not include any custom metrics.

### Service Checks

The CrewAI integration does not include any service checks.

### Events

The CrewAI integration does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][6].

[1]: https://docs.crewai.com/introduction
[2]: https://docs.crewai.com/concepts/crews#kicking-off-a-crew 
[3]: https://docs.crewai.com/concepts/tasks
[4]: https://docs.crewai.com/concepts/agents
[5]: https://docs.crewai.com/concepts/tools
[6]: https://docs.datadoghq.com/help/