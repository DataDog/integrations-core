# CHANGELOG - Hugging Face TGI

<!-- towncrier release notes start -->

## 2.0.0 / 2026-11-25

***Changed***:

* Bump minimum version of base check to 38.11.0. ([#26128](https://github.com/DataDog/integrations-core/pull/26128))

***Added***:

* Use the backend-neutral HTTP client, so HTTP requests and their errors no longer depend on `requests`. ([#26128](https://github.com/DataDog/integrations-core/pull/26128))

***Fixed***:

* Add the `collect_histograms_as_distributions` option to the configuration example and config models. ([#25590](https://github.com/DataDog/integrations-core/pull/25590))

## 1.5.1 / 2026-04-15 / Agent 7.79.0

***Fixed***:

* Improve descriptions ([#23047](https://github.com/DataDog/integrations-core/pull/23047))

## 1.5.0 / 2026-04-01 / Agent 7.78.0

***Added***:

* Add support for security validation in models ([#23109](https://github.com/DataDog/integrations-core/pull/23109))

## 1.4.0 / 2026-02-19 / Agent 7.77.0

***Added***:

* Add `enable_legacy_tags_normalization` option to preserve hyphens in tag values when set to false. ([#22303](https://github.com/DataDog/integrations-core/pull/22303))

## 1.3.0 / 2025-11-26 / Agent 7.74.0

***Added***:

* Bump Python to 3.13 ([#21848](https://github.com/DataDog/integrations-core/pull/21848))
* Bump minimum version of datadog-checks-base to 37.24.0 ([#21945](https://github.com/DataDog/integrations-core/pull/21945))

## 1.2.0 / 2025-10-31 / Agent 7.73.0

***Added***:

* Add logs ([#21314](https://github.com/DataDog/integrations-core/pull/21314))

***Fixed***:

* Add allowed values list on kerberos_auth field ([#20879](https://github.com/DataDog/integrations-core/pull/20879))

## 1.1.0 / 2025-10-02 / Agent 7.72.0

***Added***:

* Bump datadog-checks-base to 37.21.0 ([#21477](https://github.com/DataDog/integrations-core/pull/21477))

## 1.0.0 / 2025-09-05 / Agent 7.71.0

***Added***:

* Initial Release ([#20905](https://github.com/DataDog/integrations-core/pull/20905))
