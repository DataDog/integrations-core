# CHANGELOG - network

## 2.1.1 / 2021-01-26

* [Fixed] Ensure network check doesn't fail on importing fcntl on Windows. See [#8459](https://github.com/DataDog/integrations-core/pull/8459).

## 2.1.0 / 2021-01-25

* [Added] Collect AWS ENA metrics. See [#8331](https://github.com/DataDog/integrations-core/pull/8331).
* [Fixed] Correct default template usage. See [#8233](https://github.com/DataDog/integrations-core/pull/8233).

## 2.0.0 / 2020-12-11 / Agent 7.25.0

* [Changed] [network] Set the collect_connection_queues parameter default value to false. See [#8059](https://github.com/DataDog/integrations-core/pull/8059).

## 1.19.0 / 2020-10-31 / Agent 7.24.0

* [Added] Collect receive and send queue metrics. See [#7861](https://github.com/DataDog/integrations-core/pull/7861).
* [Added] Collect connection state metrics on BSD/OSX. See [#7659](https://github.com/DataDog/integrations-core/pull/7659).
* [Fixed] Fix network metric collection failure on CentOS. See [#7883](https://github.com/DataDog/integrations-core/pull/7883).

## 1.18.1 / 2020-09-28 / Agent 7.23.0

* [Fixed] Fix procfs_path retrieval in network check. See [#7652](https://github.com/DataDog/integrations-core/pull/7652).

## 1.18.0 / 2020-09-21

* [Added] Pass `PROC_ROOT` as environment variable to `ss`. See [#7095](https://github.com/DataDog/integrations-core/pull/7095).
* [Added] Upgrade psutil to 5.7.2. See [#7395](https://github.com/DataDog/integrations-core/pull/7395).

## 1.17.0 / 2020-06-29 / Agent 7.21.0

* [Added] Add network spec. See [#6889](https://github.com/DataDog/integrations-core/pull/6889).

## 1.16.0 / 2020-05-17 / Agent 7.20.0

* [Added] Allow optional dependency installation for all checks. See [#6589](https://github.com/DataDog/integrations-core/pull/6589).

## 1.15.1 / 2020-04-08 / Agent 7.19.0

* [Fixed] Fix error message. See [#6285](https://github.com/DataDog/integrations-core/pull/6285).

## 1.15.0 / 2020-04-04

* [Added] Upgrade psutil to 5.7.0. See [#6243](https://github.com/DataDog/integrations-core/pull/6243).
* [Fixed] Handle invalid type for excluded_interfaces. See [#5986](https://github.com/DataDog/integrations-core/pull/5986).

## 1.14.0 / 2020-01-13 / Agent 7.17.0

* [Added] Use lazy logging format. See [#5377](https://github.com/DataDog/integrations-core/pull/5377).

## 1.13.0 / 2020-01-02

* [Added] Gracefully handle /proc errors in network check. See [#5245](https://github.com/DataDog/integrations-core/pull/5245).

## 1.12.2 / 2019-12-13 / Agent 7.16.0

* [Fixed] Bump psutil to 5.6.7. See [#5210](https://github.com/DataDog/integrations-core/pull/5210).

## 1.12.1 / 2019-12-02

* [Fixed] Upgrade psutil dependency to 5.6.5. See [#5059](https://github.com/DataDog/integrations-core/pull/5059).

## 1.12.0 / 2019-10-30

* [Added] Add use_sudo option for collecting conntrack metrics with containers. See [#4920](https://github.com/DataDog/integrations-core/pull/4920).
* [Fixed] Fix examples in conf.yaml.default. See [#4887](https://github.com/DataDog/integrations-core/pull/4887). Thanks [q42jaap](https://github.com/q42jaap).

## 1.11.5 / 2019-10-11 / Agent 6.15.0

* [Fixed] Upgrade psutil dependency to 5.6.3. See [#4442](https://github.com/DataDog/integrations-core/pull/4442).

## 1.11.4 / 2019-08-30 / Agent 6.14.0

* [Fixed] Fix metric submission for combined connection state. See [#4473](https://github.com/DataDog/integrations-core/pull/4473).

## 1.11.3 / 2019-08-14

* [Fixed] Drastically reduce `ss` output. See [#4346](https://github.com/DataDog/integrations-core/pull/4346).

## 1.11.1 / 2019-08-02

* [Fixed] Fix proc location for conntrack files. See [#4150](https://github.com/DataDog/integrations-core/pull/4150).

## 1.11.0 / 2019-05-14 / Agent 6.12.0

* [Added] Upgrade psutil dependency to 5.6.2. See [#3684](https://github.com/DataDog/integrations-core/pull/3684).
* [Added] Add conntrack metrics. See [#3624](https://github.com/DataDog/integrations-core/pull/3624).
* [Added] Adhere to code style. See [#3543](https://github.com/DataDog/integrations-core/pull/3543).

## 1.10.0 / 2019-03-29 / Agent 6.11.0

* [Added] Strip white space when reading from proc_conntrack_max_path. See [#3365](https://github.com/DataDog/integrations-core/pull/3365).

## 1.9.0 / 2019-02-18 / Agent 6.10.0

* [Added] Add conntrack basic metrics to the network integration.. See [#2981](https://github.com/DataDog/integrations-core/pull/2981). Thanks [aerostitch](https://github.com/aerostitch).
* [Fixed] Resolve flake8 issues. See [#3060](https://github.com/DataDog/integrations-core/pull/3060).
* [Added] Upgrade psutil. See [#3019](https://github.com/DataDog/integrations-core/pull/3019).
* [Added] Support Python 3. See [#3005](https://github.com/DataDog/integrations-core/pull/3005).
* [Fixed] Use `device` tag instead of the deprecated `device_name` parameter. See [#2945](https://github.com/DataDog/integrations-core/pull/2945). Thanks [aerostitch](https://github.com/aerostitch).

## 1.8.0 / 2018-11-30 / Agent 6.8.0

* [Added] Update psutil. See [#2576][1].
* [Fixed] Use raw string literals when \ is present. See [#2465][2].

## 1.7.0 / 2018-10-12 / Agent 6.6.0

* [Added] Upgrade psutil. See [#2190][3].

## 1.6.1 / 2018-09-04 / Agent 6.5.0

* [Fixed] Retrieve no_proxy directly from the Datadog Agent's configuration. See [#2004][4].
* [Fixed] Add data files to the wheel package. See [#1727][5].

## 1.6.0 / 2018-06-07

* [Added] Add monotonic counts for some metrics. See [#1551][6]. Thanks [jalaziz][7].

## 1.5.0 / 2018-03-23

* [FEATURE] Add custom tag support.

## 1.4.0 / 2018-02-13

* [FEATURE] Get some host network stats when the agent is running inside a container and not in the host network namespace. See [#994][8]

## 1.3.0 / 2017-09-01

* [FEATURE] Collects TCPRetransFail metric from /proc/net/netstat, See [#697][9]

## 1.2.2 / 2017-08-28

* [BUGFIX] Fix incorrect `log.error` call in BSD check. See [#698][10]

## 1.2.1 / 2017-07-18

* [BUGFIX] Fix TCP6 metrics overriding TCP4 metrics when monitoring non combines socket states. See [#501][11]

## 1.2.0 / 2017-06-05

* [FEATURE] Adds metrics from `/proc/net/netstat` in addition to the existing ones from `/proc/net/snmp`. See [#299][12] and [#452][13], thanks [@cory-stripe][14]

## 1.1.0 / 2017-05-03

* [BUGFIX] Work around `ss -atun` bug not differentiating tcp and udp. See [#296][15]

## 1.0.0 / 2017-03-22

* [FEATURE] adds network integration.

<!--- The following link definition list is generated by PimpMyChangelog --->
[1]: https://github.com/DataDog/integrations-core/pull/2576
[2]: https://github.com/DataDog/integrations-core/pull/2465
[3]: https://github.com/DataDog/integrations-core/pull/2190
[4]: https://github.com/DataDog/integrations-core/pull/2004
[5]: https://github.com/DataDog/integrations-core/pull/1727
[6]: https://github.com/DataDog/integrations-core/pull/1551
[7]: https://github.com/jalaziz
[8]: https://github.com/DataDog/integrations-core/pull/994
[9]: https://github.com/DataDog/integrations-core/pull/697
[10]: https://github.com/DataDog/integrations-core/issues/698
[11]: https://github.com/DataDog/integrations-core/issues/501
[12]: https://github.com/DataDog/integrations-core/issues/299
[13]: https://github.com/DataDog/integrations-core/issues/452
[14]: https://github.com/cory-stripe
[15]: https://github.com/DataDog/integrations-core/issues/296
