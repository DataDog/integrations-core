# Agent Check: Slurm

## Overview

This check monitors [Slurm][1] through the Datadog Agent. 

Slurm (Simple Linux Utility for Resource Management) is an open-source workload manager used to schedule and manage jobs on large-scale compute clusters. It allocates resources, monitors job queues, and ensures efficient execution of parallel and batch jobs in high-performance computing environments.

The check gathers metrics from `slurmctld` by executing and parsing the output of several command-line binaries, including [`sinfo`][8], [`squeue`][9], [`sacct`][10], [`sdiag`][11], and [`sshare`][12]. These commands provide detailed information on resource availability, job queues, accounting, diagnostics, and share usage in a Slurm-managed cluster.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. Since the Agent requires direct access to the various Slurm binaries, monitoring Slurm in containerized environments is not recommended.

**Note**: This check was tested on Slurm version 21.08.0.

### Installation

The Slurm check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

### Configuration

1. Ensure that the dd-agent user has execute permissions on the relevant command binaries and the necessary permissions to access the directories where these binaries are located.

2. Edit the `slurm.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your Slurm data. See the [sample slurm.d/conf.yaml][3] for all available configuration options.

```yaml
init_config:

    ## Customize this part if the binaries are not located in the /usr/bin/ directory
    ## @param slurm_binaries_dir - string - optional - default: /usr/bin/
    ## The directory in which all the Slurm binaries are located. These are mainly:
    ## sinfo, sacct, sdiag, sshare and sdiag.

    slurm_binaries_dir: /usr/bin/

instances:

  -
    ## Configure these parameters to select which data the integration collects.
    ## @param collect_sinfo_stats - boolean - optional - default: true
    ## Whether or not to collect statistics from the sinfo command.
    #
    collect_sinfo_stats: true

    ## @param collect_sdiag_stats - boolean - optional - default: true
    ## Whether or not to collect statistics from the sdiag command.
    #
    collect_sdiag_stats: true

    ## @param collect_squeue_stats - boolean - optional - default: true
    ## Whether or not to collect statistics from the squeue command.
    #
    collect_squeue_stats: true

    ## @param collect_sacct_stats - boolean - optional - default: true
    ## Whether or not to collect statistics from the sacct command.
    #
    collect_sacct_stats: true

    ## @param collect_sshare_stats - boolean - optional - default: true
    ## Whether or not to collect statistics from the sshare command.
    #
    collect_sshare_stats: true

    ## @param collect_gpu_stats - boolean - optional - default: false
    ## Whether or not to collect GPU statistics when Slurm is configured to use GPUs using sinfo.
    #
    collect_gpu_stats: true

    ## @param sinfo_collection_level - integer - optional - default: 1
    ## The level of detail to collect from the sinfo command. The default is 'basic'. Available options are 1, 2 and
    ## 3. Level 1 collects data only for partitions. Level 2 collects data from individual nodes. Level 3 
    ## collects data from from individual nodes as well but is more verbose and includes data such as CPU and 
    ## memory usage as reported from the OS, as well as additional tags.
    #
    sinfo_collection_level: 1
```

3. [Restart the Agent][4].

### Validation

[Run the Agent's status subcommand][5] and look for `slurm` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][6] for a list of metrics provided by this integration.

### Events

The Slurm integration does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][7].


[1]: https://slurm.schedmd.com/overview.html
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://github.com/DataDog/integrations-core/blob/master/slurm/datadog_checks/slurm/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[6]: https://github.com/DataDog/integrations-core/blob/master/slurm/metadata.csv
[7]: https://docs.datadoghq.com/help/
[8]: https://slurm.schedmd.com/sinfo.html
[9]: https://slurm.schedmd.com/squeue.html
[10]: https://slurm.schedmd.com/sacct.html
[11]: https://slurm.schedmd.com/sdiag.html
[12]: https://slurm.schedmd.com/sshare.html
