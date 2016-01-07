# Overview
Get metrics from Docker in real time to:

* Visualize your containers' performance.
* Correlate the performance of containers with the applications running inside.

There are three ways to setup the Docker integration: install the agent on the host, on a single priviledged container, and on each individual container.

**Note:** docker_daemon replaces the older docker integration going forward.

# Installation

## Host Installation

1. Ensure Docker is running on the host.
2. Install the agent as described in [the agent installation instructions](https://app.datadoghq.com/account/settings#agent) for your host OS.
3. Enable [the Docker integration tile in the application](https://app.datadoghq.com/account/settings#integrations/docker).
4. Add the agent user to the docker group: ```usermod -a -G docker dd-agent```
5. Create  **docker_daemon.yaml** by copying the example file in the agent conf.d directory. If you have a standard install of Docker on your host, there shouldn't be anything you need to change to get the integration to work.
6. To enable other integrations, use ```docker ps``` to identify the ports used by the corresponding applications.
    ![](/static/images/integrations-docker-dockerps.png)

## Single Container Installation

1. Ensure Docker is running on the host.
2. Install the Docker container as described in [the docker container installation instructions](https://app.datadoghq.com/account/settings#agent/docker).

### Environment variables

A few parameters can be changed with environment variables.

* **TAGS** set host tags. Add -e TAGS="simple-tag-0,tag-key-1:tag-value-1" to use [simple-tag-0, tag-key-1:tag-value-1] as host tags.
* **LOG_LEVEL** set logging verbosity (CRITICAL, ERROR, WARNING, INFO, DEBUG). Add -e LOG_LEVEL=DEBUG to turn logs to debug mode.
* **PROXY_HOST**, **PROXY_PORT**, **PROXY_USER** and **PROXY_PASSWORD** set the proxy configuration.
* **DD_URL** set the Datadog intake server to send Agent data to (used when using an agent as a proxy )

## Each Container Installation

1. Ensure Docker is running on the host.
2. Add a RUN command to the Dockerfile as listed in the agent installation instructions in the app for the OS used in the container. For instance, if the container is based on an Ubuntu image, add something similar to the following command:

        RUN DD_API_KEY={YOUR_API_KEY} bash -c "$(curl -L https://raw.githubuser..._agent.sh)"

    NOTE: Always refer to the instructions in the app for the latest version of the install command.


# Validation

1. Restart the agent.
2. Execute the info command and verify that the integration check has passed. The output of the command should contain a section similar to the following:

        Checks
        ======

          [...]
          docker_daemon
          -------------
            - instance #0 [OK]
            - Collected 50 metrics, 0 events & 2 service checks

3. In the application on the Infrastructure List, you should see the host with the blue docker pill next to it indicating that the app is receiving the data correctly.

# Troubleshooting

Single container install not working on Amazon Linux
: Try using the following command to run the container:

      docker run -d --name dd-agent -h `hostname` \
        -v /var/run/docker.sock:/var/run/docker.sock \
        -v /proc/:/host/proc/:ro \
        -v /cgroup/:/host/sys/fs/cgroup:ro -e \
        API_KEY={your_api_key_here} \
        datadog/docker-dd-agent

What is the format of the version number?
: As per Agent 5.5.0. The docker image is following a new versioning pattern to allow us to release changes to the Docker image of the Datadog Agent but with the same version of the Agent.
: The Docker image version will have the following pattern: **X.Y.Z** where **X** is the major version of the Docker Image, **Y** is the minor version, **Z** will represent the Agent version.
: e.g. the first version of the Docker image that will bundle the Datadog Agent 5.5.0 will be: ```10.0.550```


For more information about customizing the Docker container, refer to the [Readme in the GitHub Repo](https://github.com/DataDog/docker-dd-agent).

We've written several in depth blog posts on Datadog and Docker::

* [The Docker Monitoring Problem](https://www.datadoghq.com/docker-adoption/)
* [How to Monitor Docker Resource Metrics](https://www.datadoghq.com/blog/how-to-monitor-docker-resource-metrics/)
* [How to Collect Docker Metrics](https://www.datadoghq.com/blog/how-to-collect-docker-metrics/)
* [8 Surprising Facts about Real Docker Adoption](https://www.datadoghq.com/docker-adoption/)
* [Monitor Docker on AWS ECS](https://www.datadoghq.com/blog/monitor-docker-on-aws-ecs/)
* [Dockerize Datadog](https://www.datadoghq.com/2014/06/docker-ize-datadog/)
* [Monitor Docker with Datadog](https://www.datadoghq.com/2014/06/monitor-docker-datadog/)
