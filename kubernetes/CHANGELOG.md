# CHANGELOG - kubernetes

[Agent Changelog](https://github.com/DataDog/dd-agent/blob/master/CHANGELOG.md)

1.0.0/ Unreleased
==================

### Changes

* [SDK] adds kubernetes integration to integrations-core.

* [Feature] Allow kublet host to be specified from environment. See [dd-agent-3051](https://github.com/DataDog/dd-agent/issues/3051) (Thanks [@stonith][])
* [Feature] Add image_name and image_tag to container metrics. See [dd-agent-2990](https://github.com/DataDog/dd-agent/issues/2990) (Thanks [@tarvip][])

* [Improvement] handle multiple namespaces. See [dd-agent-3028](https://github.com/DataDog/dd-agent/issues/3028)
* [Improvement] Support api server auth with a cert. See [dd-agent-3145](https://github.com/DataDog/dd-agent/issues/3145)
* [Improvement] Allow configurable custom certs. See [dd-agent-3160](https://github.com/DataDog/dd-agent/issues/3160)
* [Improvement] Add support for kublet auth when the read-only port is disabled. See [dd-agent-3142](https://github.com/DataDog/dd-agent/issues/3142), [integrations-core-242](https://github.com/DataDog/integrations-core/pull/242)
* [Improvement] Updates the path to grab certs. See [dd-agent-3210](https://github.com/DataDog/dd-agent/issues/3210). (Thanks [@dturn][])

* [Bugfix] Only use annotations for service discovery once per pod. See [dd-agent-2901](https://github.com/DataDog/dd-agent/issues/2901) (Thanks [@mikekap][])
* [Bugfix] Fix tags param in example config file. See [dd-agent-3044](https://github.com/DataDog/dd-agent/issues/3044)
* [Bugfix] Remove potentially sensitive information from logs. See [integrations-core-254](https://github.com/DataDog/integrations-core/pull/254)


[@dturn]: https://github.com/dturn
[@mikekap]: https://github.com/mikekap
[@stonith]: https://github.com/stonith
[@tarvip]: https://github.com/tarvip
