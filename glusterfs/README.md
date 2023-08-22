# Agent Check: GlusterFS

## Overview

This check monitors [Red Hat Gluster Storage][1] cluster health, volume, and brick status through the Datadog Agent. 
This GlusterFS integration is compatible with both Red Hat vendored and open-source versions of GlusterFS.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][2] for guidance on applying these instructions.

### Installation

The GlusterFS check is included in the [Datadog Agent][3] package.
No additional installation is needed on your server.

### Configuration

1. Edit the `glusterfs.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your GlusterFS performance data. See the [sample glusterfs.d/conf.yaml][4] for all available configuration options.
   
   ```yaml
   init_config:

    ## @param gstatus_path - string - optional - default: /opt/datadog-agent/embedded/sbin/gstatus
    ## Path to the gstatus command.
    ##
    ## A version of the gstatus is shipped with the Agent binary.
    ## If you are using a source install, specify the location of gstatus.
    #
    # gstatus_path: /opt/datadog-agent/embedded/sbin/gstatus

    instances:
      -
        ## @param min_collection_interval - number - optional - default: 60
        ## The GlusterFS integration collects cluster-wide metrics which can put additional workload on the server.
        ## Increase the collection interval to reduce the frequency.
        ##
        ## This changes the collection interval of the check. For more information, see:
        ## https://docs.datadoghq.com/developers/write_agent_check/#collection-interval
        #
        min_collection_interval: 60
   ```
    
   **NOTE**: By default, [`gstatus`][5] internally calls the `gluster` command which requires running as superuser. Add a line like the following to your `sudoers` file:
 
   ```text
    dd-agent ALL=(ALL) NOPASSWD:/path/to/your/gstatus
   ```

   If your GlusterFS environment does not require root, set `use_sudo` configuration option to `false`.

2. [Restart the Agent][6].

#### Log collection


1. Collecting logs is disabled by default in the Datadog Agent, enable it in your `datadog.yaml` file:

    ```yaml
    logs_enabled: true
    ```

2. Edit this configuration block in your `glusterfs.d/conf.yaml` file to start collecting your GlusterFS logs:

    ```yaml
    logs:
      - type: file
        path: /var/log/glusterfs/glusterd.log
        source: glusterfs
      - type: file
        path: /var/log/glusterfs/cli.log
        source: glusterfs
    ```

  Change the `path` parameter value based on your environment. See the [sample conf.yaml][4] for all available configuration options.

  3. [Restart the Agent][6].

For information on configuring the Agent for log collection in Kubernetes environments, see [Kubernetes Log Collection][7].

### Validation

[Run the Agent's status subcommand][8] and look for `glusterfs` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][9] for a list of metrics provided by this check.

### Events

GlusterFS does not include any events.

### Service Checks

See [service_checks.json][10] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][11].


[1]: https://www.redhat.com/en/technologies/storage/gluster
[2]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[3]: https://app.datadoghq.com/account/settings/agent/latest
[4]: https://github.com/DataDog/integrations-core/blob/master/glusterfs/datadog_checks/glusterfs/data/conf.yaml.example
[5]: https://github.com/gluster/gstatus#install
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[7]: https://docs.datadoghq.com/agent/kubernetes/log/
[8]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[9]: https://github.com/DataDog/integrations-core/blob/master/glusterfs/metadata.csv
[10]: https://github.com/DataDog/integrations-core/blob/master/glusterfs/assets/service_checks.json
[11]: https://docs.datadoghq.com/help/
