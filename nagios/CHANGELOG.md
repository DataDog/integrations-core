# CHANGELOG - nagios

## 1.2.0 / 2018-12-19

* [Added] Add instance level tags to Nagios Events. See [#2778][1].

## 1.1.3 / 2018-11-30

* [Fixed] Use raw string literals when \ is present. See [#2465][2].

## 1.1.2 / 2018-10-12

* [Fixed] Fix empty event issue with Agent 6. See [#2348][3].

## 1.1.1 / 2018-09-04

* [Fixed] Add Agent 6 compatibility by not sending timestamps for gauge metrics (Agent 6 only). See [#1822][4].
* [Fixed] Add data files to the wheel package. See [#1727][5].

## 1.1.0 / 2018-03-23

* [FEATURE] add custom tag support.

## 1.0.0 / 2017-03-22

* [FEATURE] adds nagios integration.
[1]: https://github.com/DataDog/integrations-core/pull/2778
[2]: https://github.com/DataDog/integrations-core/pull/2465
[3]: https://github.com/DataDog/integrations-core/pull/2348
[4]: https://github.com/DataDog/integrations-core/pull/1822
[5]: https://github.com/DataDog/integrations-core/pull/1727
