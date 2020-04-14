# CHANGELOG - hdfs_datanode

## 1.12.1 / 2020-04-04

* [Fixed] Remove logs sourcecategory. See [#6121](https://github.com/DataDog/integrations-core/pull/6121).

## 1.12.0 / 2020-02-22

* [Added] Add log section to hdfs integrations. See [#4632](https://github.com/DataDog/integrations-core/pull/4632).

## 1.11.0 / 2020-01-13

* [Added] Use lazy logging format. See [#5377](https://github.com/DataDog/integrations-core/pull/5377).
* [Added] Collect version metadata for hdfs_datanode. See [#5088](https://github.com/DataDog/integrations-core/pull/5088).

## 1.10.0 / 2019-12-02

* [Added] Add auth type to RequestsWrapper. See [#4708](https://github.com/DataDog/integrations-core/pull/4708).

## 1.9.0 / 2019-10-11

* [Added] Add option to override KRB5CCNAME env var. See [#4578](https://github.com/DataDog/integrations-core/pull/4578).

## 1.8.0 / 2019-07-09

* [Added] Use the new RequestsWrapper for connecting to services. See [#4056](https://github.com/DataDog/integrations-core/pull/4056).

## 1.7.0 / 2019-05-14

* [Added] Adhere to code style. See [#3514](https://github.com/DataDog/integrations-core/pull/3514).

## 1.6.0 / 2019-01-04

* [Added] Support Python 3. See [#2856][1].

## 1.5.0 / 2018-11-14

* [Added] Support keytab files for kerberos. See [#2591][2].

## 1.4.0 / 2018-11-07

* [Added] Support Kerberos auth. See [#2516][3].

## 1.3.1 / 2018-09-04

* [Fixed] Add data files to the wheel package. See [#1727][4].

## 1.3.0 / 2018-06-07

* [Added] Add support for HTTP authentication. See [#1674][5].

## 1.2.0 / 2018-03-23

* [FEATURE] adds custom tag support.

## 1.1.0 / 2018-01-10

* [FEATURE] adds configuration option to ignore SSL validation. See [#714][6]

## 1.0.0 / 2017-03-22

* [FEATURE] adds hdfs_datanode integration.

[1]: https://github.com/DataDog/integrations-core/pull/2856
[2]: https://github.com/DataDog/integrations-core/pull/2591
[3]: https://github.com/DataDog/integrations-core/pull/2516
[4]: https://github.com/DataDog/integrations-core/pull/1727
[5]: https://github.com/DataDog/integrations-core/pull/1674
[6]: https://github.com/DataDog/integrations-core/issues/714
