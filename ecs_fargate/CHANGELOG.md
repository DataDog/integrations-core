# CHANGELOG - ECS Fargate

## 1.2.2 / 2018-09-11

* [Fixed] Properly compute percentage of cpu used per container.

## 1.2.1 / 2018-09-04

* [Fixed] Fix key errors. See [#1959](https://github.com/DataDog/integrations-core/pull/1959).
* [Fixed] Update metadata of the cpu metrics from gauges to rates. See [#1518](https://github.com/DataDog/integrations-core/pull/1518).
* [Fixed] Add data files to the wheel package. See [#1727](https://github.com/DataDog/integrations-core/pull/1727).

## 1.2.0 / 2018-05-11

* [FIX] update the metadata collected from Version to Revision.
* [PACKAGING] add an integration tile in the app for Fargate.

## 1.1.0/ 2018-03-23

* [FEATURE] adds custom tag support to service checks.
* [FEATURE] make the fargate conf file docker friendly.

## 1.0.0/ 2018-02-28

* [FEATURE] adds ecs_fargate integration.
