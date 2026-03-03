# Agent Check: Nutanix

## Overview

This check collects resource usage metrics from your Nutanix cluster—CPU, memory, storage, and I/O performance for clusters, hosts, and VMs. It also collects operational activity data from Prism Central, including events, tasks, audits, and alerts.

## Setup

### Installation

The Nutanix check is included in the [Datadog Agent][1] package, so you don't need to install anything else on your server.

### Configuration

In Prism Central, create a user with the following roles:

- Cluster Viewer
- Virtual Machine Viewer
- Prism Viewer
- Monitoring Admin

Then, edit the `nutanix.d/conf.yaml` file in the `conf.d/` folder at the root of your [Agent's configuration directory][2]. See the [sample nutanix.d/conf.yaml][3] for all available configuration options.

[Restart the Agent][4] to start sending Nutanix metrics and activity data to Datadog.

**Note**: The default collection interval is 120 seconds. In practice, setting the interval to 60 seconds or higher results in more reliable and consistent metric collection.

### Validation

Run the [Agent's status subcommand][5] and look for `nutanix` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][6] for a list of metrics provided by this check.

The integration collects metrics across three resource types, each prefixed with its resource name:

- **Cluster** (`nutanix.cluster.*`): storage capacity and usage, CPU and memory allocation, I/O performance, health score, VM counts.
- **Host** (`nutanix.host.*`): per-host CPU, memory, storage, and controller I/O metrics.
- **VM** (`nutanix.vm.*`): per-VM CPU, memory, disk, network, and storage tier metrics.

A `nutanix.health.up` metric reports Prism Central connectivity status (`1` for reachable, `0` otherwise).

#### Collecting activity data

The integration collects operational activity data from Prism Central by default. Each activity type can be toggled independently in the `nutanix.d/conf.yaml` file:

- `collect_events`: Prism Central events (default: `true`)
- `collect_alerts`: alerts with severity information (default: `true`)
- `collect_tasks`: infrastructure tasks, parent tasks only (default: `true`)
  - `collect_subtasks`: include subtasks alongside parent tasks (default: `false`)
- `collect_audits`: user audit logs (default: `true`)

### Events

This check collects activity data from Prism Central and emits them as Datadog events. Each activity type is identified by the `ntnx_type` tag:

- `ntnx_type:event`: Prism Central Events
- `ntnx_type:alert`: Prism Central Alerts
- `ntnx_type:task`: Prism Central Tasks
- `ntnx_type:audit`: Prism Central Audits

Use the `collect_events`, `collect_alerts`, `collect_tasks`, and `collect_audits` parameters in the [sample nutanix.d/conf.yaml][3] to toggle each activity type.

**Note**: By default, only parent tasks are collected. Set `collect_subtasks: true` to include subtasks.

### Service Checks

The integration does not emit any service checks.

## Troubleshooting

### Category tags

Nutanix categories are attached as tags to metrics. By default, only `USER` category tags are collected. To include `SYSTEM` or `INTERNAL` categories, add an explicit category filter in `resource_filters`.

Category tags use the Nutanix category key as the tag name (e.g., `Environment:Production`). Set `prefix_category_tags: true` to prefix them with `ntnx_` (e.g., `ntnx_Environment:Production`) to avoid collisions with existing Datadog tags.

### Filtering resources

Use the `resource_filters` option to control which resources are collected. Each filter requires a `resource` type and a list of regex `patterns`. Optionally, set `property` (defaults vary by resource type) and `type` (`include` or `exclude`, default: `include`). Exclude filters take precedence over include filters.

Supported resource types: `cluster`, `host`, `vm`, `event`, `task`, `alert`, `audit`, `category`. Infrastructure resources (`cluster`, `host`, `vm`) default to matching on `name`. Nested properties are supported using `/` as a separator (e.g., `userReference/name`).

```yaml
resource_filters:
  - resource: cluster
    property: name
    patterns:
      - '^prod-'
  - resource: host
    property: name
    type: exclude
    patterns:
      - '^standby-'
  - resource: alert
    property: severity
    patterns:
      - '^WARNING$'
      - '^CRITICAL$'
```

Need help? Contact [Datadog support][7].

[1]: https://app.datadoghq.com/account/settings/agent/latest
[2]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[3]: https://github.com/DataDog/integrations-core/blob/master/nutanix/datadog_checks/nutanix/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[6]: https://github.com/DataDog/integrations-core/blob/master/nutanix/metadata.csv
[7]: https://docs.datadoghq.com/help/
