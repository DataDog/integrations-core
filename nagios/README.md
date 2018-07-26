# Agent Check: Nagios

## Overview

Send events from your Nagios-monitored infrastructure to Datadog for richer alerting and to help correlate Nagios events with metrics from your Datadog-monitored infrastructure.

This check watches your Nagios server's logs and sends events to your Datadog event stream: track service flaps, host state changes, passive service checks, host and service downtimes, and more. This check can also send Nagios performance data as metrics to Datadog.

## Setup
### Installation

The Nagios check is included in the [Datadog Agent][1] package, so you don't need to install anything else on your Nagios servers.

### Configuration

Edit the `nagios.d/conf.yaml` file in the `conf.d/` folder at the root of your [Agent's configuration directory][7]. See the [sample nagios.d/conf.yaml][2] for all available configuration options:

```
init_config:
  check_freq: 15 # default is 15

instances:
  - nagios_conf: /etc/nagios3/nagios.cfg   # or wherever your main nagios conf is
    collect_events: True                   # default is True
    passive_checks_events: True            # default is False
    collect_host_performance_data: True    # default is False
    collect_service_performance_data: True # default is False
```

The Agent reads the main Nagios configuration file to get the locations of the Nagios log files it should watch.

This check also works with Icinga, a popular fork of Nagios. If you use Icinga, just set `nagios_conf` to the location of your Icinga configuration file.

[Restart the Agent][3] to start sending Nagios events and (optionally) performance data metrics to Datadog.

### Validation

[Run the Agent's `status` subcommand][4] and look for `nagios` under the Checks section.

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
The Nagios check does not include any service checks at this time.

## Troubleshooting
Need help? Contact [Datadog Support][5].

## Further Reading

* [Understand your Nagios alerts with Datadog][6]


[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://github.com/DataDog/integrations-core/blob/master/nagios/datadog_checks/nagios/data/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[4]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[5]: https://docs.datadoghq.com/help/
[6]: https://www.datadoghq.com/blog/nagios-monitoring/
[7]: https://docs.datadoghq.com/agent/faq/agent-configuration-files/#agent-configuration-directory
