# CHANGELOG - SonarQube

## 1.5.0 / 2021-10-04

* [Added] Add HTTP option to control the size of streaming responses. See [#10183](https://github.com/DataDog/integrations-core/pull/10183).
* [Added] Add allow_redirect option. See [#10160](https://github.com/DataDog/integrations-core/pull/10160).
* [Added] Disable generic tags. See [#10027](https://github.com/DataDog/integrations-core/pull/10027).
* [Fixed] Fix the description of the `allow_redirects` HTTP option. See [#10195](https://github.com/DataDog/integrations-core/pull/10195).

## 1.4.0 / 2021-08-22 / Agent 7.31.0

* [Added] Use `display_default` as a fallback for `default` when validating config models. See [#9739](https://github.com/DataDog/integrations-core/pull/9739).

## 1.3.0 / 2021-07-12 / Agent 7.30.0

* [Added] Enable `new_gc_metrics` JMX config option for new installations. See [#9501](https://github.com/DataDog/integrations-core/pull/9501).

## 1.2.0 / 2021-05-28 / Agent 7.29.0

* [Added] Add runtime configuration validation. See [#8985](https://github.com/DataDog/integrations-core/pull/8985).
* [Fixed] Fix defaults for `collect_default_metrics` JMX config option. See [#9441](https://github.com/DataDog/integrations-core/pull/9441).
* [Fixed] Fix JMX config spec. See [#9364](https://github.com/DataDog/integrations-core/pull/9364).

## 1.1.2 / 2021-03-12 / Agent 7.27.0

* [Fixed] Fix collection of PendingTime. See [#8817](https://github.com/DataDog/integrations-core/pull/8817).

## 1.1.1 / 2021-02-16

* [Fixed] Fix automatic discovery of metrics from web API and improve example config documentation. See [#8552](https://github.com/DataDog/integrations-core/pull/8552).
* [Fixed] Bump minimum base package version. See [#8443](https://github.com/DataDog/integrations-core/pull/8443).

## 1.1.0 / 2020-12-11 / Agent 7.25.0

* [Added] Document new collect_default_jvm_metrics flag for JMXFetch integrations. See [#8153](https://github.com/DataDog/integrations-core/pull/8153).

## 1.0.0 / 2020-11-20

* [Added] Add SonarQube integration. See [#7807](https://github.com/DataDog/integrations-core/pull/7807).

