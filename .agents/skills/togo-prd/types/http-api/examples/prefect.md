# Prefect integration

## Overview

Build a Datadog Agent integration for self-hosted Prefect Server using its JSON REST API. Use
`prefect` as the integration directory and `prefect.server` as the metric namespace: the integration
monitors the Prefect server (the orchestration control plane), not the machines that run flows. It
targets the open-source, self-hosted Prefect Server, 3.2 and later 3.x releases.

Data and platform teams use Prefect to schedule and run Python workflows (flows and their tasks)
through work pools and workers. They monitor the server to know that work is being picked up, to
catch runs that are late, stuck, or failing, and to see how long work waits before it starts.

## What users need to see

- Server health and readiness: whether the API answers and whether it is ready to accept and
  dispatch work.
- Work pools: whether each pool is ready, not ready, or paused, sliced by pool and pool type.
- Workers: whether each worker is online, and how long since its last heartbeat, sliced by work pool
  and worker, so users can alert on a worker that stopped polling.
- Work queues: whether each queue is ready, not ready, or paused, how long since a worker last
  polled it, the backlog (the queue's runs in Prefect's `Late` state) and the age of the oldest one,
  sliced by work pool, queue, and queue priority. Runs scheduled for the future are not backlog.
- Deployments: whether each deployment is ready, not ready, or paused, sliced by deployment, flow,
  work pool, and queue.
- Flow runs in progress: how many are late (Prefect's `Late` state), pending, running, and paused,
  and how long each has been pending or running, so users can alert on a stuck run. Sliced by work
  pool, queue, deployment, and flow.
- Outcomes of completed flow runs: completed, failed, cancelled, and crashed counts, throughput,
  execution duration, and queue wait (actual start minus expected start), with the same slicing.
- Task runs: the same states, outcomes, throughput, and execution duration as flow runs, also sliced
  by task key.
- Datadog events, off by default, for flow run and task run state changes from the Prefect events
  API.
- The container logs of the Prefect server and workers, which log to standard output, collected by
  the Agent.

Optional, only when the API supports a reliable interpretation: concurrency limit usage, the gap
between retries of the same flow run, and how long a task run waited for its upstream dependencies.

## Design choices

- Default check interval: 15 seconds.
- Installation sizes: up to tens of work pools and queues, hundreds of deployments, and thousands of
  flow runs per hour.
- Filters: include and exclude filters for work pools, work queues, deployments, and the names of
  the events submitted to Datadog. Users must be able to scope queues within a particular work pool.
- Limits: global.
- Auth: the API is either open or protected by basic authentication through the server's
  `PREFECT_SERVER_API_AUTH_STRING` setting; both must work. When it is protected, the customer
  gives the Agent that credential; nothing else needs to be set up. Prefect Server has no roles: the
  auth string grants full API access, and the docs must say so.
- Unified service tagging: none.
- Compatibility: no older integration or script to stay compatible with.

## Out of scope

- Prefect Cloud: its API is hosted and scoped to accounts and workspaces, and it is not tested.
- Polling flow run logs through the API.

## Documentation

- [Server REST API](https://www.prefect.io/docs/v3/api-ref/rest-api/server/index)
- [Health check](https://www.prefect.io/docs/v3/api-ref/rest-api/server/root/health-check)
- [Read work
  pools](https://www.prefect.io/docs/v3/api-ref/rest-api/server/work-pools/read-work-pools)
- [Read flow runs](https://www.prefect.io/docs/v3/api-ref/rest-api/server/flow-runs/read-flow-runs)
- [Count flow
  runs](https://www.prefect.io/docs/v3/api-ref/rest-api/server/flow-runs/count-flow-runs)
- [Read task runs](https://www.prefect.io/docs/v3/api-ref/rest-api/server/task-runs/read-task-runs)
- [Read events](https://www.prefect.io/docs/v3/api-ref/rest-api/server/events/read-events)
- [Work pools](https://www.prefect.io/docs/v3/concepts/work-pools)
- [Workers](https://www.prefect.io/docs/v3/concepts/workers)
- [Deployments](https://www.prefect.io/docs/v3/concepts/deployments)
- [Flows](https://www.prefect.io/docs/v3/concepts/flows)
- [Tasks](https://www.prefect.io/docs/v3/concepts/tasks)
- [States](https://www.prefect.io/docs/v3/concepts/states)
- [Events](https://www.prefect.io/docs/v3/concepts/events)
- [Global concurrency
  limits](https://www.prefect.io/docs/v3/how-to-guides/workflows/global-concurrency-limits)
- [Security settings](https://www.prefect.io/docs/v3/advanced/security-settings)
- [Prefect source at 3.9.1](https://github.com/PrefectHQ/prefect/tree/3.9.1/src/prefect)
