# CHANGELOG - spark

1.0.0/ Unreleased
==================

### Changes

* [SDK] adds spark integration to integrations-core.

* [Improvement] No events on job status change. See [dd-agent-3194](https://github.com/datadog/dd-agent/issues/3194). This is a potentially breaking change, but it was flooding event streams with what, for most people, was useless information.

* [Bugfix] Properly report job IDs. See [dd-agent-3111](https://github.com/datadog/dd-agent/issues/3111)
* [Bugfix] Fix event source name. See [dd-agent-3193](https://github.com/datadog/dd-agent/issues/3193)

