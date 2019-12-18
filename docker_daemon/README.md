# Docker Daemon Integration

**Note**: The Docker Daemon check is still maintained but only works with **Agent v5**.

<div class="alert alert-warning">
<b>To use the Docker integration with Agent v6 consult the <a href="#agent-v6">Agent v6 section</a> below.</b>
</div>

![Docker default dashboard][1]

## Overview

Configure this Agent check to get metrics from the Docker_daemon service in real time to:

* Visualize and monitor Docker_daemon states.
* Be notified about Docker_daemon failovers and events.

## Setup
### Installation

To collect Docker metrics about all your containers, run **one** Datadog Agent on every host. There are two ways to run the Agent: directly on each host, or within a [docker-dd-agent container][2] (recommended).

For either option, your hosts need cgroup memory management enabled for the Docker check to succeed. See the [docker-dd-agent repository][3] for how to enable it.

#### Host Installation

1. Ensure Docker is running on the host.
2. Install the Agent as described in [the Agent installation instructions][4] for your host OS.
3. Enable [the Docker integration tile in the application][5].
4. Add the Agent user to the Docker group: `usermod -a -G docker dd-agent`
5. Create a `docker_daemon.yaml` file by copying [the example file in the agent conf.d directory][6]. If you have a standard install of Docker on your host, there shouldn't be anything you need to change to get the integration to work.
6. To enable other integrations, use `docker ps` to identify the ports used by the corresponding applications.
    ![Docker ps command][7]

#### Container Installation

1. Ensure Docker is running on the host.
2. As per [the Docker container installation instructions][8], run:

        docker run -d --name dd-agent \
          -v /var/run/docker.sock:/var/run/docker.sock:ro \
          -v /proc/:/host/proc/:ro \
          -v /sys/fs/cgroup/:/host/sys/fs/cgroup:ro \
          -e API_KEY={YOUR_DD_API_KEY} \
          datadog/docker-dd-agent:latest

In the command above, you are able to pass your API key to the Datadog Agent using Docker's `-e` environment variable flag. Other variables include:

| **Variable**                                                                                      | **Description**                                                                                                                                                                                                                  |
|---------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| API_KEY                                                                                           | Sets your Datadog API key.                                                                                                                                                                                                       |
| DD_HOSTNAME                                                                                       | Sets the hostname in the Agent container's `datadog.conf` file. If this variable is not set, the Agent container defaults to using the `Name` field (as reported by the `docker info` command) as the Agent container hostname.  |
| DD_URL                                                                                            | Sets the Datadog intake server URL where the Agent sends data. This is useful when [using the Agent as a proxy][9].                                                                                                              |
| LOG_LEVEL                                                                                         | Sets logging verbosity (CRITICAL, ERROR, WARNING, INFO, DEBUG). For example, `-e LOG_LEVEL=DEBUG` sets logging to debug mode.                                                                                                    |
| TAGS                                                                                              | Sets host tags as a comma delimited string. Both simple tags and key-value tags are available, for example: `-e TAGS="simple-tag, tag-key:tag-value"`.                                                                           |
| EC2_TAGS                                                                                          | Enabling this feature allows the agent to query and capture custom tags set using the EC2 API during startup. To enable, use `-e EC2_TAGS=yes`. Note that this feature requires an IAM role associated with the instance.        |
| NON_LOCAL_TRAFFIC                                                                                 | Enabling this feature allows StatsD reporting from any external IP. To enable, use `-e NON_LOCAL_TRAFFIC=yes`. This is used to report metrics from other containers or systems. See [network configuration][10] for more details. |
| PROXY_HOST, PROXY_PORT, PROXY_USER, PROXY_PASSWORD                                                | Sets proxy configuration details. **Note**: `PROXY_PASSWORD` is required for passing in an authentication password and cannot be renamed. For more information, see the [Agent proxy documentation][11].                                                                                                                                  |
| SD_BACKEND, SD_CONFIG_BACKEND, SD_BACKEND_HOST, SD_BACKEND_PORT, SD_TEMPLATE_DIR, SD_CONSUL_TOKEN | Enables and configures Autodiscovery. For more information, see the [Autodiscovery guide][12].                                                                                                                                   |

