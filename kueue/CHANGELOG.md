# CHANGELOG - Kueue

<!-- towncrier release notes start -->

## 1.0.1 / 2026-07-17

***Fixed***:

* Use the current Kueue Workload API for workload event collection, with fallback support for older clusters. ([#24563](https://github.com/DataDog/integrations-core/pull/24563))

## 1.0.0 / 2026-07-08

***Added***:

* Initial Release. ([#23908](https://github.com/DataDog/integrations-core/pull/23908))
* Add Kueue queue and resource flavor tag enrichment from the Agent tagger. ([#23999](https://github.com/DataDog/integrations-core/pull/23999))
* Add workload lifecycle event collection for Kueue Workloads. ([#24311](https://github.com/DataDog/integrations-core/pull/24311))
