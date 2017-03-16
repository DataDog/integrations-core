# CHANGELOG - http_check

1.0.0/ Unreleased
==================

### Changes

* [SDK] adds http_check integration to integrations-core.

* [Feature] Mark the Service Check as down if result matches content match option. See [dd-agent-3069](https://github.com/DataDog/dd-agent/issues/3069)

* [Improvement] Adds optiont to disable default http headers. See [integrations-core-182](https://github.com/DataDog/integrations-core/pull/182). (Thanks [@eredjar][])
* [Improvement] Remove noisy debug logging. See [integrations-core-267](https://github.com/DataDog/integrations-core/pull/267)

* [Bugfix] Fix content match for non ascii characters. See [dd-agent-3100](https://github.com/DataDog/dd-agent/issues/3100)


[@eredjar]: https://github.com/eredjar
