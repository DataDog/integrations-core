# CHANGELOG - dynamo

<!-- towncrier release notes start -->

## 2.0.0 / 2026-11-25

***Changed***:

* Rename `dynamo.dynamo_component_model_load_time_seconds` to `dynamo.component.model_load_time.seconds`. ([#25326](https://github.com/DataDog/integrations-core/pull/25326))

***Added***:

* Collect the `dynamo.frontend.model.ready` and `dynamo.frontend.stage_duration.seconds` metrics. ([#26154](https://github.com/DataDog/integrations-core/pull/26154))

***Fixed***:

* Add the `collect_histograms_as_distributions` option to the configuration example and config models. ([#25590](https://github.com/DataDog/integrations-core/pull/25590))

## 1.1.0 / 2026-10-29 / Agent 7.86.0

***Added***:

* Collect the Dynamo router KV transfer latency and shared cache metrics. ([#25737](https://github.com/DataDog/integrations-core/pull/25737))

## 1.0.0 / 2026-09-30 / Agent 7.85.0

***Added***:

* Initial Release ([#24874](https://github.com/DataDog/integrations-core/pull/24874))
* Add missing inference, request-plane, runtime, and transport metrics. ([#25212](https://github.com/DataDog/integrations-core/pull/25212))
* Collect the Dynamo model load time metric. ([#25324](https://github.com/DataDog/integrations-core/pull/25324))
