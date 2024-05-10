# CHANGELOG - kafka_consumer

<!-- towncrier release notes start -->

## 4.3.0 / 2024-03-22 / Agent 7.53.0

***Added***:

* Add consumer lag in seconds metric ([#16889](https://github.com/DataDog/integrations-core/pull/16889))

## 4.2.1 / 2024-02-16 / Agent 7.52.0

***Fixed***:

* Update the `log_level` in librkafka and redirect the logs ([#16677](https://github.com/DataDog/integrations-core/pull/16677))

## 4.2.0 / 2024-01-05 / Agent 7.51.0

***Added***:

* Bump the Python version from py3.9 to py3.11 ([#15997](https://github.com/DataDog/integrations-core/pull/15997))

## 4.1.4 / 2023-11-10 / Agent 7.50.0

***Fixed***:

* Attempt client connection before fetching consumer offsets ([#15951](https://github.com/DataDog/integrations-core/pull/15951))
* Bump librdkafka and confluent-kafka to v2.3.0 ([#16088](https://github.com/DataDog/integrations-core/pull/16088))

## 4.1.3 / 2023-10-11 / Agent 7.48.1

***Fixed***:

* Add ability to cache offsets and close admin client ([#15960](https://github.com/DataDog/integrations-core/pull/15960))

## 4.1.2 / 2023-09-04 / Agent 7.48.0

***Fixed***:

* Set tls_verify to string rather than boolean ([#15699](https://github.com/DataDog/integrations-core/pull/15699))
* Filter out empty consumer groups ([#15657](https://github.com/DataDog/integrations-core/pull/15657))

## 4.1.1 / 2023-08-24

***Fixed***:

* Use `_request_timeout` config parameter when querying metadata with kafka client ([#15630](https://github.com/DataDog/integrations-core/pull/15630))

## 4.1.0 / 2023-08-18

***Added***:

* Update dependencies for Agent 7.48 ([#15585](https://github.com/DataDog/integrations-core/pull/15585))

## 4.0.0 / 2023-08-10

***Changed***:

* Bump the minimum base check version ([#15427](https://github.com/DataDog/integrations-core/pull/15427))

***Added***:

* Update generated config models ([#15212](https://github.com/DataDog/integrations-core/pull/15212))

***Fixed***:

* Reduce number of consumer creations ([#15476](https://github.com/DataDog/integrations-core/pull/15476))
* Optimize highwater offset collection ([#15285](https://github.com/DataDog/integrations-core/pull/15285))
* Fix types for generated config models ([#15334](https://github.com/DataDog/integrations-core/pull/15334))
* Simplify regex compilation ([#15239](https://github.com/DataDog/integrations-core/pull/15239))

## 3.1.3 / 2023-08-14 / Agent 7.47.0

***Fixed***:

* Optimize highwater offset collection. See [#15285](https://github.com/DataDog/integrations-core/pull/15285).
* Reduce number of consumer creations. See [#15476](https://github.com/DataDog/integrations-core/pull/15476).

## 3.1.2 / 2023-07-13

***Fixed***:

* Do not check consumer_groups if the offset is invalid ([#15237](https://github.com/DataDog/integrations-core/pull/15237))

## 3.1.1 / 2023-07-10

***Fixed***:

* Fix unnecessary metrics ([#15098](https://github.com/DataDog/integrations-core/pull/15098))
* Bump the confluent-kafka version ([#14665](https://github.com/DataDog/integrations-core/pull/14665))
* Bump Python version from py3.8 to py3.9 ([#14701](https://github.com/DataDog/integrations-core/pull/14701))
* Improve performance of check ([#15106](https://github.com/DataDog/integrations-core/pull/15106))

## 3.1.0 / 2023-05-26 / Agent 7.46.0

***Added***:

* Update kafka consumer consumer_groups_regex example to be more inform… ([#14533](https://github.com/DataDog/integrations-core/pull/14533))

## 3.0.1 / 2023-04-21 / Agent 7.45.0

***Fixed***:

* Fix errors related to filtering based on user-specified consumer groups filters ([#14406](https://github.com/DataDog/integrations-core/pull/14406))
* Move all configuration validation to config class ([#14405](https://github.com/DataDog/integrations-core/pull/14405))

## 3.0.0 / 2023-04-14

***Changed***:

* Revamp Kafka consumer check ([#13918](https://github.com/DataDog/integrations-core/pull/13918))

***Added***:

* Implement regex for consumer_groups ([#14382](https://github.com/DataDog/integrations-core/pull/14382))

## 2.16.4 / 2023-03-03 / Agent 7.44.0

***Fixed***:

* Do not install gssapi and dtrace on py2 on arm macs ([#13749](https://github.com/DataDog/integrations-core/pull/13749))

## 2.16.3 / 2023-01-20 / Agent 7.43.0

***Fixed***:

* Add kafka consumer logs for more visibility ([#13679](https://github.com/DataDog/integrations-core/pull/13679))
* Disable socket wakeups for coordinate ID and consumer group offsets ([#13505](https://github.com/DataDog/integrations-core/pull/13505))

## 2.16.2 / 2022-11-22 / Agent 7.42.0

***Fixed***:

* Disable socket wakeup when sending requests ([#13221](https://github.com/DataDog/integrations-core/pull/13221))

## 2.16.1 / 2022-10-28 / Agent 7.41.0

***Fixed***:

* Update dependencies ([#13205](https://github.com/DataDog/integrations-core/pull/13205))
* Fix sensitive client_secret config specification ([#12983](https://github.com/DataDog/integrations-core/pull/12983))

## 2.16.0 / 2022-09-16 / Agent 7.40.0

***Added***:

* Put lag in seconds behind a feature flag ([#12942](https://github.com/DataDog/integrations-core/pull/12942))

***Fixed***:

* Bump dependencies for 7.40 ([#12896](https://github.com/DataDog/integrations-core/pull/12896))

## 2.15.4 / 2022-09-09

***Fixed***:

* Fix support for OAUTHBEARER SASL mechanism ([#12891](https://github.com/DataDog/integrations-core/pull/12891))

## 2.15.3 / 2022-08-05 / Agent 7.39.0

***Fixed***:

* Handle errors getting producer offset ([#12648](https://github.com/DataDog/integrations-core/pull/12648))

## 2.15.2 / 2022-06-27 / Agent 7.38.0

***Fixed***:

* Fix failed reading and writing to cache when file is too long ([#12109](https://github.com/DataDog/integrations-core/pull/12109))
* Remove unnecessary agent cache implementation ([#12083](https://github.com/DataDog/integrations-core/pull/12083))

## 2.15.1 / 2022-05-31 / Agent 7.37.0

***Fixed***:

* Does not fail reading and writing to cache when file is too long ([#12109](https://github.com/DataDog/integrations-core/pull/12109))

## 2.15.0 / 2022-05-15

***Added***:

* Add new lag in seconds metric ([#11861](https://github.com/DataDog/integrations-core/pull/11861))

## 2.14.0 / 2022-04-05 / Agent 7.36.0

***Added***:

* Add gssapi as a dependency ([#11725](https://github.com/DataDog/integrations-core/pull/11725))
* Add metric_patterns options to filter all metric submission by a list of regexes ([#11695](https://github.com/DataDog/integrations-core/pull/11695))

## 2.13.0 / 2022-02-19 / Agent 7.35.0

***Added***:

* Add `pyproject.toml` file ([#11378](https://github.com/DataDog/integrations-core/pull/11378))

***Fixed***:

* Fix namespace packaging on Python 2 ([#11532](https://github.com/DataDog/integrations-core/pull/11532))

## 2.12.3 / 2022-01-08 / Agent 7.34.0

***Fixed***:

* Add comment to autogenerated model files ([#10945](https://github.com/DataDog/integrations-core/pull/10945))

## 2.12.2 / 2021-12-29

***Fixed***:

* Call correct method when sending events ([#10960](https://github.com/DataDog/integrations-core/pull/10960))

## 2.12.1 / 2021-10-04 / Agent 7.32.0

***Fixed***:

* Bump minimum base package ([#10325](https://github.com/DataDog/integrations-core/pull/10325))

## 2.12.0 / 2021-10-04

***Added***:

* Update dependencies ([#10258](https://github.com/DataDog/integrations-core/pull/10258))

## 2.11.0 / 2021-09-30

***Added***:

* Manually create a `ssl.SSLContext` object for the Kafka client to use ([#10284](https://github.com/DataDog/integrations-core/pull/10284))
* Disable generic tags ([#10027](https://github.com/DataDog/integrations-core/pull/10027))

***Fixed***:

* Remove unused ssl_context documentation ([#10152](https://github.com/DataDog/integrations-core/pull/10152))
* Lazily create client on legacy implementation ([#9981](https://github.com/DataDog/integrations-core/pull/9981))

## 2.10.0 / 2021-08-22 / Agent 7.31.0

***Added***:

* Use `display_default` as a fallback for `default` when validating config models ([#9739](https://github.com/DataDog/integrations-core/pull/9739))

***Fixed***:

* Correctly handle errors during initialization + code refactor ([#9626](https://github.com/DataDog/integrations-core/pull/9626))

## 2.9.0 / 2021-05-28 / Agent 7.29.0

***Added***:

* Add runtime configuration validation ([#8942](https://github.com/DataDog/integrations-core/pull/8942))

***Fixed***:

* Fix zk_connect_str type ([#9368](https://github.com/DataDog/integrations-core/pull/9368))

## 2.8.6 / 2021-04-20 / Agent 7.28.0

***Fixed***:

* Fix warning log format ([#9192](https://github.com/DataDog/integrations-core/pull/9192))
* Provide better error message when api version cannot be determined ([#9186](https://github.com/DataDog/integrations-core/pull/9186))

## 2.8.5 / 2021-04-19

***Fixed***:

* Fix partition check ([#9117](https://github.com/DataDog/integrations-core/pull/9117))

## 2.8.4 / 2021-04-05

***Fixed***:

* Handle missing partitions and better logging ([#9089](https://github.com/DataDog/integrations-core/pull/9089))
* Add more logging ([#8795](https://github.com/DataDog/integrations-core/pull/8795))

## 2.8.3 / 2021-03-07 / Agent 7.27.0

***Fixed***:

* Rename config spec example consumer option `default` to `display_default` ([#8593](https://github.com/DataDog/integrations-core/pull/8593))
* Bump minimum base package version ([#8443](https://github.com/DataDog/integrations-core/pull/8443))

## 2.8.2 / 2021-01-25 / Agent 7.26.0

***Fixed***:

* Make 'Context limit reached' message a warning ([#8254](https://github.com/DataDog/integrations-core/pull/8254))
* Correct default template usage ([#8233](https://github.com/DataDog/integrations-core/pull/8233))

## 2.8.1 / 2020-12-15 / Agent 7.25.0

***Fixed***:

* Use spec template ([#8192](https://github.com/DataDog/integrations-core/pull/8192))

## 2.8.0 / 2020-12-11

***Added***:

* Add Kafka Consumer spec ([#8108](https://github.com/DataDog/integrations-core/pull/8108))

***Fixed***:

* Update deprecation notice ([#8161](https://github.com/DataDog/integrations-core/pull/8161))

## 2.7.0 / 2020-10-31 / Agent 7.24.0

***Added***:

* Support Windows ([#7781](https://github.com/DataDog/integrations-core/pull/7781))
* Collect version metadata ([#6556](https://github.com/DataDog/integrations-core/pull/6556))

***Fixed***:

* Update kafka-python to 2.0.2 ([#7718](https://github.com/DataDog/integrations-core/pull/7718))

## 2.6.1 / 2020-09-21 / Agent 7.23.0

***Fixed***:

* lazy initialisation of kafka_consumer client ([#7432](https://github.com/DataDog/integrations-core/pull/7432))

## 2.6.0 / 2020-07-27 / Agent 7.22.0

***Added***:

* Smaller batches when fetching highwater offsets ([#7093](https://github.com/DataDog/integrations-core/pull/7093))

***Fixed***:

* Limit the number of reported contexts ([#7084](https://github.com/DataDog/integrations-core/pull/7084))

## 2.5.0 / 2020-05-17 / Agent 7.20.0

***Added***:

* Allow optional dependency installation for all checks ([#6589](https://github.com/DataDog/integrations-core/pull/6589))

## 2.4.0 / 2020-02-22 / Agent 7.18.0

***Added***:

* Re-enable `kafka_client_api_version` option ([#5726](https://github.com/DataDog/integrations-core/pull/5726))
* Use top-level kafka imports to be more future-proof ([#5702](https://github.com/DataDog/integrations-core/pull/5702))
* Upgrade kafka-python to 2.0.0 ([#5696](https://github.com/DataDog/integrations-core/pull/5696))

***Fixed***:

* Anticipate potential bug when instantiating the Kafka admin client ([#5464](https://github.com/DataDog/integrations-core/pull/5464))

## 2.3.0 / 2020-01-28 / Agent 7.17.0

***Added***:

* Update imports for newer versions of kafka-python ([#5489](https://github.com/DataDog/integrations-core/pull/5489))

## 2.2.0 / 2020-01-13

***Added***:

* Use lazy logging format ([#5398](https://github.com/DataDog/integrations-core/pull/5398))
* Use lazy logging format ([#5377](https://github.com/DataDog/integrations-core/pull/5377))

***Fixed***:

* Fix `kafka_client_api_version` ([#5007](https://github.com/DataDog/integrations-core/pull/5007))

## 2.1.1 / 2019-11-27 / Agent 7.16.0

***Fixed***:

* Handle missing partitions ([#5035](https://github.com/DataDog/integrations-core/pull/5035))
* Handle topics set to empty dict ([#4974](https://github.com/DataDog/integrations-core/pull/4974))
* Fix error on missing config ([#4959](https://github.com/DataDog/integrations-core/pull/4959))

## 2.1.0 / 2019-10-09 / Agent 6.15.0

***Added***:

* Add support for fetching consumer offsets stored in Kafka to `monitor_unlisted_consumer_groups` ([#3957](https://github.com/DataDog/integrations-core/pull/3957)) Thanks [jeffwidman](https://github.com/jeffwidman).

## 2.0.1 / 2019-08-27 / Agent 6.14.0

***Fixed***:

* Fix logger call during exceptions ([#4440](https://github.com/DataDog/integrations-core/pull/4440))

## 2.0.0 / 2019-08-24

***Changed***:

* Drop `source:kafka` from tags. ([#4400](https://github.com/DataDog/integrations-core/pull/4400)) Thanks [jeffwidman](https://github.com/jeffwidman).
* Remove rarely used zookeeper-specific min collection interval ([#4269](https://github.com/DataDog/integrations-core/pull/4269)) Thanks [jeffwidman](https://github.com/jeffwidman).

***Added***:

* Force initial population of the cluster cache ([#4394](https://github.com/DataDog/integrations-core/pull/4394)) Thanks [jeffwidman](https://github.com/jeffwidman).
* Add flag `monitor_all_broker_highwatermarks`, refactor ([#4385](https://github.com/DataDog/integrations-core/pull/4385)) Thanks [jeffwidman](https://github.com/jeffwidman).
* Better manage partitions that are in the middle of failover ([#4382](https://github.com/DataDog/integrations-core/pull/4382)) Thanks [jeffwidman](https://github.com/jeffwidman).
* Document kafka_client_api_version ([#4381](https://github.com/DataDog/integrations-core/pull/4381)) Thanks [jeffwidman](https://github.com/jeffwidman).
* Make the Zookeeper client instance long-lived ([#4378](https://github.com/DataDog/integrations-core/pull/4378)) Thanks [jeffwidman](https://github.com/jeffwidman).
* Document that fetching consumer offsets from Zookeeper is deprecated ([#4272](https://github.com/DataDog/integrations-core/pull/4272)) Thanks [jeffwidman](https://github.com/jeffwidman).
* Cleanup pointless retries that query the wrong brokers / duplicate kafka-python functionality ([#4271](https://github.com/DataDog/integrations-core/pull/4271)) Thanks [jeffwidman](https://github.com/jeffwidman).
* Bump Kazoo to 2.6.1 to pull in some minor bugfixes ([#4260](https://github.com/DataDog/integrations-core/pull/4260)) Thanks [jeffwidman](https://github.com/jeffwidman).
* Remove unnecessary constants and cleanup error handling ([#4256](https://github.com/DataDog/integrations-core/pull/4256)) Thanks [jeffwidman](https://github.com/jeffwidman).

***Fixed***:

* Fix kafka_consumer python3 compatibility check regression ([#4387](https://github.com/DataDog/integrations-core/pull/4387))

## 1.10.0 / 2019-06-19 / Agent 6.13.0

***Added***:

* Refactor check to support different versions easily ([#3929](https://github.com/DataDog/integrations-core/pull/3929))

## 1.9.2 / 2019-06-04 / Agent 6.12.0

***Fixed***:

* Fix example conf file ([#3860](https://github.com/DataDog/integrations-core/pull/3860))

## 1.9.1 / 2019-06-01

***Fixed***:

* Fix code style ([#3838](https://github.com/DataDog/integrations-core/pull/3838))
* Handle empty topics and partitions ([#3807](https://github.com/DataDog/integrations-core/pull/3807))

## 1.9.0 / 2019-05-14

***Added***:

* Adhere to code style ([#3523](https://github.com/DataDog/integrations-core/pull/3523))

***Fixed***:

* Fix kafka_consumer conf file ([#3757](https://github.com/DataDog/integrations-core/pull/3757))

## 1.8.1 / 2019-03-29 / Agent 6.11.0

***Fixed***:

* Properly cache zookeeper connection strings ([#3333](https://github.com/DataDog/integrations-core/pull/3333))

## 1.8.0 / 2019-03-08

***Added***:

* Add support for SASL_PLAINTEXT authentication with Kafka broker ([#3056](https://github.com/DataDog/integrations-core/pull/3056))

## 1.7.0 / 2019-02-18 / Agent 6.10.0

***Added***:

* Finish Python 3 Support ([#2912](https://github.com/DataDog/integrations-core/pull/2912))

***Fixed***:

* Resolve flake8 issues ([#3060](https://github.com/DataDog/integrations-core/pull/3060))

## 1.6.0 / 2019-01-04 / Agent 6.9.0

***Added***:

* [kafka_consumer] Bump vendored kazoo to 2.6.0 ([#2729](https://github.com/DataDog/integrations-core/pull/2729)) Thanks [jeffwidman](https://github.com/jeffwidman).
* [kafka_consumer] Bump kafka-python to 1.4.4 ([#2728](https://github.com/DataDog/integrations-core/pull/2728)) Thanks [jeffwidman](https://github.com/jeffwidman).

## 1.5.0 / 2018-11-30 / Agent 6.8.0

***Added***:

* Support Python 3 ([#2648](https://github.com/DataDog/integrations-core/pull/2648))

## 1.4.1 / 2018-09-04 / Agent 6.5.0

***Fixed***:

* Add data files to the wheel package ([#1727](https://github.com/DataDog/integrations-core/pull/1727))

## 1.4.0 / 2018-06-04

***Changed***:

* Bump to kafka-python 1.4.3 ([#1627](https://github.com/DataDog/integrations-core/pull/1627)) Thanks [jeffwidman](https://github.com/jeffwidman).

## 1.3.0 / 2018-03-23

***Added***:

* Add SSL as a connect option.
* Add custom tag support.

## 1.2.2 / 2018-02-13

***Fixed***:

* Check explicitly that node_id is None instead of 0 ([#1022](https://github)com/DataDog/integrations-core/issues1022)

## 1.2.1 / 2017-11-29

***Fixed***:

* Use instance key to retrieve cached kafka_client, See [#904](https://github.com/DataDog/integrations-core/issues/904)

## 1.2.0 / 2017-11-21

***Added***:

* Support collection of consumer offsets from Kafka, in addition to ZK ([#654](https://github)com/DataDog/integrations-core/issues/654)

## 1.1.0 / 2017-10-10

***Added***:

* discovery of groups, topics and partitions ([#633](https://github.com/DataDog/integrations-core/issues/633) (Thanks [@jeffwidman](https://github)com/jeffwidman))

***Fixed***:

* set upper bound on number of contexts. Submit "broker available" metrics ([#753](https://github)com/DataDog/integrations-core/issues/753)
* Remove usage of `AgentCheck.read_config` (deprecated method) ([#733](https://github)com/DataDog/integrations-core/issues/733)

## 1.0.2 / 2017-08-28

***Added***:

* Bump Kazoo dependency to 2.4.0 ([#623](https://github.com/DataDog/integrations-core/issues/623), thanks [@jeffwidman](https://github)com/jeffwidman)
* Bump kafka-python to 1.3.4 ([#684](https://github.com/DataDog/integrations-core/issues/684), thanks [@jeffwidman](https://github)com/jeffwidman)
* Switch ZK example from string to list ([#624](https://github.com/DataDog/integrations-core/issues/624), thanks [@jeffwidman](https://github)com/jeffwidman)

## 1.0.1 / 2017-04-24

***Changed***:

* bumping kafka-python to 0.3.3 ([#272](https://github.com/DataDog/integrations-core/issues/272) (Thanks [@jeffwidman](https://github)com/jeffwidman))

## 1.0.0 / 2017-03-22

***Added***:

* adds kafka_consumer integration.
