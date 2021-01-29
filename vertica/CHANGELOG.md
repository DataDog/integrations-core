# CHANGELOG - Vertica

## 2.0.0 / 2021-01-25

* [Added] Update Vertica to use use_tls config. See [#8250](https://github.com/DataDog/integrations-core/pull/8250).
* [Fixed] Correct default template usage. See [#8233](https://github.com/DataDog/integrations-core/pull/8233).
* [Changed] Update Vertica TLS implementation with in-house TLS library. See [#8228](https://github.com/DataDog/integrations-core/pull/8228).

## 1.9.0 / 2020-12-11 / Agent 7.25.0

* [Added] Add option to limit metric collection. See [#7997](https://github.com/DataDog/integrations-core/pull/7997).

## 1.8.0 / 2020-10-31 / Agent 7.24.0

* [Added] [doc] Add encoding in log config sample. See [#7708](https://github.com/DataDog/integrations-core/pull/7708).

## 1.7.0 / 2020-09-21 / Agent 7.23.0

* [Added] Add config spec for Vertica. See [#7513](https://github.com/DataDog/integrations-core/pull/7513).
* [Fixed] Use database config template in existing specs. See [#7548](https://github.com/DataDog/integrations-core/pull/7548).

## 1.6.0 / 2020-08-10 / Agent 7.22.0

* [Added] Improve collection of library logs for debug flares. See [#7252](https://github.com/DataDog/integrations-core/pull/7252).
* [Fixed] Use DEBUG log level for Vertica when Agent log level is DEBUG or TRACE. See [#7264](https://github.com/DataDog/integrations-core/pull/7264).

## 1.5.0 / 2020-05-17 / Agent 7.20.0

* [Added] Allow optional dependency installation for all checks. See [#6589](https://github.com/DataDog/integrations-core/pull/6589).
* [Added] Add version metadata. See [#6346](https://github.com/DataDog/integrations-core/pull/6346).

## 1.4.1 / 2020-04-04 / Agent 7.19.0

* [Fixed] Remove logs sourcecategory. See [#6121](https://github.com/DataDog/integrations-core/pull/6121).

## 1.4.0 / 2020-01-13 / Agent 7.17.0

* [Added] Use lazy logging format. See [#5377](https://github.com/DataDog/integrations-core/pull/5377).
* [Fixed] Upgrade vertica to stop logging to /dev/null. See [#5352](https://github.com/DataDog/integrations-core/pull/5352).

## 1.3.1 / 2019-11-14 / Agent 7.16.0

* [Fixed] Fix client log. See [#5011](https://github.com/DataDog/integrations-core/pull/5011).

## 1.3.0 / 2019-11-14

* [Added] Add vertica lib log config. See [#5005](https://github.com/DataDog/integrations-core/pull/5005).

## 1.2.0 / 2019-11-11

* [Added] Create a new connection at every check run when necessary. See [#4983](https://github.com/DataDog/integrations-core/pull/4983).

## 1.1.1 / 2019-11-06

* [Fixed] Recreate connection when closed. See [#4958](https://github.com/DataDog/integrations-core/pull/4958).

## 1.1.0 / 2019-10-11 / Agent 6.15.0

* [Added] Add more Vertica metrics. See [#4649](https://github.com/DataDog/integrations-core/pull/4649).

## 1.0.0 / 2019-08-24 / Agent 6.14.0

* [Added] Add Vertica integration. See [#3890](https://github.com/DataDog/integrations-core/pull/3890).
