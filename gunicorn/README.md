# Gunicorn Integration

![Gunicorn Dashboard][12]

## Overview

The Datadog Agent collects one main metric about Gunicorn: the number of worker processes running. It also sends one service check: whether or not Gunicorn is running.

Gunicorn itself can provide further metrics via DogStatsD, including those for:

* Total request rate
* Request rate by status code (2xx, 3xx, 4xx, 5xx)
* Request duration (average, median, max, 95th percentile, etc)
* Log message rate by log level (critical, error, warning, exception)

## Setup

### Installation

The Datadog Agent's Gunicorn check is included in the [Datadog Agent][4] package, so you don't need to install anything else on your Gunicorn servers.

The Gunicorn check requires your Gunicorn app's Python environment to have the [`setproctitle`][2] package; without it, the Datadog Agent will always report that it cannot find a `gunicorn` master process (and hence, cannot find workers, either). Install the `setproctitle` package in your app's Python environment if you want to collect the `gunicorn.workers` metric.

### Configuration

Edit the `gunicorn.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][13] to start collecting your GUNICORN [metrics](#metric-collection) and [logs](#log-collection).
See the [sample gunicorn.yaml][3] for all available configuration options.

#### Metric Collection

* Add this configuration block to your `gunicorn.d/conf.yaml` file to start gathering your [GUNICORN metrics](#metrics):

    ```yaml
    init_config:

    instances:
        # as set
        # 1) in your app's config.py (proc_name = <YOUR_APP_NAME>), OR
        # 2) via CLI (gunicorn --name <YOUR_APP_NAME> your:app)
        - proc_name: <YOUR_APP_NAME>
    ```

* [Restart the Agent][4] to begin sending Gunicorn metrics to Datadog.

#### Connect Gunicorn to DogStatsD

Since version 19.1, Gunicorn [provides an option][5] to send its metrics to a daemon that implements the StatsD protocol, such as [DogStatsD][6]. As with many Gunicorn options, you can either pass it to `gunicorn` on the CLI (`--statsd-host`) or set it in your app's configuration file (`statsd_host`). Configure your app to send metrics to DogStatsD at `"localhost:8125"`, and restart the app.

#### Log Collection

**Available for Agent >6.0**

* Collecting logs is disabled by default in the Datadog Agent, you need to enable it in `datadog.yaml`:

  ```
  logs_enabled: true
  ```

* Use the following command to configure the path of the access log file as explained in the [Gunicorn Documentation][10]: `--access-logfile <MY_FILE_PATH>`
* Use the following command to configure the path of the error log file as explained in the [Gunicorn Documentation][11]: `--error-logfile FILE, --log-file <MY_FILE_PATH>`

*  Add this configuration block to your `gunicorn.d/conf.yaml` file to start collecting your Gunicorn Logs:

  ```
  logs:
    - type: file
      path: /var/log/gunicorn/access.log
      service: <MY_SERVICE>
      source: gunicorn
      sourcecategory: http_web_access

    - type: file
      path: /var/log/gunicorn/error.log
      service: <MY_SERVICE>
      source: gunicorn
      sourcecategory: sourcecode
      log_processing_rules:
        - type: multi_line
          name: log_start_with_date
          pattern: \[\d{4}-\d{2}-\d{2}
  ```

  Change the `service` and `path` parameter values and configure them for your environment.
  See the [sample gunicorn.yaml][3] for all available configuration options.

* [Restart the Agent][4]

### Validation

[Run the Agent's `status` subcommand][7] and look for `gunicorn` under the Checks section.

If the status is not OK, see the Troubleshooting section.

Use `netstat` to verify that Gunicorn is sending _its_ metrics, too:

```
$ sudo netstat -nup | grep "127.0.0.1:8125.*ESTABLISHED"
udp        0      0 127.0.0.1:38374         127.0.0.1:8125          ESTABLISHED 15500/gunicorn: mas
```

## Data Collected

### Metrics

See [metadata.csv][8] for a list of metrics provided by this integration.

### Events
The Gunicorn check does not include any events at this time.

### Service Checks

`gunicorn.is_running`:

Returns CRITICAL if the Agent cannot find a Gunicorn master process, or if cannot find any working or idle worker processes.


## Troubleshooting

### Agent cannot find Gunicorn process
```
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

```
$ ps -ef | grep gunicorn
ubuntu   18013 16695  2 20:23 pts/0    00:00:00 /usr/bin/python /usr/bin/gunicorn --config test-app-config.py gunicorn-test:app
ubuntu   18018 18013  0 20:23 pts/0    00:00:00 /usr/bin/python /usr/bin/gunicorn --config test-app-config.py gunicorn-test:app
ubuntu   18019 18013  0 20:23 pts/0    00:00:00 /usr/bin/python /usr/bin/gunicorn --config test-app-config.py gunicorn-test:app
```

If it _is_ installed, `gunicorn` processes appear in the format the Datadog Agent expects:

```
$ ps -ef | grep gunicorn
ubuntu   18457 16695  5 20:26 pts/0    00:00:00 gunicorn: master [my_app]
ubuntu   18462 18457  0 20:26 pts/0    00:00:00 gunicorn: worker [my_app]
ubuntu   18463 18457  0 20:26 pts/0    00:00:00 gunicorn: worker [my_app]
```

## Further Reading
To get a better idea of how (or why) to integrate your Gunicorn apps with Datadog, check out our [blog post][9].


[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://pypi.python.org/pypi/setproctitle
[3]: https://github.com/DataDog/integrations-core/blob/master/gunicorn/datadog_checks/gunicorn/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[5]: https://docs.gunicorn.org/en/stable/settings.html#statsd-host
[6]: https://docs.datadoghq.com/guides/dogstatsd
[7]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[8]: https://github.com/DataDog/integrations-core/blob/master/gunicorn/metadata.csv
[9]: https://www.datadoghq.com/blog/monitor-gunicorn-performance/
[10]: https://docs.gunicorn.org/en/stable/settings.html#accesslog
[11]: https://docs.gunicorn.org/en/stable/settings.html#errorlog
[12]: https://raw.githubusercontent.com/DataDog/integrations-core/master/gunicorn/images/gunicorn-dash.png
[13]: https://docs.datadoghq.com/agent/faq/agent-configuration-files/#agent-configuration-directory
