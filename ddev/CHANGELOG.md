# CHANGELOG - ddev

## 3.1.0 / 2023-06-23

***Added***:

* Update version of datadog-checks-dev. See [#14865](https://github.com/DataDog/integrations-core/pull/14865).
* Add Git utilities. See [#14838](https://github.com/DataDog/integrations-core/pull/14838).
* Add pluggy to ddev dependencies. See [#14821](https://github.com/DataDog/integrations-core/pull/14821).

## 3.0.0 / 2023-06-20

* [Added] Bump the minimum version of datadog-checks-dev. See [#14785](https://github.com/DataDog/integrations-core/pull/14785).
* [Added] Upgrade Pydantic model code generator. See [#14779](https://github.com/DataDog/integrations-core/pull/14779).
* [Added] Use Git for versioning. See [#14778](https://github.com/DataDog/integrations-core/pull/14778).
* [Added] Add validations for removed dependencies. See [#14556](https://github.com/DataDog/integrations-core/pull/14556).
* [Added] Migrate `clean` command. See [#14726](https://github.com/DataDog/integrations-core/pull/14726).
* [Added] Add `release list` command to list integration version releases. See [#14687](https://github.com/DataDog/integrations-core/pull/14687).
* [Added] Migrate command to upgrade Python. See [#14700](https://github.com/DataDog/integrations-core/pull/14700).
* [Fixed] Bump python version from py3.8 to py3.9. See [#14701](https://github.com/DataDog/integrations-core/pull/14701).
* [Changed] Remove `pyperclip` dependency and clipboard functionality. See [#14782](https://github.com/DataDog/integrations-core/pull/14782).

## 2.1.0 / 2023-05-26

* [Added] Add validation for metric limit. See [#14528](https://github.com/DataDog/integrations-core/pull/14528).
* [Fixed] Consider changes to `metadata.csv` as testable. See [#14429](https://github.com/DataDog/integrations-core/pull/14429).
* [Fixed] Account for dependency upgrades in CI matrix logic. See [#14366](https://github.com/DataDog/integrations-core/pull/14366).
* [Fixed] Fix edge case in CI matrix construction. See [#14355](https://github.com/DataDog/integrations-core/pull/14355).

## 2.0.0 / 2023-04-11

* [Changed] Replace flake8 and isort with Ruff. See [#14212](https://github.com/DataDog/integrations-core/pull/14212).

## 1.6.0 / 2023-03-31

* [Added] Add GitHub Actions workflows. See [#14187](https://github.com/DataDog/integrations-core/pull/14187).

## 1.5.0 / 2023-03-23

* [Added] Bump datadog-checks-dev to 18.x. See [#14225](https://github.com/DataDog/integrations-core/pull/14225).

## 1.4.3 / 2023-03-01

* [Fixed] Bump datadog_checks_dev dependency version. See [#14064](https://github.com/DataDog/integrations-core/pull/14064).

## 1.4.2 / 2023-02-27

* [Fixed] Bump datadog_checks_dev dependency version. See [#14040](https://github.com/DataDog/integrations-core/pull/14040).

## 1.4.1 / 2023-01-25

* [Fixed] Pin and bump the datadog_checks_dev version. See [#13557](https://github.com/DataDog/integrations-core/pull/13557).

## 1.4.0 / 2023-01-20

* [Added] Update manifest validation. See [#13637](https://github.com/DataDog/integrations-core/pull/13637).
* [Added] Standardize integration selection. See [#13570](https://github.com/DataDog/integrations-core/pull/13570).
* [Fixed] And fallbacks to some org config options. See [#13629](https://github.com/DataDog/integrations-core/pull/13629).

## 1.3.0 / 2022-12-09

* [Added] Add `validate license-header` subcommand. See [#13417](https://github.com/DataDog/integrations-core/pull/13417).
* [Added] Add JSON Pointer utilities. See [#13464](https://github.com/DataDog/integrations-core/pull/13464).
* [Added] Add utility for displaying warnings and errors. See [#13427](https://github.com/DataDog/integrations-core/pull/13427).
* [Added] Add `config` commands. See [#13412](https://github.com/DataDog/integrations-core/pull/13412).
* [Fixed] Bump datadog_checks_dev dependency to 17.5.0. See [#13490](https://github.com/DataDog/integrations-core/pull/13490).
* [Fixed] Output non-critical information to stderr. See [#13459](https://github.com/DataDog/integrations-core/pull/13459).

## 1.2.0 / 2022-11-23

* [Added] Upgrade dependencies. See [#13375](https://github.com/DataDog/integrations-core/pull/13375).

## 1.1.0 / 2022-10-28

* [Added] Add `status` command. See [#13197](https://github.com/DataDog/integrations-core/pull/13197).
* [Added] Add Git utilities. See [#13185](https://github.com/DataDog/integrations-core/pull/13185).
* [Added] Add utilities for filtering integrations. See [#13156](https://github.com/DataDog/integrations-core/pull/13156).
* [Added] Add more utilities. See [#13136](https://github.com/DataDog/integrations-core/pull/13136).

## 1.0.1 / 2022-09-16

* [Fixed] Fix legacy tooling initialization when using the --here flag. See [#12823](https://github.com/DataDog/integrations-core/pull/12823).

## 1.0.0 / 2022-08-05

* [Added] Make ddev a standalone package. See [#12565](https://github.com/DataDog/integrations-core/pull/12565).