**Note**: Add `--restart=unless-stopped` if you want your agent to be resistant to restarts.

#### Running the agent container on Amazon Linux

To run the Datadog Agent container on Amazon Linux, make this change to the `cgroup` volume mount location:

```
docker run -d --name dd-agent \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  -v /proc/:/host/proc/:ro \
  -v /cgroup/:/host/sys/fs/cgroup:ro \
  -e API_KEY={YOUR API KEY} \
  datadog/docker-dd-agent:latest
```

#### Alpine Linux based container

The standard Docker image is based on Debian Linux, but as of Datadog Agent v5.7, there is an [Alpine Linux][13] based image. The Alpine Linux image is considerably smaller in size than the traditional Debian-based image. It also inherits Alpine's security-oriented design.

To use the Alpine Linux image, append `-alpine` to the version tag. For example:

```
docker run -d --name dd-agent \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  -v /proc/:/host/proc/:ro \
  -v /sys/fs/cgroup/:/host/sys/fs/cgroup:ro \
  -e API_KEY={YOUR API KEY} \
  datadog/docker-dd-agent:latest-alpine
```

#### Image versioning
Starting with version 5.5.0 of the Datadog Agent, the Docker image follows a new versioning pattern. This allows us to release changes to the Docker image of the Datadog Agent but with the same version of the Agent.

The Docker image version has the following pattern: **X.Y.Z** where **X** is the major version of the Docker Image, **Y** is the minor version, **Z** represents the Agent version.

For example, the first version of the Docker image that bundles the Datadog Agent 5.5.0 is: `10.0.550`

#### Custom containers and additional information

For more information about building custom Docker containers with the Datadog Agent, the Alpine Linux based image, versioning, and more, reference the [docker-dd-agent project on Github][2].

### Validation

