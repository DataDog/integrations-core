# CHANGELOG - docker_daemon

1.0.0/ Unreleased
==================

### Changes

* [SDK] adds docker_daemon integration to integrations-core.

* [Feature] Add a number of new metrics for container and volume counts. See [dd-agent-2740](https://github.com/DataDog/dd-agent/issues/2740), [dd-agent-3077](https://github.com/DataDog/dd-agent/issues/3077). (Thanks [@parkr][])
* [Feature] Tag container metrics with swarm if available. See [dd-agent-3182](https://github.com/DataDog/dd-agent/issues/3182), [dd-agent-3243](https://github.com/DataDog/dd-agent/issues/3243)

* [Improvement] Make Docker Healthcheck a Service Check. See [dd-agent-2859](https://github.com/DataDog/dd-agent/issues/2859)

* [Bugfix] Report as many cgroup metrics as possible. See [dd-agent-3134](https://github.com/DataDog/dd-agent/issues/3134)


[@parkr]: https://github.com/parkr
