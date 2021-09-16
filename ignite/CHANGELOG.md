# CHANGELOG - ignite

## 2.0.0 / 2021-08-22 / Agent 7.31.0

* [Changed] Change `ignite.total_allocated_pages` and `ignite.total_allocated_size` from monotonic_count to gauge. See [#9939](https://github.com/DataDog/integrations-core/pull/9939).

## 1.4.0 / 2021-07-12 / Agent 7.30.0

* [Added] Enable `new_gc_metrics` JMX config option for new installations. See [#9501](https://github.com/DataDog/integrations-core/pull/9501).

## 1.3.2 / 2021-05-28 / Agent 7.29.0

* [Fixed] Fix defaults for `collect_default_metrics` JMX config option. See [#9441](https://github.com/DataDog/integrations-core/pull/9441).
* [Fixed] Fix JMX config spec. See [#9364](https://github.com/DataDog/integrations-core/pull/9364).

## 1.3.1 / 2021-03-07 / Agent 7.27.0

* [Fixed] Bump minimum base package version. See [#8443](https://github.com/DataDog/integrations-core/pull/8443).

## 1.3.0 / 2020-12-11 / Agent 7.25.0

* [Added] Document new collect_default_jvm_metrics flag for JMXFetch integrations. See [#8153](https://github.com/DataDog/integrations-core/pull/8153).

## 1.2.0 / 2020-10-31 / Agent 7.24.0

* [Added] [doc] Add encoding in log config sample. See [#7708](https://github.com/DataDog/integrations-core/pull/7708).

## 1.1.1 / 2020-09-21 / Agent 7.23.0

* [Fixed] Use consistent formatting for boolean values. See [#7405](https://github.com/DataDog/integrations-core/pull/7405).

## 1.1.0 / 2020-08-10 / Agent 7.22.0

* [Added] Convert jmx to in-app types for replay_check_run. See [#7275](https://github.com/DataDog/integrations-core/pull/7275).
* [Fixed] Update logs config service field to optional. See [#7209](https://github.com/DataDog/integrations-core/pull/7209).
* [Fixed] Add new_gc_metrics to all jmx integrations. See [#7073](https://github.com/DataDog/integrations-core/pull/7073).

## 1.0.1 / 2020-06-29 / Agent 7.21.0

* [Fixed] Assert new jvm metrics. See [#6996](https://github.com/DataDog/integrations-core/pull/6996).
* [Fixed] Fix template specs typos. See [#6912](https://github.com/DataDog/integrations-core/pull/6912).
* [Fixed] Adjust jmxfetch config. See [#6864](https://github.com/DataDog/integrations-core/pull/6864).

## 1.0.0 / 2020-05-17 / Agent 7.20.0

* [Added] Add new integration Apache Ignite. See [#5767](https://github.com/DataDog/integrations-core/pull/5767).
