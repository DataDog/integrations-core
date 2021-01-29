# CHANGELOG - disk

## 4.1.1 / 2021-01-28

* [Fixed] Fix example config for `create_mounts`. See [#8480](https://github.com/DataDog/integrations-core/pull/8480).

## 4.1.0 / 2021-01-25

* [Added] Support network drives on Windows. See [#8273](https://github.com/DataDog/integrations-core/pull/8273).
* [Added] Add device_label tag in addition to label tag. See [#8306](https://github.com/DataDog/integrations-core/pull/8306).
* [Fixed] Correct default template usage. See [#8233](https://github.com/DataDog/integrations-core/pull/8233).

## 4.0.0 / 2020-10-31 / Agent 7.24.0

* [Changed] Rename whitelist/blacklist to include/exclude. See [#7627](https://github.com/DataDog/integrations-core/pull/7627).

## 3.0.0 / 2020-09-24 / Agent 7.23.0

* [Added] Add options for global exclusion patterns. See [#7648](https://github.com/DataDog/integrations-core/pull/7648).
* [Changed] Ignore `/proc/sys/fs/binfmt_misc` by default. See [#7650](https://github.com/DataDog/integrations-core/pull/7650).

## 2.11.0 / 2020-09-21

* [Added] [disk] Add `include_all_devices` option and improve error logs. See [#7378](https://github.com/DataDog/integrations-core/pull/7378).
* [Added] Upgrade psutil to 5.7.2. See [#7395](https://github.com/DataDog/integrations-core/pull/7395).
* [Fixed] Upgrade isort. See [#7539](https://github.com/DataDog/integrations-core/pull/7539).

## 2.10.1 / 2020-06-11 / Agent 7.21.0

* [Fixed] Rename disk check example config back to .default suffix. See [#6880](https://github.com/DataDog/integrations-core/pull/6880).

## 2.10.0 / 2020-06-09

* [Added] Add disk timeout configuration option. See [#6826](https://github.com/DataDog/integrations-core/pull/6826).

## 2.9.1 / 2020-06-11 / Agent 7.20.1

* [Fixed] Rename disk check example config back to .default suffix. See [#6880](https://github.com/DataDog/integrations-core/pull/6880).

## 2.9.0 / 2020-05-17 / Agent 7.20.0

* [Added] Allow optional dependency installation for all checks. See [#6589](https://github.com/DataDog/integrations-core/pull/6589).
* [Added] Add config spec. See [#6553](https://github.com/DataDog/integrations-core/pull/6553).
* [Added] Add device_name tag. See [#6332](https://github.com/DataDog/integrations-core/pull/6332).

## 2.8.0 / 2020-04-04 / Agent 7.19.0

* [Added] Upgrade psutil to 5.7.0. See [#6243](https://github.com/DataDog/integrations-core/pull/6243).

## 2.7.0 / 2020-02-22 / Agent 7.18.0

* [Added] Read udev disk labels from the blkid cache file. See [#5515](https://github.com/DataDog/integrations-core/pull/5515).

## 2.6.0 / 2020-01-13 / Agent 7.17.0

* [Added] Use lazy logging format. See [#5398](https://github.com/DataDog/integrations-core/pull/5398).
* [Added] Use lazy logging format. See [#5377](https://github.com/DataDog/integrations-core/pull/5377).

## 2.5.3 / 2019-12-13 / Agent 7.16.0

* [Fixed] Bump psutil to 5.6.7. See [#5210](https://github.com/DataDog/integrations-core/pull/5210).

## 2.5.2 / 2019-12-02

* [Fixed] Upgrade psutil dependency to 5.6.5. See [#5059](https://github.com/DataDog/integrations-core/pull/5059).

## 2.5.1 / 2019-10-11 / Agent 6.15.0

* [Fixed] Upgrade psutil dependency to 5.6.3. See [#4442](https://github.com/DataDog/integrations-core/pull/4442).

## 2.5.0 / 2019-08-24 / Agent 6.14.0

* [Added] Remove legacy collection method. See [#4417](https://github.com/DataDog/integrations-core/pull/4417).
* [Added] Add `min_disk_size` option. See [#4317](https://github.com/DataDog/integrations-core/pull/4317).

## 2.4.0 / 2019-07-12 / Agent 6.13.0

* [Added] Remove legacy code. See [#4103](https://github.com/DataDog/integrations-core/pull/4103).

## 2.3.0 / 2019-07-04

* [Added] Add disk label. See [#3953](https://github.com/DataDog/integrations-core/pull/3953).

## 2.2.0 / 2019-05-14 / Agent 6.12.0

* [Added] Upgrade psutil dependency to 5.6.2. See [#3684](https://github.com/DataDog/integrations-core/pull/3684).
* [Added] Adhere to code style. See [#3500](https://github.com/DataDog/integrations-core/pull/3500).

## 2.1.0 / 2019-02-18 / Agent 6.10.0

* [Added] Upgrade psutil. See [#3019](https://github.com/DataDog/integrations-core/pull/3019).
* [Fixed] Use `device` tag instead of the deprecated `device_name` parameter. See [#2946](https://github.com/DataDog/integrations-core/pull/2946). Thanks [aerostitch](https://github.com/aerostitch).

## 2.0.1 / 2019-01-04 / Agent 6.9.0

* [Fixed] Fix regression on agent 5 only. See [#2848][1].

## 2.0.0 / 2018-11-30 / Agent 6.8.0

* [Added] Update psutil. See [#2576][2].
* [Added] Add new filtering options, continue deprecations. See [#2483][3].
* [Changed] Removed deprecated agentConfig option locations. See [#2488][4].
* [Added] Support Python 3. See [#2468][5].
* [Fixed] Use raw string literals when \ is present. See [#2465][6].

## 1.4.0 / 2018-10-12 / Agent 6.6.0

* [Added] Upgrade psutil. See [#2190][7].

## 1.3.0 / 2018-09-04 / Agent 6.5.0

* [Added] Adding optional service_check_rw parameter to check for read-only filesystem. See [#2086][8]. Thanks [bberezov][9].
* [Fixed] Add data files to the wheel package. See [#1727][10].

## 1.2.0 / 2018-03-23

* [FEATURE] Adds custom tag support

## 1.1.0 / 2018-02-13

* [FEATURE] Adds additional device/mount tagging based on regex
* [IMPROVEMENT] Allows disk latency metrics to be collected for non-Windows. See [#1018][11].

## 1.0.2 / 2017-10-10

* [BUGFIX] Skip now works with NFS secure mounts too. See [#470][12].

## 1.0.1 / 2017-07-18

* [SANITY] Import `Platform` helper from `utils.platform` instead of deprecated `util`. See [#484][13]

## 1.0.0 / 2017-03-22

* [FEATURE] adds disk integration.

<!--- The following link definition list is generated by PimpMyChangelog --->
[1]: https://github.com/DataDog/integrations-core/pull/2848
[2]: https://github.com/DataDog/integrations-core/pull/2576
[3]: https://github.com/DataDog/integrations-core/pull/2483
[4]: https://github.com/DataDog/integrations-core/pull/2488
[5]: https://github.com/DataDog/integrations-core/pull/2468
[6]: https://github.com/DataDog/integrations-core/pull/2465
[7]: https://github.com/DataDog/integrations-core/pull/2190
[8]: https://github.com/DataDog/integrations-core/pull/2086
[9]: https://github.com/bberezov
[10]: https://github.com/DataDog/integrations-core/pull/1727
[11]: https://github.com/DataDog/integrations-core/issues/1018
[12]: https://github.com/DataDog/integrations-core/issues/470
[13]: https://github.com/DataDog/integrations-core/issues/484
