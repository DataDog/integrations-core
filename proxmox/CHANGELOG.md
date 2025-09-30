# CHANGELOG - Proxmox

<!-- towncrier release notes start -->

## 2.0.1 / TBD

***Fixed***:

* Handle AttributeError when Qemu Agent is not available. ([#21399](https://github.com/DataDog/integrations-core/pull/21399))

## 2.0.0 / 2025-08-07 / Agent 7.70.0

***Changed***:

* Set `empty_default_hostname` true by default. ([#20780](https://github.com/DataDog/integrations-core/pull/20780))

***Added***:

* Add failover support with Agent High Availability feature. ([#20755](https://github.com/DataDog/integrations-core/pull/20755))
* Add HA metrics. ([#20763](https://github.com/DataDog/integrations-core/pull/20763))
* Add support for sending tasks as events. ([#20849](https://github.com/DataDog/integrations-core/pull/20849))
* Add support for filtering metrics and events by resource. ([#20933](https://github.com/DataDog/integrations-core/pull/20933))

***Fixed***:

* Improve descriptions and examples in example configuration file ([#20878](https://github.com/DataDog/integrations-core/pull/20878))

## 1.0.0 / 2025-07-10 / Agent 7.69.0

***Added***:

* Initial Release ([#20428](https://github.com/DataDog/integrations-core/pull/20428))
* Bump datadog_checks_base to 37.16.0 ([#20711](https://github.com/DataDog/integrations-core/pull/20711))
