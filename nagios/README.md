# Agent Check: Nagios

## Overview

Send events from your Nagios-monitored infrastructure to Datadog for richer alerting and to help correlate Nagios events with metrics from your Datadog-monitored infrastructure.

This check watches your Nagios server's logs and sends events to your Datadog event stream: track service flaps, host state changes, passive service checks, host and service downtimes, and more. The check can also send Nagios Perfdata as metrics to Datadog.

* Watches your Nagios server's logs and sends events to your Datadog event stream. It emits eve

The check emits events for service flaps, host state changes, passive service checks, host and service downtimes, and more. It can also send Nagios Perfdata to Datadog as metrics.

## Setup
### Installation

The Nagios check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your Nagios servers. If you need the newest version of the check, install the `dd-check-nagios` package.

### Configuration

Create a file `nagios.yaml` in the Agent's `conf.d` directory:

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

The Agent reads the main nagios configuration file to get the locations of the nagios log files it should watch.

This check also works with Icinga, the popular fork of Nagios. If you use Icinga, just set `nagios_conf` to the location of your Icinga configuration file.

Restart the Agent to start sending Nagios events and (optionally) perfdata metrics to Datadog.

### Validation

Run the Agent's `info` subcommand and look for `nagios` under the Checks section:

```
  Checks
  ======
    [...]

    nagios
    -------
      - instance #0 [OK]
      - Collected 10 metrics, 15 events & 0 service checks

    [...]
```

## Compatibility

The nagios check is compatible with all major platforms.

## Data Collected
### Metrics

With a default configuration, the Nagios check doesn't collect any metrics. But if you set `collect_host_performance_data` and/or `collect_service_performance_data` to `True`, the check watches for perfdata and sumbits it as gauge metrics to Datadog.

### Events

The check watches the Nagios events log for log lines containing these string, emitting an event for each such line:

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
The Nagios check does not include any service check at this time.

## Troubleshooting

If you have any questions about Datadog or a use case our [Docs](https://docs.datadoghq.com/) didn’t mention, we’d love to help! Here’s how you can reach out to us:

### Visit the Knowledge Base

Learn more about what you can do in Datadog on the [Support Knowledge Base](https://datadog.zendesk.com/agent/).

### Web Support

Messages in the [event stream](https://app.datadoghq.com/event/stream) containing **@support-datadog** will reach our Support Team. This is a convenient channel for referencing graph snapshots or a particular event. In addition, we have a livechat service available during the day (EST) from any page within the app.

### By Email

You can also contact our Support Team via email at [support@datadoghq.com](mailto:support@datadoghq.com).

### Over Slack

Reach out to our team and other Datadog users on [Slack](http://chat.datadoghq.com/).

## Further Reading
### Blog Article
To get a better idea of how to understand your Nagios alerts with Datadog, check out our [series of blog posts](https://www.datadoghq.com/blog/nagios-monitoring/) about it.
