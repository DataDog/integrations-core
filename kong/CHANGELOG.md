# CHANGELOG - kong

## 1.8.0 / 2020-04-04

* [Added] Add option to set SNI hostname via the `Host` header for RequestsWrapper. See [#5833](https://github.com/DataDog/integrations-core/pull/5833).
* [Fixed] Update deprecated imports. See [#6088](https://github.com/DataDog/integrations-core/pull/6088).
* [Fixed] Remove logs sourcecategory. See [#6121](https://github.com/DataDog/integrations-core/pull/6121).

## 1.7.1 / 2020-02-25

* [Fixed] Update datadog_checks_base dependencies. See [#5846](https://github.com/DataDog/integrations-core/pull/5846).

## 1.7.0 / 2020-02-22

* [Added] Add `service` option to default configuration. See [#5805](https://github.com/DataDog/integrations-core/pull/5805).
* [Added] Adds RequestsWrapper to Kong. See [#5807](https://github.com/DataDog/integrations-core/pull/5807).

## 1.6.0 / 2020-01-13

* [Added] Use lazy logging format. See [#5398](https://github.com/DataDog/integrations-core/pull/5398).

## 1.5.0 / 2019-05-14

* [Added] Adhere to code style. See [#3524](https://github.com/DataDog/integrations-core/pull/3524).

## 1.4.0 / 2019-03-29

* [Added] Update the kong integration with log instruction. See [#2935](https://github.com/DataDog/integrations-core/pull/2935).

## 1.3.0 / 2019-01-04

* [Added] Support Python 3. See [#2772][1].

## 1.2.1 / 2018-09-04

* [Fixed] Add data files to the wheel package. See [#1727][2].

## 1.2.0 / 2018-05-11

* [FEATURE] Add `ssl_validation` settings to disable SSL Cert Verification

## 1.1.0 / 2018-03-23

* [FEATURE] Add custom tag support to service checks.

## 1.0.0 / 2017-03-22

* [FEATURE] adds kong integration.
[1]: https://github.com/DataDog/integrations-core/pull/2772
[2]: https://github.com/DataDog/integrations-core/pull/1727
