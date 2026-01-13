# CHANGELOG - Lustre

<!-- towncrier release notes start -->

## 1.3.0 / 2025-11-26 / Agent 7.74.0

***Added***:

* Bump minimum version of datadog-checks-base to 37.24.0 ([#21945](https://github.com/DataDog/integrations-core/pull/21945))

## 1.2.1 / 2025-11-19 / Agent 7.73.0

***Fixed***:

* Fix device discovery for older versions of Lustre (<2.15.5) ([#21901](https://github.com/DataDog/integrations-core/pull/21901))

## 1.2.0 / 2025-10-31

***Security***:

* Switch from using shell=True to shell=False in subprocess command ([#21690](https://github.com/DataDog/integrations-core/pull/21690))

***Added***:

* Add histogram bucket metrics for `lustre.jobstats.read_bytes` and `lustre.jobstats.write_bytes` ([#21589](https://github.com/DataDog/integrations-core/pull/21589))

## 1.1.0 / 2025-10-02 / Agent 7.72.0

***Added***:

* Bump Python to 3.13 ([#21161](https://github.com/DataDog/integrations-core/pull/21161))
* Add `filesystem`, `jobid_var` and `jobid_name` tags ([#21270](https://github.com/DataDog/integrations-core/pull/21270))
* Bump datadog-checks-base to 37.21.0 ([#21477](https://github.com/DataDog/integrations-core/pull/21477))

## 1.0.1 / 2025-08-07 / Agent 7.70.0

***Fixed***:

* Improve error handling implementation with enhanced debug logs and refined logic ([#20727](https://github.com/DataDog/integrations-core/pull/20727))
* Fix typo in OSS parameter ([#20857](https://github.com/DataDog/integrations-core/pull/20857))

## 1.0.0 / 2025-07-10 / Agent 7.69.0

***Added***:

* Initial Release ([#20146](https://github.com/DataDog/integrations-core/pull/20146))
