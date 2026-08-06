# CHANGELOG - KrakenD

<!-- towncrier release notes start -->

## 2.0.0 / 2026-08-05

***Changed***:

* Apply the default label renames even when an instance overrides `rename_labels`. ([#24754](https://github.com/DataDog/integrations-core/pull/24754))

***Added***:

* Add process autodiscovery support. ([#24238](https://github.com/DataDog/integrations-core/pull/24238))
* Collect the `krakend.api.http_client.response_size` metric, which reports backend response sizes from the `Content-Length` header. ([#24752](https://github.com/DataDog/integrations-core/pull/24752))

***Fixed***:

* Migrate the metrics mapping to file-based YAML loading. ([#22751](https://github.com/DataDog/integrations-core/pull/22751))
* Require `datadog-checks-base>=37.41.0` since config discovery relies on it. ([#24545](https://github.com/DataDog/integrations-core/pull/24545))

## 1.5.0 / 2026-07-08

***Added***:

* Add configuration discovery support. ([#24126](https://github.com/DataDog/integrations-core/pull/24126))

## 1.4.1 / 2026-04-15 / Agent 7.79.0

***Fixed***:

* Improve descriptions ([#23047](https://github.com/DataDog/integrations-core/pull/23047))

## 1.4.0 / 2026-04-01 / Agent 7.78.1

***Added***:

* Add support for security validation in models ([#23109](https://github.com/DataDog/integrations-core/pull/23109))

## 1.3.0 / 2026-02-19 / Agent 7.77.0

***Added***:

* Add `enable_legacy_tags_normalization` option to preserve hyphens in tag values when set to false. ([#22303](https://github.com/DataDog/integrations-core/pull/22303))

## 1.2.0 / 2025-11-26 / Agent 7.74.0

***Added***:

* Bump minimum version of datadog-checks-base to 37.24.0 ([#21945](https://github.com/DataDog/integrations-core/pull/21945))

## 1.1.1 / 2025-10-31 / Agent 7.73.0

***Fixed***:

* Add allowed values list on kerberos_auth field ([#20879](https://github.com/DataDog/integrations-core/pull/20879))

## 1.1.0 / 2025-10-02 / Agent 7.72.0

***Added***:

* Bump Python to 3.13 ([#21161](https://github.com/DataDog/integrations-core/pull/21161))
* Bump datadog-checks-base to 37.21.0 ([#21477](https://github.com/DataDog/integrations-core/pull/21477))

## 1.0.1 / 2025-08-07 / Agent 7.70.0

***Fixed***:

* Improve descriptions and examples in example configuration file ([#20878](https://github.com/DataDog/integrations-core/pull/20878))

## 1.0.0 / 2025-07-10 / Agent 7.69.0

***Changed***:

* Bump datadog_checks_base to 37.16.0 ([#20711](https://github.com/DataDog/integrations-core/pull/20711))

***Added***:

* Initial release ([#20668](https://github.com/DataDog/integrations-core/pull/20668))
