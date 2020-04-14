# CHANGELOG - ECS Fargate

## 2.7.0 / 2020-04-04

* [Added] Collect network metrics for ECS Fargate. See [#6216](https://github.com/DataDog/integrations-core/pull/6216).
* [Fixed] Update deprecated imports. See [#6088](https://github.com/DataDog/integrations-core/pull/6088).

## 2.6.0 / 2020-01-13

* [Fixed] Fix CPU metrics. See [#5404](https://github.com/DataDog/integrations-core/pull/5404).
* [Added] Use lazy logging format. See [#5377](https://github.com/DataDog/integrations-core/pull/5377).

## 2.5.0 / 2019-12-02

* [Added] Add auth type to RequestsWrapper. See [#4708](https://github.com/DataDog/integrations-core/pull/4708).

## 2.4.0 / 2019-10-11

* [Added] Add option to override KRB5CCNAME env var. See [#4578](https://github.com/DataDog/integrations-core/pull/4578).
* [Fixed] Fix ecs_fargate timeout. See [#4518](https://github.com/DataDog/integrations-core/pull/4518).

## 2.3.0 / 2019-08-24

* [Added] Update with proxy settings and request wrapper. See [#3477](https://github.com/DataDog/integrations-core/pull/3477).

## 2.2.2 / 2019-07-17

* [Fixed] Use tagger with container_id prefix. See [#4126](https://github.com/DataDog/integrations-core/pull/4126).

## 2.2.1 / 2019-06-28

* [Fixed] Make the kubelet and ECS fargate checks resilient to the tagger returning None. See [#4004](https://github.com/DataDog/integrations-core/pull/4004).

## 2.2.0 / 2019-05-14

* [Added] Adhere to code style. See [#3503](https://github.com/DataDog/integrations-core/pull/3503).

## 2.1.0 / 2019-02-18

* [Added] Support Python 3. See [#2885](https://github.com/DataDog/integrations-core/pull/2885).

## 2.0.0 / 2018-11-30

* [Changed] Rework tagging to be consistent with the live container view and Autodiscovery. See [#2601][1].

## 1.3.0 / 2018-09-11

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
