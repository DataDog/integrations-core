# CHANGELOG - ECS Fargate

## 2.1.0 / 2019-02-18

* [Added] Finish Python 3 Support. See [#2958](https://github.com/DataDog/integrations-core/pull/2958).
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
