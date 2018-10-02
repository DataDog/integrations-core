# CHANGELOG - rabbitmq

## 1.5.2 / 2018-09-04

* [Fixed] Add data files to the wheel package. See [#1727](https://github.com/DataDog/integrations-core/pull/1727).

## 1.5.1 / 2018-03-23

* [BUGFIX] URL encode queue names that might have special characters like '#'. See [#1100][], thanks [@sylr][].

## 1.5.0 / 2018-02-13

* [IMPROVEMENT] begin deprecation of `no_proxy` config flag in favor of `skip_proxy`. See [#1057][].

## 1.4.0 / 2018-01-10

* [FEATURE] Add data collection for exchanges. See [#176][]. (Thanks [@wholroyd][])
* [FEATURE] Add a metric illustrating the available disk space. See [#902][]. (Thanks [@dnavre][])
* [BUGFIX] Assume a protocol if there isn't one, fixing a bug if you don't use a protocol. See [#909][].
* [IMPROVEMENT] If vhosts are listed in the config, the check will only query for those specific vhosts, rather than querying for all of them. See [#910][].
* [FEATURE] Add metrics to monitor a cluster. See [#924][]

## 1.3.1 / 2017-10-10

* [BUGFIX] Add a key check before updating connection state metric. See [#729][]. (Thanks [@ian28223][])

## 1.3.0 / 2017-08-28

* [FEATURE] Add a metric to get the number of bindings for a queue. See [#674][]
* [BUGFIX] Set aliveness service to CRITICAL if the rabbitmq server is down. See[#635][]

## 1.2.0 / 2017-07-18

* [FEATURE] Add a metric about the number of connections to rabbitmq. See [#504][]
* [FEATURE] Add custom tags to metrics, event and service checks. See [#506][]
* [FEATURE] Add a metric about the number of each connection states. See [#514][] (Thanks [@jamescarr][])

## 1.1.0 / 2017-06-05

* [IMPROVEMENT] Disable proxy if so-desired. See [#407][]

## 1.0.0 / 2017-03-22

* [FEATURE] adds rabbitmq integration.

[#407]: https://github.com/DataDog/integrations-core/issues/407
[#504]: https://github.com/DataDog/integrations-core/issues/504
[#506]: https://github.com/DataDog/integrations-core/issues/506
[#514]: https://github.com/DataDog/integrations-core/issues/514
[#635]: https://github.com/DataDog/integrations-core/issues/635
[#674]: https://github.com/DataDog/integrations-core/issues/674
[#729]: https://github.com/DataDog/integrations-core/issues/729
[#902]: https://github.com/DataDog/integrations-core/issues/902
[#909]: https://github.com/DataDog/integrations-core/issues/909
[#924]: https://github.com/DataDog/integrations-core/issues/924
[#909]: https://github.com/DataDog/integrations-core/issues/909
[#910]: https://github.com/DataDog/integrations-core/issues/910
[#1100]: https://github.com/DataDog/integrations-core/issues/1100
[@dnavre]: https://github.com/dnavre
[@ian28223]: https://github.com/ian28223
[@jamescarr]: https://github.com/jamescarr
[@sylr]: https://github.com/sylr
