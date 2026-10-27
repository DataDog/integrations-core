# CHANGELOG - Infiniband

<!-- towncrier release notes start -->

## 2.0.0 / 2026-10-01

***Changed***:

* The InfiniBand check now requires GPU monitoring to be enabled (gpu.enabled in datadog.yaml). Instances are skipped when it is not enabled. ([#25277](https://github.com/DataDog/integrations-core/pull/25277))
* Report `infiniband.port_rcv_data` and `infiniband.port_xmit_data` in bytes rather than the raw sysfs value, which IBTA defines in units of 4-byte words, so the values for these two metrics increase fourfold and any monitor or dashboard using a static threshold on them must be rescaled; the `port_state` and `port_phys_state` tag values are now normalized, which changes the emitted value for any state whose kernel name contains a space or angle brackets. ([#25278](https://github.com/DataDog/integrations-core/pull/25278))

***Added***:

* Collect the `req_transport_retries_exceeded` and `req_rnr_retries_exceeded` hardware counters, and log at debug level any configured counter name that does not match a file in sysfs. ([#25278](https://github.com/DataDog/integrations-core/pull/25278))

***Fixed***:

* Correct the `exclude_counters` and `exclude_hw_counters` configuration examples, which were swapped, replace an `additional_counters` example that named a counter absent from every kernel tree, repair the physical-state monitor's tag filter and group-by so it can match the emitted tags, and drop two permanently empty dashboard widgets whose signal is already covered by adjacent panels. ([#25278](https://github.com/DataDog/integrations-core/pull/25278))

## 1.7.0 / 2026-06-09 / Agent 7.81.0

***Added***:

* Add port rate, link layer, network device, and device identity metadata to InfiniBand metrics. ([#23901](https://github.com/DataDog/integrations-core/pull/23901))

## 1.6.0 / 2026-04-01 / Agent 7.78.0

***Added***:

* Add support for security validation in models ([#23109](https://github.com/DataDog/integrations-core/pull/23109))

## 1.5.0 / 2026-02-19 / Agent 7.77.0

***Added***:

* Add `enable_legacy_tags_normalization` option to preserve hyphens in tag values when set to false. ([#22303](https://github.com/DataDog/integrations-core/pull/22303))

## 1.4.0 / 2025-12-22 / Agent 7.75.0

***Added***:

* Skip errors when reading unimplemented metrics ([#22158](https://github.com/DataDog/integrations-core/pull/22158))

## 1.3.0 / 2025-11-26 / Agent 7.74.0

***Added***:

* Add EFA retransmits and error state metrics ([#21802](https://github.com/DataDog/integrations-core/pull/21802))
* Bump minimum version of datadog-checks-base to 37.24.0 ([#21945](https://github.com/DataDog/integrations-core/pull/21945))

## 1.2.0 / 2025-10-02 / Agent 7.72.0

***Added***:

* Bump Python to 3.13 ([#21161](https://github.com/DataDog/integrations-core/pull/21161))
* Bump datadog-checks-base to 37.21.0 ([#21477](https://github.com/DataDog/integrations-core/pull/21477))

## 1.1.0 / 2025-04-17 / Agent 7.66.0

***Added***:

* Add state and phys_state metrics ([#20070](https://github.com/DataDog/integrations-core/pull/20070))

## 1.0.0 / 2025-03-19 / Agent 7.65.0

***Added***:

* Initial Release ([#19748](https://github.com/DataDog/integrations-core/pull/19748))
