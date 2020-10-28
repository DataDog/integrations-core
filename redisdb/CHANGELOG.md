# CHANGELOG - redisdb

## 3.1.1 / 2020-09-21 / Agent 7.23.0

* [Fixed] Fix style for the latest release of Black. See [#7438](https://github.com/DataDog/integrations-core/pull/7438).
* [Fixed] Handle redis role missing. See [#7413](https://github.com/DataDog/integrations-core/pull/7413).

## 3.1.0 / 2020-08-10 / Agent 7.22.0

* [Added] Add auto_conf.yaml spec for redisdb. See [#7161](https://github.com/DataDog/integrations-core/pull/7161).
* [Added] Add redis config spec. See [#7091](https://github.com/DataDog/integrations-core/pull/7091).
* [Fixed] Update logs config service field to optional. See [#7209](https://github.com/DataDog/integrations-core/pull/7209).
* [Fixed] Refactor instance argument. See [#7018](https://github.com/DataDog/integrations-core/pull/7018).

## 3.0.0 / 2020-06-29 / Agent 7.21.0

* [Added] Upgrade redis dependency to support `username` in connection strings. See [#6708](https://github.com/DataDog/integrations-core/pull/6708).
* [Fixed] Add flag to enable CLIENT command metrics. See [#6877](https://github.com/DataDog/integrations-core/pull/6877).
* [Changed] Collect port and host from same source in _generate_instance_key. See [#6680](https://github.com/DataDog/integrations-core/pull/6680).

## 2.1.1 / 2020-06-11 / Agent 7.20.2

* [Fixed] Add flag to enable CLIENT command metrics. See [#6877](https://github.com/DataDog/integrations-core/pull/6877).

## 2.1.0 / 2020-05-17 / Agent 7.20.0

* [Added] Allow optional dependency installation for all checks. See [#6589](https://github.com/DataDog/integrations-core/pull/6589).
* [Added] Add 'redis.net.connections' metric to count connections by client. See [#6495](https://github.com/DataDog/integrations-core/pull/6495). Thanks [remicalixte](https://github.com/remicalixte).
* [Fixed] Reduce slow-log log message. See [#6631](https://github.com/DataDog/integrations-core/pull/6631).
* [Fixed] Use agent 6 signature. See [#6424](https://github.com/DataDog/integrations-core/pull/6424).

## 2.0.2 / 2020-04-04 / Agent 7.19.0

* [Fixed] Remove logs sourcecategory. See [#6121](https://github.com/DataDog/integrations-core/pull/6121).

## 2.0.1 / 2020-02-10 / Agent 7.18.0

* [Fixed] Handle error in config_get. See [#5676](https://github.com/DataDog/integrations-core/pull/5676).

## 2.0.0 / 2020-02-05

* [Changed] Submit `redis.key.length` metric regardless of `warn_on_missing_keys`. See [#5591](https://github.com/DataDog/integrations-core/pull/5591).
* [Added] Add aof loading metrics. See [#5431](https://github.com/DataDog/integrations-core/pull/5431). Thanks [tanner-bruce](https://github.com/tanner-bruce).

## 1.15.0 / 2020-01-13 / Agent 7.17.0

* [Added] Use lazy logging format. See [#5398](https://github.com/DataDog/integrations-core/pull/5398).
* [Added] Use lazy logging format. See [#5377](https://github.com/DataDog/integrations-core/pull/5377).
* [Added] Upgrade `redis` to 3.3.11. See [#5150](https://github.com/DataDog/integrations-core/pull/5150).
* [Added] Report maxclients. See [#5207](https://github.com/DataDog/integrations-core/pull/5207). Thanks [jd](https://github.com/jd).

## 1.14.0 / 2019-12-02 / Agent 7.16.0

* [Added] Add active defragmentation gauges. See [#5022](https://github.com/DataDog/integrations-core/pull/5022).
* [Fixed] Fix example keys config. See [#4939](https://github.com/DataDog/integrations-core/pull/4939). Thanks [sileht](https://github.com/sileht).
* [Added] Use a stub class for metadata testing. See [#4919](https://github.com/DataDog/integrations-core/pull/4919).

## 1.13.0 / 2019-10-11 / Agent 6.15.0

* [Added] Submit version metadata. See [#4705](https://github.com/DataDog/integrations-core/pull/4705).

## 1.12.2 / 2019-10-04

* [Fixed] Don't display warning for default keys value. See [#4641](https://github.com/DataDog/integrations-core/pull/4641).

## 1.12.1 / 2019-08-24 / Agent 6.14.0

* [Fixed] Always publish a value for missing keys. See [#4386](https://github.com/DataDog/integrations-core/pull/4386).

## 1.12.0 / 2019-06-01 / Agent 6.12.0

* [Added] Add redis.mem.overhead and redis.mem.startup. See [#3760](https://github.com/DataDog/integrations-core/pull/3760). Thanks [maximebedard](https://github.com/maximebedard).

## 1.11.0 / 2019-05-14

* [Fixed] Adjust latency tracking in redisdb integration. See [#3689](https://github.com/DataDog/integrations-core/pull/3689). Thanks [Firehed](https://github.com/Firehed).
* [Added] Adhere to code style. See [#3562](https://github.com/DataDog/integrations-core/pull/3562).

## 1.10.0 / 2019-02-18 / Agent 6.10.0

* [Added] Add redis_db tag to redis.key.length. See [#3008](https://github.com/DataDog/integrations-core/pull/3008).

## 1.9.0 / 2019-01-22 / Agent 6.9.0

* [Fixed] Only try to decode slowlog command entrypoint. See [#2998][1].
* [Added] Finish Python 3 Support. See [#2951][2].

## 1.8.0 / 2018-11-30 / Agent 6.8.0

* [Added] Support Python 3. See [#2422][3].

## 1.7.1 / 2018-10-12 / Agent 6.6.0

* [Fixed] Handle `host:` command when parsing commandstats output. See [#2356][4].
* [Fixed] Fix multiple db key length. See [#2187][5].

## 1.7.0 / 2018-09-04 / Agent 6.5.0

* [Added] Support finding key lengths on any db. See [#1948][6].
* [Fixed] Add data files to the wheel package. See [#1727][7].

## 1.6.0 / 2018-06-06

* [Added] Add a config option to disable connection cache. See [#1668][8].
* [Added] Package `auto_conf.yaml` for appropriate integrations. See [#1664][9].

## 1.5.0 / 2018-05-11

* [FEATURE] Hardcode the 6379 port in the Autodiscovery template. See [#1444][10] for more information.

## 1.4.0 / 2018-01-10

* [IMPROVEMENT] Keys can be expressed as patterns, see [#300][11]. Thanks [@aliva][12].
* [BUGFIX] Skip non-local keys. See  [#798][13]. Thanks [@chadharvey][14]

## 1.3.0 / 2017-11-21

* [UPDATE] Update auto_conf template to support agent 6 and 5.20+. See [#860][15]

## 1.2.0 / 2017-08-28

* [IMPROVEMENT] Add "redis.net.commands.instantaneous" metric. See [#672][16]
* [IMPROVEMENT] Add "redis.mem.maxmemory" metric. See [#673][17], thanks [@endzyme][18]

## 1.1.0 / 2017-07-18

* [IMPROVEMENT] Add "redis_role:{master,slave}" tag.

## 1.0.0 / 2017-02-22

* [FEATURE] Add redisdb integration.

<!--- The following link definition list is generated by PimpMyChangelog --->
[1]: https://github.com/DataDog/integrations-core/pull/2998
[2]: https://github.com/DataDog/integrations-core/pull/2951
[3]: https://github.com/DataDog/integrations-core/pull/2422
[4]: https://github.com/DataDog/integrations-core/pull/2356
[5]: https://github.com/DataDog/integrations-core/pull/2187
[6]: https://github.com/DataDog/integrations-core/pull/1948
[7]: https://github.com/DataDog/integrations-core/pull/1727
[8]: https://github.com/DataDog/integrations-core/pull/1668
[9]: https://github.com/DataDog/integrations-core/pull/1664
[10]: https://github.com/DataDog/integrations-core/pull/1444
[11]: https://github.com/DataDog/integrations-core/issues/300
[12]: https://github.com/aliva
[13]: https://github.com/DataDog/integrations-core/issues/798
[14]: https://github.com/chadharvey
[15]: https://github.com/DataDog/integrations-core/issues/860
[16]: https://github.com/DataDog/integrations-core/issues/672
[17]: https://github.com/DataDog/integrations-core/issues/673
[18]: https://github.com/endzyme
