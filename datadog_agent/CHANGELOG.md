# CHANGELOG - Datadog Agent

<!-- towncrier release notes start -->

## 1.0.0 / 2026-11-25

***Changed***:

* Bump minimum version of base check to 38.11.0. ([#26128](https://github.com/DataDog/integrations-core/pull/26128))

***Added***:

* Initial Release. ([#25795](https://github.com/DataDog/integrations-core/pull/25795))
* Use the backend-neutral HTTP client, so HTTP requests and their errors no longer depend on `requests`. ([#26128](https://github.com/DataDog/integrations-core/pull/26128))

***Fixed***:

* Add the `collect_histograms_as_distributions` option to the configuration example and config models. ([#25590](https://github.com/DataDog/integrations-core/pull/25590))
