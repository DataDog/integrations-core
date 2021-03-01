# CHANGELOG - kafka_consumer

## 2.8.2 / 2021-01-25

* [Fixed] Make 'Context limit reached' message a warning. See [#8254](https://github.com/DataDog/integrations-core/pull/8254).
* [Fixed] Correct default template usage. See [#8233](https://github.com/DataDog/integrations-core/pull/8233).

## 2.8.1 / 2020-12-15 / Agent 7.25.0

* [Fixed] Use spec template. See [#8192](https://github.com/DataDog/integrations-core/pull/8192).

## 2.8.0 / 2020-12-11

* [Added] Add Kafka Consumer spec. See [#8108](https://github.com/DataDog/integrations-core/pull/8108).
* [Fixed] Update deprecation notice. See [#8161](https://github.com/DataDog/integrations-core/pull/8161).

## 2.7.0 / 2020-10-31 / Agent 7.24.0

* [Added] Support Windows. See [#7781](https://github.com/DataDog/integrations-core/pull/7781).
* [Added] Collect version metadata. See [#6556](https://github.com/DataDog/integrations-core/pull/6556).
* [Fixed] Update kafka-python to 2.0.2. See [#7718](https://github.com/DataDog/integrations-core/pull/7718).

## 2.6.1 / 2020-09-21 / Agent 7.23.0

* [Fixed] lazy initialisation of kafka_consumer client. See [#7432](https://github.com/DataDog/integrations-core/pull/7432).

## 2.6.0 / 2020-07-27 / Agent 7.22.0

* [Added] Smaller batches when fetching highwater offsets. See [#7093](https://github.com/DataDog/integrations-core/pull/7093).
* [Fixed] Limit the number of reported contexts. See [#7084](https://github.com/DataDog/integrations-core/pull/7084).

## 2.5.0 / 2020-05-17 / Agent 7.20.0

* [Added] Allow optional dependency installation for all checks. See [#6589](https://github.com/DataDog/integrations-core/pull/6589).

## 2.4.0 / 2020-02-22 / Agent 7.18.0

* [Added] Re-enable `kafka_client_api_version` option. See [#5726](https://github.com/DataDog/integrations-core/pull/5726).
* [Added] Use top-level kafka imports to be more future-proof. See [#5702](https://github.com/DataDog/integrations-core/pull/5702).
* [Added] Upgrade kafka-python to 2.0.0. See [#5696](https://github.com/DataDog/integrations-core/pull/5696).
* [Fixed] Anticipate potential bug when instantiating the Kafka admin client. See [#5464](https://github.com/DataDog/integrations-core/pull/5464).

## 2.3.0 / 2020-01-28 / Agent 7.17.0

* [Added] Update imports for newer versions of kafka-python. See [#5489](https://github.com/DataDog/integrations-core/pull/5489).

## 2.2.0 / 2020-01-13

* [Added] Use lazy logging format. See [#5398](https://github.com/DataDog/integrations-core/pull/5398).
* [Added] Use lazy logging format. See [#5377](https://github.com/DataDog/integrations-core/pull/5377).
* [Fixed] Fix `kafka_client_api_version`. See [#5007](https://github.com/DataDog/integrations-core/pull/5007).

## 2.1.1 / 2019-11-27 / Agent 7.16.0

* [Fixed] Handle missing partitions. See [#5035](https://github.com/DataDog/integrations-core/pull/5035).
* [Fixed] Handle topics set to empty dict. See [#4974](https://github.com/DataDog/integrations-core/pull/4974).
* [Fixed] Fix error on missing config. See [#4959](https://github.com/DataDog/integrations-core/pull/4959).

## 2.1.0 / 2019-10-09 / Agent 6.15.0

* [Added] Add support for fetching consumer offsets stored in Kafka to `monitor_unlisted_consumer_groups`. See [#3957](https://github.com/DataDog/integrations-core/pull/3957). Thanks [jeffwidman](https://github.com/jeffwidman).

## 2.0.1 / 2019-08-27 / Agent 6.14.0

* [Fixed] Fix logger call during exceptions. See [#4440](https://github.com/DataDog/integrations-core/pull/4440).

## 2.0.0 / 2019-08-24

* [Changed] Drop `source:kafka` from tags.. See [#4400](https://github.com/DataDog/integrations-core/pull/4400). Thanks [jeffwidman](https://github.com/jeffwidman).
* [Added] Force initial population of the cluster cache. See [#4394](https://github.com/DataDog/integrations-core/pull/4394). Thanks [jeffwidman](https://github.com/jeffwidman).
* [Added] Add flag `monitor_all_broker_highwatermarks`, refactor. See [#4385](https://github.com/DataDog/integrations-core/pull/4385). Thanks [jeffwidman](https://github.com/jeffwidman).
* [Fixed] Fix kafka_consumer python3 compatibility check regression. See [#4387](https://github.com/DataDog/integrations-core/pull/4387).
* [Added] Better manage partitions that are in the middle of failover. See [#4382](https://github.com/DataDog/integrations-core/pull/4382). Thanks [jeffwidman](https://github.com/jeffwidman).
* [Added] Document kafka_client_api_version. See [#4381](https://github.com/DataDog/integrations-core/pull/4381). Thanks [jeffwidman](https://github.com/jeffwidman).
* [Added] Make the Zookeeper client instance long-lived. See [#4378](https://github.com/DataDog/integrations-core/pull/4378). Thanks [jeffwidman](https://github.com/jeffwidman).
* [Added] Document that fetching consumer offsets from Zookeeper is deprecated. See [#4272](https://github.com/DataDog/integrations-core/pull/4272). Thanks [jeffwidman](https://github.com/jeffwidman).
* [Added] Cleanup pointless retries that query the wrong brokers / duplicate kafka-python functionality. See [#4271](https://github.com/DataDog/integrations-core/pull/4271). Thanks [jeffwidman](https://github.com/jeffwidman).
* [Changed] Remove rarely used zookeeper-specific min collection interval. See [#4269](https://github.com/DataDog/integrations-core/pull/4269). Thanks [jeffwidman](https://github.com/jeffwidman).
* [Added] Bump Kazoo to 2.6.1 to pull in some minor bugfixes. See [#4260](https://github.com/DataDog/integrations-core/pull/4260). Thanks [jeffwidman](https://github.com/jeffwidman).
* [Added] Remove unnecessary constants and cleanup error handling. See [#4256](https://github.com/DataDog/integrations-core/pull/4256). Thanks [jeffwidman](https://github.com/jeffwidman).

## 1.10.0 / 2019-06-19 / Agent 6.13.0

* [Added] Refactor check to support different versions easily. See [#3929](https://github.com/DataDog/integrations-core/pull/3929).

## 1.9.2 / 2019-06-04 / Agent 6.12.0

* [Fixed] Fix example conf file. See [#3860](https://github.com/DataDog/integrations-core/pull/3860).

## 1.9.1 / 2019-06-01

* [Fixed] Fix code style. See [#3838](https://github.com/DataDog/integrations-core/pull/3838).
* [Fixed] Handle empty topics and partitions. See [#3807](https://github.com/DataDog/integrations-core/pull/3807).

## 1.9.0 / 2019-05-14

* [Fixed] Fix kafka_consumer conf file. See [#3757](https://github.com/DataDog/integrations-core/pull/3757).
* [Added] Adhere to code style. See [#3523](https://github.com/DataDog/integrations-core/pull/3523).

## 1.8.1 / 2019-03-29 / Agent 6.11.0

* [Fixed] Properly cache zookeeper connection strings. See [#3333](https://github.com/DataDog/integrations-core/pull/3333).

## 1.8.0 / 2019-03-08

* [Added] Add support for SASL_PLAINTEXT authentication with Kafka broker. See [#3056](https://github.com/DataDog/integrations-core/pull/3056).

## 1.7.0 / 2019-02-18 / Agent 6.10.0

* [Fixed] Resolve flake8 issues. See [#3060](https://github.com/DataDog/integrations-core/pull/3060).
* [Added] Finish Python 3 Support. See [#2912](https://github.com/DataDog/integrations-core/pull/2912).

## 1.6.0 / 2019-01-04 / Agent 6.9.0

* [Added] [kafka_consumer] Bump vendored kazoo to 2.6.0. See [#2729][1]. Thanks [jeffwidman][2].
* [Added] [kafka_consumer] Bump kafka-python to 1.4.4. See [#2728][3]. Thanks [jeffwidman][2].

## 1.5.0 / 2018-11-30 / Agent 6.8.0

* [Added] Support Python 3. See [#2648][4].

## 1.4.1 / 2018-09-04 / Agent 6.5.0

* [Fixed] Add data files to the wheel package. See [#1727][5].

## 1.4.0 / 2018-06-04

* [Changed] Bump to kafka-python 1.4.3. See [#1627][6]. Thanks [jeffwidman][2].

## 1.3.0 / 2018-03-23

* [FEATURE] Add SSL as a connect option.
* [FEATURE] Add custom tag support.

## 1.2.2 / 2018-02-13

* [BUGFIX] Check explicitly that node_id is None instead of 0. See [#1022][7]

## 1.2.1 / 2017-11-29

* [BUGFIX] Use instance key to retrieve cached kafka_client, See [#904][8]

## 1.2.0 / 2017-11-21

* [FEATURE] Support collection of consumer offsets from Kafka, in addition to ZK. See [#654][9]

## 1.1.0 / 2017-10-10

* [FEATURE] discovery of groups, topics and partitions. See [#633][10] (Thanks [@jeffwidman][11])
* [SANITY] set upper bound on number of contexts. Submit "broker available" metrics. See [#753][12]
* [SANITY] Remove usage of `AgentCheck.read_config` (deprecated method). See [#733][13]

## 1.0.2 / 2017-08-28

* [IMPROVEMENT] Bump Kazoo dependency to 2.4.0. See [#623][14], thanks [@jeffwidman][11]
* [IMPROVEMENT] Bump kafka-python to 1.3.4. See [#684][15], thanks [@jeffwidman][11]
* [IMPROVEMENT] Switch ZK example from string to list. See [#624][16], thanks [@jeffwidman][11]

## 1.0.1 / 2017-04-24

* [DEPENDENCY] bumping kafka-python to 0.3.3. See [#272][17] (Thanks [@jeffwidman][11])

## 1.0.0 / 2017-03-22

* [FEATURE] adds kafka_consumer integration.

<!--- The following link definition list is generated by PimpMyChangelog --->
[1]: https://github.com/DataDog/integrations-core/pull/2729
[2]: https://github.com/jeffwidman
[3]: https://github.com/DataDog/integrations-core/pull/2728
[4]: https://github.com/DataDog/integrations-core/pull/2648
[5]: https://github.com/DataDog/integrations-core/pull/1727
[6]: https://github.com/DataDog/integrations-core/pull/1627
[7]: https://github.com/DataDog/integrations-core/issues1022
[8]: https://github.com/DataDog/integrations-core/issues/904
[9]: https://github.com/DataDog/integrations-core/issues/654
[10]: https://github.com/DataDog/integrations-core/issues/633
[11]: https://github.com/jeffwidman
[12]: https://github.com/DataDog/integrations-core/issues/753
[13]: https://github.com/DataDog/integrations-core/issues/733
[14]: https://github.com/DataDog/integrations-core/issues/623
[15]: https://github.com/DataDog/integrations-core/issues/684
[16]: https://github.com/DataDog/integrations-core/issues/624
[17]: https://github.com/DataDog/integrations-core/issues/272
