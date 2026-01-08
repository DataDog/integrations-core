# Agent Check: IBM Spectrum LSF

## Overview

This check monitors [IBM Spectrum LSF][1] using the Datadog Agent. 

This integration gives an overview of the performance of your IBM Spectrum LSF environment. It also provides detailed information about running and completed jobs, slot utilization, and queues.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][3] for guidance on applying these instructions.

### Installation

The IBM Spectrum LSF check is included in the [Datadog Agent][2] package.

Install the Datadog Agent and configure the IBM Spectrum LSF check on the management host of your cluster. This integration monitors the entire cluster.

#### On Linux

Add the `dd-agent` user as an LSF [administrator][10].

The integration runs commands such as `lsid`, `bhosts`, and `lsclusters`. In order to run these commands, the Agent needs them in its `PATH`. This is typically done by running `source $LSF_HOME/conf/profile.lsf`. However, the Datadog Agent uses upstart or systemd to orchestrate the `datadog-agent` service. You may need to add environment variables to the service configuration files at the default locations of:
- Upstart: `/etc/init/datadog-agent.conf`
- Systemd: `/lib/systemd/system/datadog-agent.service`

To get the environment variables necessary for the Agent service, locate the `<LSF_TOP_DIR>/conf/profile.lsf` file and run the following command:

```env -i bash -c "source <LSF_TOP_DIR>/conf/profile.lsf; env"```

Running this command outputs a list of environment variables necessary to run the IBM Spectrum LSF commands.

##### For Operating Systems using systemd

Add these environment variables to the file `/etc/datadog-agent/environment`; here is an example:

```
LSF_SERVERDIR=<LSF_TOP_DIR>/10.1/linux3.10-glibc2.17-x86_64/etc
LSF_ENVDIR=<LSF_TOP_DIR>/conf
LSF_BINDIR=<LSF_TOP_DIR>/10.1/linux3.10-glibc2.17-x86_64/bin
LSF_LIBDIR=<LSF_TOP_DIR>/10.1/linux3.10-glibc2.17-x86_64/lib
PATH=<LSF_TOP_DIR>/10.1/linux3.10-glibc2.17-x86_64/etc:<LSF_TOP_DIR>/10.1/linux3.10-glibc2.17-x86_64/bin:/usr/local/bin:/usr/bin:/bin:.
LD_LIBRARY_PATH=<LSF_TOP_DIR>/10.1/linux3.10-glibc2.17-x86_64/lib
```
Restart the agent.

View more information about setting environment variables for the Datadog Agent [here][11].

##### For Operating Systems using upstart

After getting the list of necessary environment variables, add them to the `/etc/init/datadog-agent.conf` file.

Example of the configuration for upstart:

```
description "Datadog Agent"

start on started networking
stop on runlevel [!2345]

respawn
respawn limit 10 5
normal exit 0

console log
env DD_LOG_TO_CONSOLE=false
env LSF_SERVERDIR=<LSF_TOP_DIR>/10.1/linux3.10-glibc2.17-x86_64/etc
env LSF_ENVDIR=<LSF_TOP_DIR>/conf
env LSF_BINDIR=<LSF_TOP_DIR>/10.1/linux3.10-glibc2.17-x86_64/bin
env LSF_LIBDIR=<LSF_TOP_DIR>/10.1/linux3.10-glibc2.17-x86_64/lib
env PATH=<LSF_TOP_DIR>/10.1/linux3.10-glibc2.17-x86_64/etc:<LSF_TOP_DIR>/10.1/linux3.10-glibc2.17-x86_64/bin:/usr/local/bin:/usr/bin:/bin:.
env LD_LIBRARY_PATH=<LSF_TOP_DIR>/10.1/linux3.10-glibc2.17-x86_64/lib

setuid dd-agent

script
  exec /opt/datadog-agent/bin/agent/agent start -p /opt/datadog-agent/run/agent.pid
end script

  rm -f /opt/datadog-agent/run/agent.pid
end script
```
Restart the agent.

Each time there is an Agent update, `/etc/init/datadog-agent.conf` is wiped and needs to be updated again.

### Configuration

1. Edit the `ibm_spectrum_lsf.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your `ibm_spectrum_lsf` performance data. See the [sample ibm_spectrum_lsf.d/conf.yaml][4] for all available configuration options.

  The IBM Spectrum LSF integration runs a series of management commands to collect data. To control which commands are run and which metrics are emitted, use the `metric_sources` configuration option. By default, data from the following commands are collected, but you can enable more optional metrics or opt out of collecting any set of metrics: `lsclusters`, `lshosts`, `bhosts`, `lsload`, `bqueues`, `bslots`, `bjobs`.

  For example, if you want to only measure GPU-specific metrics, your `metrics_sources` will look like:
  ```
    metric_sources:
      - lsload_gpu
      - bhosts_gpu
  ```

  The `badmin_perfmon` metric source collects data from the `badmin perfmon view -json` command. This collects [overall statistics][12] about the cluster. To collect these metrics, performance collection must be enabled on your server using the `badmin perfmon start <COLLECTION_INTERVAL>` command. By default, the integration runs this command automatically (and stops collection once the Agent is turned off). However, you can turn off this behavior by setting `badmin_perfmon_auto: false`.

  Since collecting these metrics can add extra load on your server, we recommend setting a higher collection interval for these metrics, or at least 60. The exact interval depends on the load and size of your cluster. View IBM Spectrum LSF's [recommendations][13] for managing high query load.

  Similarly, the `bhist` command collects information about completed jobs, which can be query-intensive, so we recommend monitoring this command with the `min_collection_interval` set to 60.

  Here is a sample configuration monitoring all available metrics:

  ```
  instances:
  - cluster_name: test-cluster
    metric_sources:
      - lsclusters
      - lshosts
      - bhosts
      - lsload
      - bqueues
      - bslots
      - bjobs
      - lsload_gpu
      - bhosts_gpu
  - cluster_name: test-cluster
    badmin_perfmon_auto: false
    metric_sources:
      - badmin_perfmon
      - bhist
    min_collection_interval: 60
  ```

2. [Restart the Agent][5].

### Validation

[Run the Agent's status subcommand][6] and look for `ibm_spectrum_lsf` under the Checks section.


## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

The IBM Spectrum LSF integration does not include any events.

### Service Checks

The IBM Spectrum LSF integration does not include any service checks.

## Troubleshooting

Use the `datadog-agent check` command to view the metrics the integration is collecting, as well as  debug logs from the check:

```sudo -u dd-agent bash -c "source /usr/share/lsf/conf/profile.lsf && datadog-agent check ibm_spectrum_lsf -l debug"```

Need help? Contact [Datadog support][9].


[1]: https://www.ibm.com/products/hpc-workload-management
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/containers/kubernetes/integrations/
[4]: https://github.com/DataDog/integrations-core/blob/master/ibm_spectrum_lsf/datadog_checks/ibm_spectrum_lsf/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/configuration/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/configuration/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/ibm_spectrum_lsf/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/ibm_spectrum_lsf/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
[10]: https://www.ibm.com/docs/en/spectrum-lsf/10.1.0?topic=cluster-adding-administrators
[11]: https://docs.datadoghq.com/agent/guide/environment-variables/#using-environment-variables-in-systemd-units
[12]: https://www.ibm.com/docs/ru/spectrum-lsf/10.1.0?topic=performance-monitor-metrics-in-real-time
[13]: https://www.ibm.com/docs/en/spectrum-lsf/10.1.0?topic=tips-maintaining-cluster-performance