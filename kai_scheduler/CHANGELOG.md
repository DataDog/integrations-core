# CHANGELOG - KAI Scheduler

<!-- towncrier release notes start -->

## 1.1.0 / 2026-11-25

***Added***:

* Add KAI PodGroup life cycle events: `kai.podgroup.created`, `kai.podgroup.pending`, `kai.podgroup.admitted`, and `kai.podgroup.evicted`. ([#25939](https://github.com/DataDog/integrations-core/pull/25939))
* Add the `job_scheduler`, `job_scheduler_queue`, and `job_scheduler_workload` tags to KAI PodGroup events. ([#25992](https://github.com/DataDog/integrations-core/pull/25992))
* Define the fields of `kube_config_dict` and make it configurable through Fleet Automation, with its credentials handled as secrets. ([#26160](https://github.com/DataDog/integrations-core/pull/26160))

***Fixed***:

* Add the `collect_histograms_as_distributions` option to the configuration example and config models. ([#25590](https://github.com/DataDog/integrations-core/pull/25590))

## 1.0.0 / 2026-10-29 / Agent 7.86.0

***Added***:

* Add the KAI Scheduler integration. ([#25747](https://github.com/DataDog/integrations-core/pull/25747))
