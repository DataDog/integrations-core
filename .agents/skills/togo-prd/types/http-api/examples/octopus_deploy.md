# Octopus Deploy integration

## Overview

Build a Datadog Agent integration for self-hosted Octopus Deploy Server using its JSON REST API. Use
`octopus_deploy` as the integration directory and `octopus_deploy` as the metric namespace.

Platform and release teams use Octopus Deploy to release software to their environments and to run
operational runbooks. They monitor it to know that the server and its deployment targets are
healthy, to catch deployments that are stuck or failing, and to see how often and how fast they
ship.

## Use cases and scope

- Server availability and health: whether the API answers, the server version, and for each server
  node its state (online, offline, in maintenance mode, draining) and its task cap against the tasks
  it is running. In a high-availability cluster, users must see each node separately.
- Deployment target health: health status and whether the target is disabled, sliced by space,
  environment, target role, and operating system where Octopus reports it, so users can alert on
  unreachable infrastructure.
- Inventory: spaces, environments, project groups, and projects, and for each environment whether it
  uses guided failure and whether it allows dynamic infrastructure.
- In-flight work: queued and executing tasks and how long each has been queued or running, so users
  can alert on a stuck task and on a saturated task queue. Runbook runs count as tasks here, and
  users must be able to tell them apart from deployments.
- Manual interventions: deployments waiting on guided failure or on a manual intervention step, and
  how long they have been waiting.
- Outcomes of completed deployments: success, failure, cancellation, and timeout counts, queue time
  and execution time reported separately, and throughput.
- Users slice deployment and task signals by space, project group, project, and environment, and
  must be able to tell which release version a deployment carried.
- Datadog events, off by default, for audit events. The default categories are `DeploymentStarted`,
  `DeploymentSucceeded`, `DeploymentFailed`, `MachineHealthy`, `MachineUnhealthy`,
  `MachineUnavailable`, `MachineAdded`, `MachineDeleted`, `CertificateExpired`, and `LoginFailed`,
  plus the category for certificates about to expire if the server lists one. Users can choose
  other categories from the ones the server supports.
- Deployment task logs as Datadog logs, collected whenever Agent log collection is on, with no
  separate option. Info-level task logs by default; users can choose verbose task logs. Task logs
  follow the same space, project, and environment filters as metrics.
- The Octopus Server log file, collected by the Agent.

Optional, only when the API supports a reliable interpretation: worker health (sliced by worker
pool), tenant slicing of deployment and task signals, DORA metrics from Octopus Insights, the age of
the release currently deployed to each project and environment, and active deployment freezes.

## Versions, editions, and deployment models

- Octopus Server 2026.3 and later releases.
- Self-hosted Octopus Server, with one node or several nodes in a high-availability cluster.

## Setup the customer provides

- A service account with read-only permissions in the spaces to monitor, and an API key for it.
- For the optional DORA metrics, Octopus Insights enabled on the server.

## Design choices

- Default check interval: 15 seconds.
- Installation sizes: typically 1 to 5 spaces, about 100 projects, and tens of targets; large
  installations have about 50 spaces with thousands of projects and targets.
- Filters: include and exclude filters for spaces, project groups, projects, and environments. Users
  must be able to scope projects within a particular space or project group, not only with patterns
  applied everywhere, and to collect only some environments (for example, production only).
- Limits: the space limit is global; the project group, project, and environment limits apply per
  space.
- Auth: an API key sent in the `X-Octopus-ApiKey` header. Document a read-only service account as
  the least-privileged setup.
- Unified service tagging, opt-in: `service` from the project, `env` from the environment, and
  `version` from the release.

## Compatibility

None.

## Out of scope

- Octopus Cloud. It exposes the same API, but it is not tested.
- The Octopus Insights reports themselves, beyond the optional DORA metrics.

## Documentation

- [REST API overview](https://octopus.com/docs/api)
- [Official API examples repository](https://github.com/OctopusDeploy/OctopusDeploy-Api)
- [Service accounts](https://octopus.com/docs/security/users-and-teams/service-accounts)
- [Create an API key](https://octopus.com/docs/api/authentication/create-an-api-key)
- [Rate limiting API](https://octopus.com/docs/api/rate-limiting)
- [High availability](https://octopus.com/docs/administration/high-availability)
- [Octopus Server nodes API](https://octopus.com/docs/api/octopus-server-nodes)
- [Tasks](https://octopus.com/docs/tasks)
- [Tasks API](https://octopus.com/docs/api/tasks)
- [Task cap](https://octopus.com/docs/support/increase-the-octopus-server-task-cap)
- [Runbooks](https://octopus.com/docs/runbooks)
- [Deployment targets API](https://octopus.com/docs/api/deployment-targets)
- [Workers API](https://octopus.com/docs/api/workers)
- [Machine policies and health
  checks](https://octopus.com/docs/infrastructure/deployment-targets/machine-policies)
- [Deployments API](https://octopus.com/docs/api/deployments)
- [Guided failures](https://octopus.com/docs/releases/guided-failures)
- [Interruptions API](https://octopus.com/docs/api/interruptions)
- [Auditing](https://octopus.com/docs/security/users-and-teams/auditing)
- [Events API](https://octopus.com/docs/api/events)
- [Log files](https://octopus.com/docs/support/log-files)
- [Tenants](https://octopus.com/docs/tenants)
- [Insights](https://octopus.com/docs/insights)
- [Deployment freezes](https://octopus.com/docs/deployments/deployment-freezes)
- [Octopus Server Linux
  container](https://octopus.com/docs/installation/octopus-server-linux-container)