[Run the Agent's status subcommand][14] and look for `docker_daemon` under the Checks section.

## Agent v6

The latest Docker check is named `docker` and written in Go to take advantage of the new internal architecture. Starting from version 6.0, the Agent won't load the `docker_daemon` check anymore, even if it is still available and maintained for Agent v5. All features are ported on version >6.0 , except the following deprecations:

  * The `url`, `api_version` and `tags*` options are deprecated, direct use of the [standard Docker environment variables][15] is encouraged.
  * The `ecs_tags`, `performance_tags` and `container_tags` options are deprecated. Every relevant tag is now collected by default.
  * The `collect_container_count` option to enable the `docker.container.count` metric is not supported. `docker.containers.running` and `.stopped` should be used.

Some options have moved from `docker_daemon.yaml` to the main `datadog.yaml`:

  * `collect_labels_as_tags` has been renamed `docker_labels_as_tags` and now supports high cardinality tags, see the details in `datadog.yaml.example`.
  * `exclude` and `include` lists have been renamed `ac_include` and `ac_exclude`. To make filtering consistent across all components of the Agent, filtering on arbitrary tags has been dropped. The only supported filtering tags are `image` (image name) and `name` (container name). Regexp filtering is still available, see `datadog.yaml.example` for examples.
  * The `docker_root` option has been split in two options `container_cgroup_root` and `container_proc_root`.
  * `exclude_pause_container` has been added to exclude paused containers on Kubernetes and Openshift (defaults to true). This avoids removing them from the exclude list by error.

Additional changes:

  * The `TAGS` environment variable was renamed to `DD_TAGS`.
  * The Docker Hub repository has changed from [datadog/docker-dd-agent][16] to [datadog/agent][17].

The [`import`][18] command converts the old `docker_daemon.yaml` to the new `docker.yaml`. The command also moves needed settings from `docker_daemon.yaml` to `datadog.yaml`.

## Data Collected
### Metrics
See [metadata.csv][19] for a list of metrics provided by this integration.

### Events
The Docker integration produces the following events:

* Delete Image
* Die
* Error
* Fail
* Kill
* Out of memory (oom)
* Pause
* Restart container
* Restart Daemon
* Update

### Service Checks

**docker.service_up**:
Returns `CRITICAL` if the Agent is unable to collect the list of containers from the Docker daemon, otherwise returns `OK`.

**docker.container_health**:
This Service Check is only available for Agent v5. It returns `CRITICAL` if a container is unhealthy, `UNKNOWN` if the health is unknown, and `OK` otherwise.

**docker.exit**:
Returns `CRITICAL` if a container exited with a non-zero exit code, otherwise returns `OK`.

**Note**: To use `docker.exit`, add `collect_exit_code: true` in your [Docker YAML file][20] and restart the Agent.

## Troubleshooting
Need help? Contact [Datadog support][21].

## Further Reading
### Knowledge Base

* [Compose and the Datadog Agent][22]
* [DogStatsD and Docker][23]

### Datadog Blog

Learn more about how to monitor Docker performance metrics with [our series of posts][24]. We detail the challenges when monitoring Docker, its key performance metrics, how to collect them, and lastly how the largest TV and radio outlet in the U.S. monitors Docker using Datadog.

We've also written several other in-depth blog posts to help you get the most out of Datadog and Docker:

* [How to Monitor Docker Resource Metrics][25]
* [How to Collect Docker Metrics][26]
* [8 Surprising Facts about Real Docker Adoption][27]
* [Monitor Docker on AWS ECS][28]
* [Dockerize Datadog][29]
* [Monitor Docker with Datadog][30]


[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/docker_daemon/images/docker.png
[2]: https://github.com/DataDog/docker-dd-agent
[3]: https://github.com/DataDog/docker-dd-agent#cgroups
[4]: https://app.datadoghq.com/account/settings#agent
[5]: https://app.datadoghq.com/account/settings#integrations/docker
[6]: https://github.com/DataDog/integrations-core/blob/master/docker_daemon/datadog_checks/docker_daemon/data/conf.yaml.example
[7]: https://raw.githubusercontent.com/DataDog/integrations-core/master/docker_daemon/images/integrations-docker-dockerps.png
[8]: https://app.datadoghq.com/account/settings#agent/docker
[9]: https://github.com/DataDog/dd-agent/wiki/Proxy-Configuration#using-the-agent-as-a-proxy
[10]: https://github.com/DataDog/dd-agent/wiki/Network-Traffic-and-Proxy-Configuration
[11]: https://github.com/DataDog/dd-agent/wiki/Proxy-Configuration#using-a-web-proxy-as-proxy
[12]: https://docs.datadoghq.com/agent/autodiscovery
[13]: https://alpinelinux.org
[14]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[15]: https://docs.docker.com/engine/reference/commandline/cli/#environment-variables
[16]: https://hub.docker.com/r/datadog/docker-dd-agent
[17]: https://hub.docker.com/r/datadog/agent
[18]: https://docs.datadoghq.com/agent/#cli
[19]: https://github.com/DataDog/integrations-core/blob/master/docker_daemon/metadata.csv
[20]: https://github.com/DataDog/integrations-core/blob/master/docker_daemon/datadog_checks/docker_daemon/data/conf.yaml.example#L124
[21]: https://docs.datadoghq.com/help
[22]: https://docs.datadoghq.com/integrations/faq/compose-and-the-datadog-agent
[23]: https://docs.datadoghq.com/integrations/faq/dogstatsd-and-docker
[24]: https://www.datadoghq.com/blog/the-docker-monitoring-problem
[25]: https://www.datadoghq.com/blog/how-to-monitor-docker-resource-metrics
[26]: https://www.datadoghq.com/blog/how-to-collect-docker-metrics
[27]: https://www.datadoghq.com/docker-adoption
[28]: https://www.datadoghq.com/blog/monitor-docker-on-aws-ecs
[29]: https://www.datadoghq.com/blog/docker-performance-datadog
[30]: https://www.datadoghq.com/blog/monitor-docker-datadog
