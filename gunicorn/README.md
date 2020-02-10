# Gunicorn Integration

![Gunicorn Dashboard][1]

## Overview

The Datadog Agent collects one main metric about Gunicorn: the number of worker processes running. It also sends one service check: whether or not Gunicorn is running.

Gunicorn itself can provide further metrics via DogStatsD, including those for:

- Total request rate
- Request rate by status code (2xx, 3xx, 4xx, 5xx)
- Request duration (average, median, max, 95th percentile, etc.)
- Log message rate by log level (critical, error, warning, exception)

## Setup

### Installation

The Datadog Agent's Gunicorn check is included in the [Datadog Agent][3] package, so you don't need to install anything else on your Gunicorn servers.

The Gunicorn check requires your Gunicorn app's Python environment to have the [`setproctitle`][4] package; without it, the Datadog Agent will always report that it cannot find a `gunicorn` master process (and hence, cannot find workers, either). Install the `setproctitle` package in your app's Python environment if you want to collect the `gunicorn.workers` metric.

### Configuration

Edit the `gunicorn.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][5] to start collecting your Gunicorn [metrics](#metric-collection) and [logs](#log-collection).
See the [sample gunicorn.yaml][6] for all available configuration options.

#### Metric collection

1. Add this configuration block to your `gunicorn.d/conf.yaml` file to start gathering your [Gunicorn metrics](#metrics):

```yaml
init_config:

instances:
  # as set
  # 1) in your app's config.py (proc_name = <YOUR_APP_NAME>), OR
  # 2) via CLI (gunicorn --name <YOUR_APP_NAME> your:app)
  - proc_name: <YOUR_APP_NAME>
```

2. [Restart the Agent][3] to begin sending Gunicorn metrics to Datadog.

#### Connect Gunicorn to DogStatsD

Since version 19.1, Gunicorn [provides an option][7] to send its metrics to a daemon that implements the StatsD protocol, such as [DogStatsD][8]. As with many Gunicorn options, you can either pass it to `gunicorn` on the CLI (`--statsd-host`) or set it in your app's configuration file (`statsd_host`). Configure your app to send metrics to DogStatsD at `"localhost:8125"`, and restart the app.

**Note**: If you are using this option, do **not** add the metric collection configuration block to `gunicorn.d/conf.yaml`. That is, if you are connecting Gunicorn to DogStatsD, ignore the directions in the [Metric Collection](#metric-collection) section of this document.

#### Log collection

_Available for Agent versions >6.0_

1. Collecting logs is disabled by default in the Datadog Agent, enable it in your `datadog.yaml` file:

   ```yaml
   logs_enabled: true
   ```

2. Use the following command to configure the path of the access log file as explained in the [Gunicorn Documentation][9]: `--access-logfile <MY_FILE_PATH>`

3. Use the following command to configure the path of the error log file as explained in the [Gunicorn Documentation][10]: `--error-logfile FILE, --log-file <MY_FILE_PATH>`

4. Add this configuration block to your `gunicorn.d/conf.yaml` file to start collecting your Gunicorn logs:

   ```yaml
   logs:
     - type: file
       path: /var/log/gunicorn/access.log
       service: "<MY_SERVICE>"
       source: gunicorn
       sourcecategory: http_web_access

     - type: file
       path: /var/log/gunicorn/error.log
       service: "<MY_SERVICE>"
       source: gunicorn
       sourcecategory: sourcecode
       log_processing_rules:
         - type: multi_line
           name: log_start_with_date
           pattern: \[\d{4}-\d{2}-\d{2}
   ```

    Change the `service` and `path` parameter values and configure them for your environment. See the [sample gunicorn.yaml][6] for all available configuration options.

5. [Restart the Agent][3].

### Validation

[Run the Agent's status subcommand][11] and look for `gunicorn` under the Checks section.

If the status is not `OK`, see the Troubleshooting section.

Use `netstat` to verify that Gunicorn is sending _its_ metrics, too:

```text
$ sudo netstat -nup | grep "127.0.0.1:8125.*ESTABLISHED"
udp        0      0 127.0.0.1:38374         127.0.0.1:8125          ESTABLISHED 15500/gunicorn: mas
```

## Data Collected

### Metrics

See [metadata.csv][12] for a list of metrics provided by this integration.

### Events

The Gunicorn check does not include any events.

### Service Checks

**gunicorn.is_running**:<br>
Returns `CRITICAL` if the Agent cannot find a Gunicorn master process, or any working or idle worker processes, otherwise returns `OK`.

## Troubleshooting

### Agent cannot find Gunicorn process

```shell
  Checks
  ======

    gunicorn (5.12.1)
    -----------------
      - instance #0 [ERROR]: 'Found no master process with name: gunicorn: master [my_web_app]'
      - Collected 0 metrics, 0 events & 1 service check
      - Dependencies:
          - psutil: 4.4.1
```

Either Gunicorn really isn't running, or your app's Python environment doesn't have the `setproctitle` package installed.

If `setproctitle` is not installed, Gunicorn appears in the process table like so:

```text
$ ps -ef | grep gunicorn
ubuntu   18013 16695  2 20:23 pts/0    00:00:00 /usr/bin/python /usr/bin/gunicorn --config test-app-config.py gunicorn-test:app
ubuntu   18018 18013  0 20:23 pts/0    00:00:00 /usr/bin/python /usr/bin/gunicorn --config test-app-config.py gunicorn-test:app
ubuntu   18019 18013  0 20:23 pts/0    00:00:00 /usr/bin/python /usr/bin/gunicorn --config test-app-config.py gunicorn-test:app
```

If it _is_ installed, `gunicorn` processes appear in the format the Datadog Agent expects:

```text
$ ps -ef | grep gunicorn
ubuntu   18457 16695  5 20:26 pts/0    00:00:00 gunicorn: master [my_app]
ubuntu   18462 18457  0 20:26 pts/0    00:00:00 gunicorn: worker [my_app]
ubuntu   18463 18457  0 20:26 pts/0    00:00:00 gunicorn: worker [my_app]
```

## Further Reading

- [Monitor Gunicorn performance with Datadog][13]

[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/gunicorn/images/gunicorn-dash.png
[3]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[4]: https://pypi.python.org/pypi/setproctitle
[5]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[6]: https://github.com/DataDog/integrations-core/blob/master/gunicorn/datadog_checks/gunicorn/data/conf.yaml.example
[7]: https://docs.gunicorn.org/en/stable/settings.html#statsd-host
[8]: https://docs.datadoghq.com/guides/dogstatsd
[9]: https://docs.gunicorn.org/en/stable/settings.html#accesslog
[10]: https://docs.gunicorn.org/en/stable/settings.html#errorlog
[11]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[12]: https://github.com/DataDog/integrations-core/blob/master/gunicorn/metadata.csv
[13]: https://www.datadoghq.com/blog/monitor-gunicorn-performance
