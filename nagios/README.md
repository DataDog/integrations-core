# Agent Check: Nagios

## Overview

Send events from your Nagios-monitored infrastructure to Datadog for richer alerting and to help correlate Nagios events with metrics from your Datadog-monitored infrastructure.

This check watches your Nagios server's logs and sends events to Datadog for the following:

- Service flaps
- Host state changes
- Passive service checks
- Host and service downtimes

This check can also send Nagios performance data as metrics to Datadog.

**Minimum Agent version:** 6.0.0

## Setup

### Installation

The Nagios check is included in the [Datadog Agent][1] package, so you don't need to install anything else on your Nagios servers.

### Configuration

Follow the instructions below to configure this check for an Agent running on a host. For containerized environments, see the [Containerized](#containerized) section.

<!-- xxx tabs xxx -->
<!-- xxx tab "Host" xxx -->

#### Host

To configure this check for an Agent running on a host:

1. Edit the `nagios.d/conf.yaml` file in the `conf.d/` folder at the root of your [Agent's configuration directory][2]. See the [sample nagios.d/conf.yaml][3] for all available configuration options.

2. [Restart the Agent][4] to start sending Nagios events and (optionally) performance data metrics to Datadog.

**Note**: The Nagios check can potentially emit [custom metrics][5], which may impact your [billing][6].

<!-- xxz tab xxx -->
<!-- xxx tab "Containerized" xxx -->

#### Containerized

For containerized environments, see the [Autodiscovery Integration Templates][7] for guidance on applying the parameters below.

| Parameter            | Value                                        |
| -------------------- | -------------------------------------------- |
| `<INTEGRATION_NAME>` | `nagios`                                     |
| `<INIT_CONFIG>`      | blank or `{}`                                |
| `<INSTANCE_CONFIG>`  | `{"nagios_conf": "/etc/nagios3/nagios.cfg"}` |

**Note**: The containerized Agent should be able to access the `/etc/nagios3/nagios.cfg` file to enable the Datadog-Nagios integration.

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

### Validation

[Run the Agent's status subcommand][8] and look for `nagios` under the Checks section.

## Data Collected

### Metrics

With the default configuration, the Nagios check doesn't collect any metrics. But if you set `collect_host_performance_data` and/or `collect_service_performance_data` to `True`, the check watches for Nagios performance data and submits it as gauge metrics to Datadog.

### Log collection

1. Collecting logs is disabled by default in the Datadog Agent, enable it in your `datadog.yaml` file:

    ```yaml
    logs_enabled: true
    ```

2. Add this configuration block to your `nagios.d/conf.yaml` file to start collecting your Nagios logs:

    ```yaml
    logs:
      - type: file
        path: /opt/nagios/var/log/nagios.log
        source: nagios
    ```

    Change the `path` parameter value based on your environment, see `log_file` value in your nagios configuration file. See the [sample nagios.d/conf.yaml][3] for all available configuration options.

3. [Restart the Agent][4].

### Events

The check watches the Nagios events log for log lines containing these strings, emitting an event for each line:

- SERVICE FLAPPING ALERT
- ACKNOWLEDGE_SVC_PROBLEM
- SERVICE ALERT
- HOST ALERT
- ACKNOWLEDGE_HOST_PROBLEM
- SERVICE NOTIFICATION
- HOST DOWNTIME ALERT
- PROCESS_SERVICE_CHECK_RESULT
- SERVICE DOWNTIME ALERT

### Service Checks

The Nagios check does not include any service checks.

## Triggering On-Call Pages

Because Nagios events are submitted by the Datadog Agent through the `/intake` endpoint, the `oncall_team` query parameter approach is not available. Instead, configure Nagios notification commands to POST events directly to the [Datadog Events API][11], bypassing the Agent.

### How it works

Nagios sends an event to Datadog with an `@oncall-<team-handle>` mention in the event text. Datadog On-Call matches this mention and pages the on-call team.

- Events with `alert_type: error` or `alert_type: warning` paired with a shared `aggregation_key` deduplicate into a single page.
- An event with `alert_type: success` and the same `aggregation_key` auto-resolves the page.
- Events with `alert_type: info` do not trigger or resolve pages.

### Status mapping

| Nagios state | Datadog `alert_type` |
|---|---|
| `CRITICAL` / `DOWN` | `error` |
| `WARNING` | `warning` |
| `OK` / `UP` | `success` |
| `UNKNOWN` | `info` |

### Setup

**Step 1: Create the notification script**

Create `/usr/local/nagios/libexec/notify_datadog_oncall.sh`:

```bash
#!/bin/bash
set -u

DD_API_KEY="<YOUR_DATADOG_API_KEY>"
DD_SITE="datadoghq.com"  # Change to your site, e.g. datadoghq.eu, us3.datadoghq.com

NOTIF_TYPE="${1}"   # PROBLEM or RECOVERY
HOSTNAME="${2}"
SERVICEDESC="${3}"
STATE="${4}"        # CRITICAL, WARNING, OK, UNKNOWN, UP, DOWN
ONCALL_TEAM="${5}"  # Datadog On-Call team handle, e.g. "ops"
OUTPUT="${6}"

case "$STATE" in
  CRITICAL|DOWN) ALERT_TYPE="error" ;;
  WARNING)        ALERT_TYPE="warning" ;;
  OK|UP)          ALERT_TYPE="success" ;;
  *)              ALERT_TYPE="info" ;;
esac

if [ "$NOTIF_TYPE" = "RECOVERY" ]; then
  ALERT_TYPE="success"
fi

curl -s -m 15 -X POST "https://api.${DD_SITE}/api/v1/events" \
  -H "Content-Type: application/json" \
  -H "DD-API-KEY: ${DD_API_KEY}" \
  -d "{
    \"title\": \"Nagios: ${HOSTNAME} / ${SERVICEDESC} is ${STATE}\",
    \"text\": \"@oncall-${ONCALL_TEAM}\\n${OUTPUT}\",
    \"alert_type\": \"${ALERT_TYPE}\",
    \"aggregation_key\": \"${HOSTNAME}-${SERVICEDESC}\",
    \"source_type_name\": \"nagios\",
    \"host\": \"${HOSTNAME}\",
    \"tags\": [\"integration:nagios\", \"service:${SERVICEDESC}\", \"host:${HOSTNAME}\"]
  }"
```

Make the script executable:

```shell
sudo chmod 755 /usr/local/nagios/libexec/notify_datadog_oncall.sh
```

**Step 2: Define the Nagios command**

Add to `commands.cfg`:

```nagios
define command {
    command_name    notify-datadog-oncall
    command_line    /usr/local/nagios/libexec/notify_datadog_oncall.sh "$NOTIFICATIONTYPE$" "$HOSTALIAS$" "$SERVICEDESC$" "$SERVICESTATE$" "$_CONTACTONCALL_TEAM$" "$SERVICEOUTPUT$"
}
```

**Step 3: Create contacts with the On-Call team handle**

The custom variable `_oncall_team` sets the Datadog On-Call team handle per contact. Add contacts to `contacts.cfg`:

```nagios
define contact {
    contact_name                    datadog-ops
    alias                           Ops Team On-Call
    service_notification_period     24x7
    host_notification_period        24x7
    service_notification_options    w,u,c,r
    host_notification_options       d,u,r
    service_notification_commands   notify-datadog-oncall
    host_notification_commands      notify-datadog-oncall
    _oncall_team                    ops
}
```

The `_oncall_team` value (e.g., `ops`) maps to the Datadog On-Call team handle `@oncall-ops`. Set it to exactly the team handle configured in [Datadog On-Call][12].

**Step 4: Assign the contact to services or hosts**

```nagios
define service {
    use                     generic-service
    host_name               webserver-01
    service_description     HTTP_Service
    check_command           check_http
    contacts                datadog-ops
    notification_options    w,u,c,r
}
```

**Step 5: Reload Nagios**

```shell
sudo systemctl reload nagios
```

Verify pages appear under **On-Call > Pages** in Datadog.

## Troubleshooting

Need help? Contact [Datadog support][9].

## Further Reading

- [Understand your Nagios alerts with Datadog][10]

[1]: /account/settings/agent/latest
[2]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[3]: https://github.com/DataDog/integrations-core/blob/master/nagios/datadog_checks/nagios/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[5]: https://docs.datadoghq.com/developers/metrics/custom_metrics/
[6]: https://docs.datadoghq.com/account_management/billing/custom_metrics/
[7]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[8]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[9]: https://docs.datadoghq.com/help/
[10]: https://www.datadoghq.com/blog/nagios-monitoring
[11]: https://docs.datadoghq.com/api/latest/events/
[12]: https://docs.datadoghq.com/service_management/on-call/
