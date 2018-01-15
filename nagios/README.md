# Agent Check: Nagios

## Overview

Send events from your Nagios-monitored infrastructure to Datadog for richer alerting and to help correlate Nagios events with metrics from your Datadog-monitored infrastructure.

This check watches your Nagios server's logs and sends events to your Datadog event stream: track service flaps, host state changes, passive service checks, host and service downtimes, and more. The check can also send Nagios Perfdata as metrics to Datadog.

* Watches your Nagios server's logs and sends events to your Datadog event stream. It emits eve

The check emits events for service flaps, host state changes, passive service checks, host and service downtimes, and more. It can also send Nagios Perfdata to Datadog as metrics.

## Setup
### Installation

The Nagios check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your Nagios servers.  

If you need the newest version of the Nagios check, install the `dd-check-nagios` package; this package's check overrides the one packaged with the Agent. See the [integrations-core](https://github.com/DataDog/integrations-core#installing-the-integrations) repository for more details.

### Configuration

Create a file `nagios.yaml` in the Agent's `conf.d` directory. See the [sample nagios.yaml](https://github.com/DataDog/integrations-core/blob/master/nagios/conf.yaml.example) for all available configuration options:

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

[Restart the Agent](https://docs.datadoghq.com/agent/faq/start-stop-restart-the-datadog-agent) to start sending Nagios events and (optionally) perfdata metrics to Datadog.

### Validation

[Run the Agent's `info` subcommand](https://docs.datadoghq.com/agent/faq/agent-status-and-information/) and look for `nagios` under the Checks section:

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
Need help? Contact [Datadog Support](http://docs.datadoghq.com/help/).

## Further Reading

* [Understand your Nagios alerts with Datadog](https://www.datadoghq.com/blog/nagios-monitoring/)