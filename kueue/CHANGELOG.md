# CHANGELOG - Kueue

<!-- towncrier release notes start -->

## 3.1.0 / 2026-11-25

***Added***:

* Add the `job_scheduler`, `job_scheduler_queue`, and `job_scheduler_workload` tags to Kueue Workload events. ([#25992](https://github.com/DataDog/integrations-core/pull/25992))
* Define the fields of `kube_config_dict` and make it configurable through Fleet Automation, with its credentials handled as secrets. ([#26160](https://github.com/DataDog/integrations-core/pull/26160))

***Fixed***:

* Add the `collect_histograms_as_distributions` option to the configuration example and config models. ([#25590](https://github.com/DataDog/integrations-core/pull/25590))

## 3.0.0 / 2026-10-29 / Agent 7.86.0

***Changed***:

* Stop copying check instance tags onto Kueue workload events. ([#25787](https://github.com/DataDog/integrations-core/pull/25787))

***Added***:

* Support HA Kueue: drop follower samples by default, add the `collect_follower_metrics` option, and submit Workload events only from the leader replica. ([#25541](https://github.com/DataDog/integrations-core/pull/25541))
* Add a per-workload event index so Kueue workload events that share a timestamp can be ordered. ([#25762](https://github.com/DataDog/integrations-core/pull/25762))

## 2.0.0 / 2026-09-17 / Agent 7.84.0

***Changed***:

* Enable collection of histogram buckets as distribution metrics by default. ([#25196](https://github.com/DataDog/integrations-core/pull/25196))

***Added***:

* Add events for Kueue Workloads that cannot reserve quota. ([#25236](https://github.com/DataDog/integrations-core/pull/25236))

## 1.1.0 / 2026-08-05 / Agent 7.83.0

***Added***:

* Add support for Kueue log collection.
  Collect the cumulative ``kueue.finished_workloads.count`` counter. ([#24700](https://github.com/DataDog/integrations-core/pull/24700))

***Fixed***:

* Correct metric metadata so counters, histograms, and gauges resolve in dashboards, and remove a metric that Kueue does not emit.
  Fix the ``kueue_preempted_by`` workload event tag value, which appended the preempting Job UID to the Workload UID.
  Stop emitting the ``kueue_preempted_by`` workload event tag on evictions caused by resource flavor migration rather than preemption. ([#24700](https://github.com/DataDog/integrations-core/pull/24700))
* Preserve resource tags for Kueue metrics mapped to ``other``. ([#24760](https://github.com/DataDog/integrations-core/pull/24760))

## 1.0.1 / 2026-07-17 / Agent 7.82.0

***Fixed***:

* Use the current Kueue Workload API for workload event collection, with fallback support for older clusters. ([#24563](https://github.com/DataDog/integrations-core/pull/24563))

## 1.0.0 / 2026-07-08

***Added***:

* Initial Release. ([#23908](https://github.com/DataDog/integrations-core/pull/23908))
* Add Kueue queue and resource flavor tag enrichment from the Agent tagger. ([#23999](https://github.com/DataDog/integrations-core/pull/23999))
* Add workload lifecycle event collection for Kueue Workloads. ([#24311](https://github.com/DataDog/integrations-core/pull/24311))
