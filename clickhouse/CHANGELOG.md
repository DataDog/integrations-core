# CHANGELOG - ClickHouse

## 2.0.1 / 2021-01-25

* [Fixed] Remove `calculate_text_stack_trace` setting to allow the use of read-only accounts. See [#6637](https://github.com/DataDog/integrations-core/pull/6637). Thanks [TheMcGoose](https://github.com/TheMcGoose).

## 2.0.0 / 2020-10-31 / Agent 7.24.0

* [Added] [doc] Add encoding in log config sample. See [#7708](https://github.com/DataDog/integrations-core/pull/7708).
* [Changed] QueryManager - Prevent queries leaking between check instances. See [#7750](https://github.com/DataDog/integrations-core/pull/7750).

## 1.4.0 / 2020-09-21 / Agent 7.23.0

* [Added] Add config specs to clickhouse. See [#7433](https://github.com/DataDog/integrations-core/pull/7433).
* [Fixed] Use database config template in existing specs. See [#7548](https://github.com/DataDog/integrations-core/pull/7548).
* [Fixed] Fix style for the latest release of Black. See [#7438](https://github.com/DataDog/integrations-core/pull/7438).

## 1.3.2 / 2020-07-09 / Agent 7.22.0

* [Fixed] Update `can_connect` service check status on each check run. See [#7006](https://github.com/DataDog/integrations-core/pull/7006). Thanks [isaachui](https://github.com/isaachui).

## 1.3.1 / 2020-06-19 / Agent 7.21.0

* [Fixed] Submit `can_connect` service check on each check run. See [#6926](https://github.com/DataDog/integrations-core/pull/6926).

## 1.3.0 / 2020-05-17 / Agent 7.20.0

* [Added] Allow optional dependency installation for all checks. See [#6589](https://github.com/DataDog/integrations-core/pull/6589).

## 1.2.0 / 2020-04-04 / Agent 7.19.0

* [Added] Add `ddev test` option to verify support of new metrics. See [#6141](https://github.com/DataDog/integrations-core/pull/6141).
* [Added] Add new metrics: `cache_dictionary.update_queue.batches`, `cache_dictionary.update_queue.keys` . See [#5976](https://github.com/DataDog/integrations-core/pull/5976).
* [Fixed] Remove logs sourcecategory. See [#6121](https://github.com/DataDog/integrations-core/pull/6121).

## 1.1.0 / 2020-02-22 / Agent 7.18.0

* [Added] Add newly-documented metrics. See [#5795](https://github.com/DataDog/integrations-core/pull/5795).
* [Added] Add new metric for tracking MySQL connections. See [#5700](https://github.com/DataDog/integrations-core/pull/5700).

## 1.0.1 / 2020-01-24 / Agent 7.17.0

* [Fixed] Fix config. See [#5551](https://github.com/DataDog/integrations-core/pull/5551).

## 1.0.0 / 2019-12-18

* [Added] Add ClickHouse integration. See [#4957](https://github.com/DataDog/integrations-core/pull/4957).
