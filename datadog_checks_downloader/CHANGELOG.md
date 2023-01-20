# CHANGELOG - Datadog Checks Downloader

## 3.10.1 / 2022-12-09

* [Fixed] Update dependencies. See [#13478](https://github.com/DataDog/integrations-core/pull/13478).

## 3.10.0 / 2022-10-28 / Agent 7.41.0

* [Added] Update downloader to use v5 root layout. See [#13174](https://github.com/DataDog/integrations-core/pull/13174).
* [Fixed] Fix setup.py keywords in datadog-checks-downloader. See [#12951](https://github.com/DataDog/integrations-core/pull/12951). Thanks [fridex](https://github.com/fridex).

## 3.9.0 / 2022-09-16 / Agent 7.40.0

* [Added] Add `packaging` to dependencies. See [#12753](https://github.com/DataDog/integrations-core/pull/12753).
* [Fixed] Use packaging instead of pkg_resources for parsing version. See [#12560](https://github.com/DataDog/integrations-core/pull/12560). Thanks [fridex](https://github.com/fridex).

## 3.8.0 / 2022-08-05 / Agent 7.39.0

* [Added] Use context manager when creating temporary directory. See [#12559](https://github.com/DataDog/integrations-core/pull/12559). Thanks [fridex](https://github.com/fridex).
* [Fixed] Prevent from publishing datadog-checks-downloader to PyPI. See [#12556](https://github.com/DataDog/integrations-core/pull/12556).
* [Fixed] Revert #12559 to make it compatible with python2. See [#12647](https://github.com/DataDog/integrations-core/pull/12647).
* [Fixed] Avoid using assert statement by creating UpdatedTargetsError exception. See [#12558](https://github.com/DataDog/integrations-core/pull/12558).
* [Fixed] Adjust logging setup when multiple -v flags are supplied. See [#12562](https://github.com/DataDog/integrations-core/pull/12562). Thanks [fridex](https://github.com/fridex).

## 3.7.0 / 2022-04-11 / Agent 7.36.0

* [Added] Update downloader to use v4 root layout. See [#11779](https://github.com/DataDog/integrations-core/pull/11779).

## 3.6.0 / 2022-02-24 / Agent 7.35.0

* [Added] Add --ignore-python-version flag. See [#11568](https://github.com/DataDog/integrations-core/pull/11568).

## 3.5.0 / 2022-02-19

* [Added] Add `pyproject.toml` file. See [#11305](https://github.com/DataDog/integrations-core/pull/11305).
* [Fixed] Fix namespace packaging on Python 2. See [#11532](https://github.com/DataDog/integrations-core/pull/11532).

## 3.4.1 / 2021-10-19 / Agent 7.32.0

* [Fixed] Update tuf to 0.19.0 for python 3. See [#10444](https://github.com/DataDog/integrations-core/pull/10444).

## 3.4.0 / 2021-07-09 / Agent 7.30.0

* [Added] Upgrade downloader after ceremony. See [#9556](https://github.com/DataDog/integrations-core/pull/9556).

## 3.3.0 / 2021-05-28 / Agent 7.29.0

* [Added] Better error message if the integration doesn't have the expected type. See [#9403](https://github.com/DataDog/integrations-core/pull/9403).

## 3.2.0 / 2020-10-31 / Agent 7.24.0

* [Security] Update TUF, in-toto and securesystemslib. See [#7844](https://github.com/DataDog/integrations-core/pull/7844).

## 3.1.1 / 2020-09-21 / Agent 7.23.0

* [Fixed] Fix style for the latest release of Black. See [#7438](https://github.com/DataDog/integrations-core/pull/7438).

## 3.1.0 / 2020-07-14 / Agent 7.21.1

* [Added] Update to v6 root from @FlorianVeaux. See [#7115](https://github.com/DataDog/integrations-core/pull/7115).
* [Added] Add warning when selecting an extras integration that resides in core. See [#7079](https://github.com/DataDog/integrations-core/pull/7079).
* [Added] Add dependencies to setup.py. See [#7030](https://github.com/DataDog/integrations-core/pull/7030).

## 3.0.0 / 2020-06-18 / Agent 7.21.0

* [Added] Support multiple root layouts. See [#6856](https://github.com/DataDog/integrations-core/pull/6856).

## 2.5.0 / 2020-05-17 / Agent 7.20.0

* [Added] Allow optional dependency installation for all checks. See [#6589](https://github.com/DataDog/integrations-core/pull/6589).

## 2.4.0 / 2020-02-26 / Agent 7.18.0

* [Added] Bump securesystemslib to 0.14.2. See [#5890](https://github.com/DataDog/integrations-core/pull/5890).

## 2.3.1 / 2020-02-24

* [Fixed] Hide internal logging exceptions. See [#5848](https://github.com/DataDog/integrations-core/pull/5848).

## 2.3.0 / 2020-02-22

* [Added] Update in-toto and its deps. See [#5599](https://github.com/DataDog/integrations-core/pull/5599).

## 2.2.0 / 2020-01-10 / Agent 7.17.0

* [Added] Update TUF dependency. See [#5441](https://github.com/DataDog/integrations-core/pull/5441).
* [Added] Use lazy logging format. See [#5398](https://github.com/DataDog/integrations-core/pull/5398).

## 2.1.0 / 2020-01-02

* [Changed] Don't provide a CLI entry point. See [#5374](https://github.com/DataDog/integrations-core/pull/5374).

## 2.0.0 / 2019-12-05 / Agent 7.16.0

* [Fixed] Clean up test artifacts. See [#5129](https://github.com/DataDog/integrations-core/pull/5129).

## 0.7.0 / 2019-12-02

* [Added] Support downloading universal and pure Python wheels. See [#4981](https://github.com/DataDog/integrations-core/pull/4981).

## 0.6.0 / 2019-06-01 / Agent 6.12.0

* [Added] Update downloader to new TUF root v4. See [#3811](https://github.com/DataDog/integrations-core/pull/3811).

## 0.5.0 / 2019-05-14

* [Added] Allow users to override TUF repository URL prefix. See [#3660](https://github.com/DataDog/integrations-core/pull/3660).
* [Added] Adhere to code style. See [#3498](https://github.com/DataDog/integrations-core/pull/3498).

## 0.4.0 / 2019-03-29 / Agent 6.11.0

* [Added] Refactor CLI code. See [#3317](https://github.com/DataDog/integrations-core/pull/3317).
* [Added] Upgrade in-toto. See [#3411](https://github.com/DataDog/integrations-core/pull/3411).
* [Fixed] Never chdir back to a directory we don't control. See [#3282](https://github.com/DataDog/integrations-core/pull/3282).
* [Fixed] Fix pylint. See [#3190](https://github.com/DataDog/integrations-core/pull/3190).

## 0.3.0 / 2019-02-22 / Agent 6.10.0

* [Added] Allow `datadog_checks_downloader` to be securely updated. See [#3184](https://github.com/DataDog/integrations-core/pull/3184).
* [Added] Move exceptions to their own submodule. See [#3180](https://github.com/DataDog/integrations-core/pull/3180).
* [Fixed] Increase requests timeout. See [#3182](https://github.com/DataDog/integrations-core/pull/3182).

## 0.2.0 / 2019-02-20

* [Fixed] Better error message when no such DD package or version. See [#3161](https://github.com/DataDog/integrations-core/pull/3161).
* [Added] Add __main__ module to package. See [#3108](https://github.com/DataDog/integrations-core/pull/3108).
* [Fixed] Use Cloudfront instead of direct-to-S3. See [#3087](https://github.com/DataDog/integrations-core/pull/3087).

## 0.1.0 / 2019-02-05

* [Added] Add datadog-checks-downloader. See [#3026](https://github.com/DataDog/integrations-core/pull/3026).
