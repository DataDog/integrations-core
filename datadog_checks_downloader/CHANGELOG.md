# CHANGELOG - Datadog Checks Downloader

## 2.0.0 / 2019-12-05

* [Fixed] Clean up test artifacts. See [#5129](https://github.com/DataDog/integrations-core/pull/5129).

## 0.7.0 / 2019-12-02

* [Added] Support downloading universal and pure Python wheels. See [#4981](https://github.com/DataDog/integrations-core/pull/4981).

## 0.6.0 / 2019-06-01

* [Added] Update downloader to new TUF root v4. See [#3811](https://github.com/DataDog/integrations-core/pull/3811).

## 0.5.0 / 2019-05-14

* [Added] Allow users to override TUF repository URL prefix. See [#3660](https://github.com/DataDog/integrations-core/pull/3660).
* [Added] Adhere to code style. See [#3498](https://github.com/DataDog/integrations-core/pull/3498).

## 0.4.0 / 2019-03-29

* [Added] Refactor CLI code. See [#3317](https://github.com/DataDog/integrations-core/pull/3317).
* [Added] Upgrade in-toto. See [#3411](https://github.com/DataDog/integrations-core/pull/3411).
* [Fixed] Never chdir back to a directory we don't control. See [#3282](https://github.com/DataDog/integrations-core/pull/3282).
* [Fixed] Fix pylint. See [#3190](https://github.com/DataDog/integrations-core/pull/3190).

## 0.3.0 / 2019-02-22

* [Added] Allow `datadog_checks_downloader` to be securely updated. See [#3184](https://github.com/DataDog/integrations-core/pull/3184).
* [Added] Move exceptions to their own submodule. See [#3180](https://github.com/DataDog/integrations-core/pull/3180).
* [Fixed] Increase requests timeout. See [#3182](https://github.com/DataDog/integrations-core/pull/3182).

## 0.2.0 / 2019-02-20

* [Fixed] Better error message when no such DD package or version. See [#3161](https://github.com/DataDog/integrations-core/pull/3161).
* [Added] Add __main__ module to package. See [#3108](https://github.com/DataDog/integrations-core/pull/3108).
* [Fixed] Use Cloudfront instead of direct-to-S3. See [#3087](https://github.com/DataDog/integrations-core/pull/3087).

## 0.1.0 / 2019-02-05

* [Added] Add datadog-checks-downloader. See [#3026](https://github.com/DataDog/integrations-core/pull/3026).
