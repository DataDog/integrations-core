# CHANGELOG - JBoss/WildFly

## 1.5.1 / 2021-03-07

* [Fixed] Bump minimum base package version. See [#8443](https://github.com/DataDog/integrations-core/pull/8443).

## 1.5.0 / 2020-12-11 / Agent 7.25.0

* [Added] Document new collect_default_jvm_metrics flag for JMXFetch integrations. See [#8153](https://github.com/DataDog/integrations-core/pull/8153).

## 1.4.0 / 2020-10-31 / Agent 7.24.0

* [Added] Add missing custom_jar_paths option to config. See [#7809](https://github.com/DataDog/integrations-core/pull/7809).
* [Added] [doc] Add encoding in log config sample. See [#7708](https://github.com/DataDog/integrations-core/pull/7708).

## 1.3.3 / 2020-09-21 / Agent 7.23.0

* [Fixed] Use consistent formatting for boolean values. See [#7405](https://github.com/DataDog/integrations-core/pull/7405).

## 1.3.2 / 2020-08-10 / Agent 7.22.0

* [Fixed] Update logs config service field to optional. See [#7209](https://github.com/DataDog/integrations-core/pull/7209).
* [Fixed] Add new_gc_metrics to all jmx integrations. See [#7073](https://github.com/DataDog/integrations-core/pull/7073).

## 1.3.1 / 2020-06-29 / Agent 7.21.0

* [Fixed] Assert new jvm metrics. See [#6996](https://github.com/DataDog/integrations-core/pull/6996).
* [Fixed] Fix template specs typos. See [#6912](https://github.com/DataDog/integrations-core/pull/6912).
* [Fixed] Adjust jmxfetch config. See [#6864](https://github.com/DataDog/integrations-core/pull/6864).

## 1.3.0 / 2020-05-17 / Agent 7.20.0

* [Added] Allow optional dependency installation for all checks. See [#6589](https://github.com/DataDog/integrations-core/pull/6589).
* [Added] Add rmi_connection_timeout & rmi_client_timeout to config spec. See [#6459](https://github.com/DataDog/integrations-core/pull/6459).
* [Added] Add default template to openmetrics & jmx config. See [#6328](https://github.com/DataDog/integrations-core/pull/6328).

## 1.2.0 / 2020-04-04 / Agent 7.19.0

* [Added] Fix service check name and add config spec. See [#6225](https://github.com/DataDog/integrations-core/pull/6225).
* [Fixed] Remove logs sourcecategory. See [#6121](https://github.com/DataDog/integrations-core/pull/6121).
* [Fixed] Various doc fixes. See [#5944](https://github.com/DataDog/integrations-core/pull/5944).

## 1.1.1 / 2019-12-02 / Agent 7.16.0

* [Fixed] Update example config to require `username` and `password`. See [#4445](https://github.com/DataDog/integrations-core/pull/4445).

## 1.1.0 / 2019-06-18 / Agent 6.13.0

* [Added] Add log setup and configuration. See [#3672](https://github.com/DataDog/integrations-core/pull/3672).

## 1.0.0 / 2019-03-29 / Agent 6.11.0

* [Added] JBoss/WildFly JMX Integration. See [#3320](https://github.com/DataDog/integrations-core/pull/3320).
