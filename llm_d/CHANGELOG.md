# CHANGELOG - llm-d

<!-- towncrier release notes start -->

## 1.0.0 / 2026-11-25

***Added***:

* Add the llm-d integration. ([#26003](https://github.com/DataDog/integrations-core/pull/26003))
* Collect the llm-d v1.0.0 EPP prefix-cache prediction and request and response processing latency metrics. ([#26044](https://github.com/DataDog/integrations-core/pull/26044))
* Add new Openmetrics config parameters to the llm_d integration ([#26059](https://github.com/DataDog/integrations-core/pull/26059))

***Fixed***:

* Stop deriving the `inference_pool` tag from EPP pool labels; report them as `llm_d_pool` instead. ([#26044](https://github.com/DataDog/integrations-core/pull/26044))
