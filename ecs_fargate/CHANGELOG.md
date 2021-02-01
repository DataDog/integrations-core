# CHANGELOG - ECS Fargate

## 2.12.0 / 2021-01-25

* [Added] Add new default for newly autodiscovered checks. See [#8177](https://github.com/DataDog/integrations-core/pull/8177).
* [Fixed] Correct default template usage. See [#8233](https://github.com/DataDog/integrations-core/pull/8233).

## 2.11.0 / 2020-12-11 / Agent 7.25.0

* [Added] Amazon fargate config specs. See [#8003](https://github.com/DataDog/integrations-core/pull/8003).

## 2.10.0 / 2020-08-10 / Agent 7.22.0

* [Added] Support include/exclude containers in ECS Fargate. See [#7165](https://github.com/DataDog/integrations-core/pull/7165).
* [Fixed] DOCS-838 Template wording. See [#7038](https://github.com/DataDog/integrations-core/pull/7038).
* [Fixed] Update ntlm_domain example. See [#7118](https://github.com/DataDog/integrations-core/pull/7118).

## 2.9.0 / 2020-06-29 / Agent 7.21.0

* [Added] Add note about warning concurrency. See [#6967](https://github.com/DataDog/integrations-core/pull/6967).

## 2.8.0 / 2020-05-17 / Agent 7.20.0

* [Added] Allow optional dependency installation for all checks. See [#6589](https://github.com/DataDog/integrations-core/pull/6589).

## 2.7.0 / 2020-04-04 / Agent 7.19.0

* [Added] Collect network metrics for ECS Fargate. See [#6216](https://github.com/DataDog/integrations-core/pull/6216).
* [Fixed] Update deprecated imports. See [#6088](https://github.com/DataDog/integrations-core/pull/6088).

## 2.6.0 / 2020-01-13 / Agent 7.17.0

* [Fixed] Fix CPU metrics. See [#5404](https://github.com/DataDog/integrations-core/pull/5404).
* [Added] Use lazy logging format. See [#5377](https://github.com/DataDog/integrations-core/pull/5377).

## 2.5.0 / 2019-12-02 / Agent 7.16.0

* [Added] Add auth type to RequestsWrapper. See [#4708](https://github.com/DataDog/integrations-core/pull/4708).

## 2.4.0 / 2019-10-11 / Agent 6.15.0

* [Added] Add option to override KRB5CCNAME env var. See [#4578](https://github.com/DataDog/integrations-core/pull/4578).
* [Fixed] Fix ecs_fargate timeout. See [#4518](https://github.com/DataDog/integrations-core/pull/4518).

## 2.3.0 / 2019-08-24 / Agent 6.14.0

* [Added] Update with proxy settings and request wrapper. See [#3477](https://github.com/DataDog/integrations-core/pull/3477).

## 2.2.2 / 2019-07-17 / Agent 6.13.0

* [Fixed] Use tagger with container_id prefix. See [#4126](https://github.com/DataDog/integrations-core/pull/4126).

## 2.2.1 / 2019-06-28 / Agent 6.12.1

* [Fixed] Make the kubelet and ECS fargate checks resilient to the tagger returning None. See [#4004](https://github.com/DataDog/integrations-core/pull/4004).

## 2.2.0 / 2019-05-14 / Agent 6.12.0

* [Added] Adhere to code style. See [#3503](https://github.com/DataDog/integrations-core/pull/3503).

## 2.1.0 / 2019-02-18 / Agent 6.10.0

* [Added] Support Python 3. See [#2885](https://github.com/DataDog/integrations-core/pull/2885).

## 2.0.0 / 2018-11-30 / Agent 6.8.0

* [Changed] Rework tagging to be consistent with the live container view and Autodiscovery. See [#2601][1].

## 1.3.0 / 2018-09-11 / Agent 6.5.0

* [Added] Add cpu percent metric and fix container stopped behaviour. See [#2206][2].

## 1.2.1 / 2018-09-04

* [Fixed] Fix key errors. See [#1959][3].
* [Fixed] Update metadata of the cpu metrics from gauges to rates. See [#1518][4].
* [Fixed] Add data files to the wheel package. See [#1727][5].

## 1.2.0 / 2018-05-11

* [FIX] update the metadata collected from Version to Revision.
* [PACKAGING] add an integration tile in the app for Fargate.

## 1.1.0/ 2018-03-23

* [FEATURE] adds custom tag support to service checks.
* [FEATURE] make the fargate conf file docker friendly.

## 1.0.0/ 2018-02-28

* [FEATURE] adds ecs_fargate integration.
[1]: https://github.com/DataDog/integrations-core/pull/2601
[2]: https://github.com/DataDog/integrations-core/pull/2206
[3]: https://github.com/DataDog/integrations-core/pull/1959
[4]: https://github.com/DataDog/integrations-core/pull/1518
[5]: https://github.com/DataDog/integrations-core/pull/1727
