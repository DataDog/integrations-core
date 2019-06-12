# Agent Check: Nagios

## Overview

Send events from your Nagios-monitored infrastructure to Datadog for richer alerting and to help correlate Nagios events with metrics from your Datadog-monitored infrastructure.

This check watches your Nagios server's logs and sends events to your Datadog event stream: track service flaps, host state changes, passive service checks, host and service downtimes, and more. This check can also send Nagios performance data as metrics to Datadog.

## Setup
### Installation

The Nagios check is included in the [Datadog Agent][1] package, so you don't need to install anything else on your Nagios servers.

### Configuration

Edit the `nagios.d/conf.yaml` file in the `conf.d/` folder at the root of your [Agent's configuration directory][2]. See the [sample nagios.d/conf.yaml][3] for all available configuration options.

[Restart the Agent][4] to start sending Nagios events and (optionally) performance data metrics to Datadog.

#### Metrics collection
The Nagios check can potentially emit [custom metrics][13], which may impact your [billing][14].

### Validation

[Run the Agent's status subcommand][5] and look for `nagios` under the Checks section.

## Data Collected
### Metrics

With the default configuration, the Nagios check doesn't collect any metrics. But if you set `collect_host_performance_data` and/or `collect_service_performance_data` to `True`, the check watches for Nagios performance data and submits it as gauge metrics to Datadog.

### Events

The check watches the Nagios events log for log lines containing these strings, emitting an event for each line:

- SERVICE FLAPPING ALERT
- ACKNOWLEDGE_SVC_PROBLEM
- SERVICE ALERT
- HOST ALERT
- PASSIVE SERVICE CHECK
- CURRENT SERVICE STATE
- ACKNOWLEDGE_HOST_PROBLEM
- CURRENT HOST STATE
- SERVICE NOTIFICATION
- HOST DOWNTIME ALERT
- PROCESS_SERVICE_CHECK_RESULT
- SERVICE DOWNTIME ALERT

### Service Checks
The Nagios check does not include any service checks.

## Troubleshooting
Need help? Contact [Datadog support][6].

## Further Reading

* [Understand your Nagios alerts with Datadog][7]


[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/?tab=agentv6#agent-configuration-directory
[3]: https://github.com/DataDog/integrations-core/blob/master/nagios/datadog_checks/nagios/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#start-stop-and-restart-the-agent
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#agent-status-and-information
[6]: https://docs.datadoghq.com/help
[7]: https://www.datadoghq.com/blog/nagios-monitoring
[8]: https://docs.datadoghq.com/developers/metrics/custom_metrics
[9]: https://docs.datadoghq.com/account_management/billing/custom_metrics/
