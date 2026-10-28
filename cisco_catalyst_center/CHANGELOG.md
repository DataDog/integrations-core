# CHANGELOG - cisco_catalyst_center

<!-- towncrier release notes start -->

## 1.1.0 / 2026-10-14

***Added***:

* Add the device's tags, such as `device_name` and `site_hierarchy`, to the device throughput and uplink metrics. ([#25549](https://github.com/DataDog/integrations-core/pull/25549))

***Fixed***:

* Report device reachability from the inventory when Assurance has none, stop sending stale and placeholder values, and show collector failures in the Agent status. ([#25549](https://github.com/DataDog/integrations-core/pull/25549))

## 1.0.0 / 2026-09-30

***Added***:

* Initial Release. ([#25314](https://github.com/DataDog/integrations-core/pull/25314))
