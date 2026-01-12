# Changes

## 0.6.0

* [Added] Add cumulative metrics support to mirror JMeter's Aggregate Report.
* [Added] Add `statisticsCalculationMode` configuration option to control percentile calculation algorithms (`ddsketch`, `aggregate_report`, `dashboard`).
* [Added] Add assertion metrics to track success and failure of assertions.
* [Added] Add Datadog Events for test start and test end.

## 0.5.0

* [Added] Add ability to exclude sample results to be sent as logs based on response code regex
  See [#47](https://github.com/DataDog/jmeter-datadog-backend-listener/issues/47)

## 0.4.0

* [Changed] Set configured tags on plugin generated logs. (See [#45](https://github.com/DataDog/jmeter-datadog-backend-listener/pull/45)).

## 0.3.1

* [Fixed] Setting `includeSubresults` to `true` will now also include the parent results as well as subresults recursively (See [#35](https://github.com/DataDog/jmeter-datadog-backend-listener/pull/35)).

## 0.3.0

* [Added] Add ability to release to Maven Central. See [#26](https://github.com/DataDog/jmeter-datadog-backend-listener/pull/26)
* [Added] Add custom tags to global metrics. See [#23](https://github.com/DataDog/jmeter-datadog-backend-listener/pull/23)

## 0.2.0

* [Added] Add `customTags` config option. See [#15](https://github.com/DataDog/jmeter-datadog-backend-listener/pull/15)
* [Added] Tag metrics by `thread_group`. See [#17](https://github.com/DataDog/jmeter-datadog-backend-listener/pull/17)
* [Added] Add `thread_group` to log payload. See [#18](https://github.com/DataDog/jmeter-datadog-backend-listener/pull/18)

## 0.1.0

Initial release
