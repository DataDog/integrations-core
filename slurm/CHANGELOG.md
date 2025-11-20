# CHANGELOG - Slurm

<!-- towncrier release notes start -->

## 2.1.0 / 2025-10-02 / Agent 7.72.0

***Added***:

* Bump Python to 3.13 ([#21161](https://github.com/DataDog/integrations-core/pull/21161))
* Bump datadog-checks-base to 37.21.0 ([#21477](https://github.com/DataDog/integrations-core/pull/21477))

## 2.0.2 / 2025-07-10 / Agent 7.69.0

***Fixed***:

* Update configuration spec to better match the code for the collect_scontrol_stats param ([#20541](https://github.com/DataDog/integrations-core/pull/20541))

## 2.0.1 / 2025-06-12 / Agent 7.68.0

***Fixed***:

* Fix collection of metrics from sinfo on `collection_level` 2 ([#20456](https://github.com/DataDog/integrations-core/pull/20456))

## 2.0.0 / 2025-05-15 / Agent 7.67.0

***Changed***:

* Change tagging logic for node and partition metrics ([#20257](https://github.com/DataDog/integrations-core/pull/20257))
* Bump datadog-checks-base to 37.10.1 ([#20271](https://github.com/DataDog/integrations-core/pull/20271))

***Added***:

* Collect post job efficiency data from seff output ([#20255](https://github.com/DataDog/integrations-core/pull/20255))

***Fixed***:

* Changed metric to `slurm.sdiag.backfill.last_cycle_seconds_ago` for consistency ([#20256](https://github.com/DataDog/integrations-core/pull/20256))

## 1.2.0 / 2025-05-08

***Added***:

* Add metric to track seconds since last backfill cycle from sdiag ([#20165](https://github.com/DataDog/integrations-core/pull/20165))
* Add slurm_partition_name to job metrics ([#20170](https://github.com/DataDog/integrations-core/pull/20170))
* Add slurm node memory metrics ([#20225](https://github.com/DataDog/integrations-core/pull/20225))
* Added metrics for disk reads for sacct metrics set ([#20231](https://github.com/DataDog/integrations-core/pull/20231))

***Fixed***:

* Fix cpu count for sinfo node by using the correct query parameter ([#20167](https://github.com/DataDog/integrations-core/pull/20167))
* Fix Slurm partition nodes metrics and `slurm_cluster_name` tag ([#20169](https://github.com/DataDog/integrations-core/pull/20169))
* Fix averss, maxrss, avecpu from sacct metric set that weren't getting parsed ([#20230](https://github.com/DataDog/integrations-core/pull/20230))

## 1.1.0 / 2025-03-19 / Agent 7.65.0

***Added***:

* Add metric collection from scontrol for worker nodes ([#19715](https://github.com/DataDog/integrations-core/pull/19715))

## 1.0.3 / 2024-12-06 / Agent 7.61.0

***Fixed***:

* Add all user query param to the different queries ([#19182](https://github.com/DataDog/integrations-core/pull/19182))

## 1.0.2 / 2024-11-28

***Fixed***:

* Bump base package dependency to get fixed pyyaml. ([#19156](https://github.com/DataDog/integrations-core/pull/19156))

## 1.0.1 / 2024-11-25 / Agent 7.60.0

***Fixed***:

* Fix issue in which the sacct params kept growing with each iteration ([#19117](https://github.com/DataDog/integrations-core/pull/19117))

## 1.0.0 / 2024-11-06

***Added***:

* Initial Release ([#18893](https://github.com/DataDog/integrations-core/pull/18893))
