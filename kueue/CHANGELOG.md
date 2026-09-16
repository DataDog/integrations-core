# CHANGELOG - Kueue

<!-- towncrier release notes start -->

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
