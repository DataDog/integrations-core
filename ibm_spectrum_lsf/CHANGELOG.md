# CHANGELOG - IBM Spectrum LSF

<!-- towncrier release notes start -->

## 1.3.0 / 2026-02-19

***Added***:

* Add `enable_legacy_tags_normalization` option to preserve hyphens in tag values when set to false. ([#22303](https://github.com/DataDog/integrations-core/pull/22303))
* Add support for log collection. ([#22416](https://github.com/DataDog/integrations-core/pull/22416))
* Add support for bhist details metrics. ([#22483](https://github.com/DataDog/integrations-core/pull/22483))

***Fixed***:

* Update conf.yaml to display 'default' field defined in spec.yaml ([#21744](https://github.com/DataDog/integrations-core/pull/21744))

## 1.2.0 / 2026-01-21 / Agent 7.76.0

***Added***:

* Add project tag to in progress jobs metrics. ([#22083](https://github.com/DataDog/integrations-core/pull/22083))

## 1.1.0 / 2025-12-22 / Agent 7.75.0

***Added***:

* Support badmin perfmon metrics. ([#22024](https://github.com/DataDog/integrations-core/pull/22024))
* Support bhist metrics to monitor completed jobs. ([#22030](https://github.com/DataDog/integrations-core/pull/22030))
* Add a user tag to running job metrics. ([#22072](https://github.com/DataDog/integrations-core/pull/22072))

## 1.0.0 / 2025-11-25 / Agent 7.74.0

***Added***:

* Initial Release ([#21668](https://github.com/DataDog/integrations-core/pull/21668)) ([#21957](https://github.com/DataDog/integrations-core/pull/21957)) ([#21959](https://github.com/DataDog/integrations-core/pull/21959))