# CHANGELOG - Docker

1.0.0/ Unreleased
==================

### Changes

#### Deprecated

The "docker" check is deprecated and will be removed in a future version of the agent. Please use the "docker_daemon" one instead

* [FEATURE] adds docker integration to integrations-core.
* [Improvement] Improved Hostname logic for containers. See [dd-agent-3116](https://github.com/datadog/dd-agent/issues/3116)
* [Improvement] Better detection and handling of incorrect PIDs. See [dd-agent-3218](https://github.com/datadog/dd-agent/issues/3218), [integrations-core-237](https://github.com/DataDog/integrations-core/pull/237)

* [Bugfix] Fix whitelist pattern matching. See [dd-agent-3048](https://github.com/datadog/dd-agent/issues/3048)
* [Bugfix] Fix image tag extraction. See [dd-agent-3172](https://github.com/datadog/dd-agent/issues/3172)

