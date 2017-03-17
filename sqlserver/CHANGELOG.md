# CHANGELOG - sqlserver

[Agent Changelog](https://github.com/DataDog/dd-agent/blob/master/CHANGELOG.md)

1.0.0/ Unreleased
==================

### Changes

* [SDK] adds sqlserver integration to integrations-core.

* [Feature] Allow connection through pyodbc as well as adodbapi. See [integrations-core-259](https://github.com/DataDog/integrations-core/pull/259), [integrations-core-264](https://github.com/DataDog/integrations-core/pull/264), [omnibus-software-129](https://github.com/DataDog/omnibus-software/pull/129), [dd-agent-omnibus-154](https://github.com/DataDog/dd-agent-omnibus/pull/154)

* [Bugfix] Stops passwords from leaking into logs. See [dd-agent-3053](https://github.com/datadog/dd-agent/issues/3053)
* [Bugfix] Collect metric list if SQLServer is not up during check init. See [dd-agent-3067](https://github.com/datadog/dd-agent/issues/3067)
