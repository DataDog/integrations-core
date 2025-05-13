# CHANGELOG - Slurm

<!-- towncrier release notes start -->

## 2.0.0-beta.2 / 2025-05-13

No significant changes.

## 2.0.0-beta.1 / 2025-05-09

***Changed***:

* Change tagging logic for node and partition metrics ([#20257](https://github.com/DataDog/integrations-core/pull/20257))

***Added***:

* Collect post job efficiency data from seff output ([#20254](https://github.com/DataDog/integrations-core/pull/20254))

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
