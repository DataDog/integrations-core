# CHANGELOG - mysql

[Agent Changelog](https://github.com/DataDog/dd-agent/blob/master/CHANGELOG.md)

1.0.0/ Unreleased
==================

### Changes

* [SDK] adds mysql integration to integrations-core.

* [Improvement] Add another format for innodb writes innodb. See [dd-agent-3148](https://github.com/datadog/dd-agent/issues/3148)

* [Bugfix] Use `information_schema` in versions below 5.6.0. See [dd-agent-3196](https://github.com/datadog/dd-agent/issues/3196)
* [Bugfix] Fix version comparison operator. See [integrations-core-231](https://github.com/DataDog/integrations-core/pull/231)

