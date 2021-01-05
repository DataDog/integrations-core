# Agent Check: GlusterFS

## Overview

This check monitors [Red Hat Gluster Storage][1] cluster health, volume, and brick status through the Datadog Agent. 
This GlusterFS integration is compatible with both Red Hat vendored and open-source versions of GlusterFS.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][2] for guidance on applying these instructions.

### Installation

The GlusterFS check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

### Configuration

1. Edit the `glusterfs.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your GlusterFS performance data. See the [sample glusterfs.d/conf.yaml][3] for all available configuration options.
   
   ```yaml
   init_config:

    ## @param gstatus_path - string - optional - default: /path/to/gstatus
    ## Path to the gstatus command.
    ##
    ## A version of the gstatus is shipped with the Agent binary.
    ## If you are using a source install, specify the location of gstatus.
    #
    # gstatus_path: /path/to/gstatus

    instances:
      -
        ## @param use_sudo - boolean - optional - default: false
        ## GlusterFS requires sudo. Please be sure to add the following line to your sudoers file:
        ##
        ## dd-agent ALL=(ALL) NOPASSWD:/opt/datadog-agent/embedded/sbin/gstatus
        ##
        ## Enable the option for the check to run with sudo.
        #
        use_sudo: true
   ```
   
   If you enable `use_sudo`, add a line like the following to your `sudoers` file:
   ```text
    dd-agent ALL=(ALL) NOPASSWD:/path/to/your/gstatus
   ```
   
   [`gstatus`][8] internally calls the `gluster` command which requires running as superuser.
    
2. [Restart the Agent][4].

### Validation

[Run the Agent's status subcommand][5] and look for `glusterfs` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][6] for a list of metrics provided by this check.

### Service Checks

**glusterfs.brick.health**:<br>
Returns `CRITICAL` if the sub volume is 'degraded'. Returns `OK` if 'up'.

**glusterfs.volume.health**:<br>
Returns `CRITICAL` if the volume is 'degraded'. Returns `OK` if 'up'.

**glusterfs.cluster.health**:<br>
Returns `CRITICAL` if the cluster is 'degraded'. Returns `OK` otherwise.

### Events

GlusterFS does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][7].

[1]: https://www.redhat.com/en/technologies/storage/gluster
[2]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[3]: https://github.com/DataDog/integrations-core/blob/master/glusterfs/datadog_checks/glusterfs/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[6]: https://github.com/DataDog/integrations-core/blob/master/glusterfs/metadata.csv
[7]: https://docs.datadoghq.com/help/
[8]: https://github.com/gluster/gstatus#install