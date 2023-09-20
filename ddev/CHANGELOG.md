# CHANGELOG - ddev

## Unreleased

***Fixed***:

* Trigger tests on JMX metrics.yaml updates ([#15877](https://github.com/DataDog/integrations-core/pull/15877))

## 5.1.0 / 2023-09-20

***Added***:

* Add color output to tests in CI ([#15774](https://github.com/DataDog/integrations-core/pull/15774))
* Migrate `ddev dep` to `ddev` ([#15830](https://github.com/DataDog/integrations-core/pull/15830))

***Fixed***:

* Make sure repo override in envvar makes it into config ([#15782](https://github.com/DataDog/integrations-core/pull/15782))
* Bump the `target-version` to python 3.9 for ruff and black ([#15824](https://github.com/DataDog/integrations-core/pull/15824))
* Bump the `datadog-checks-dev` version to ~=25 ([#15823](https://github.com/DataDog/integrations-core/pull/15823))
* Fix the `--compat` option of the `test` command ([#15815](https://github.com/DataDog/integrations-core/pull/15815))

## 5.0.0 / 2023-09-06

***Removed***:

* Remove `release agent requirements` subcommand ([#15621](https://github.com/DataDog/integrations-core/pull/15621))

***Added***:

* Migrate test command ([#15762](https://github.com/DataDog/integrations-core/pull/15762))

***Fixed***:

* Bump datadog-checks-dev version to ~=24.0 ([#15683](https://github.com/DataDog/integrations-core/pull/15683))

## 4.0.1 / 2023-08-25

***Fixed***:

* Support private repositories for changelog errors ([#15685](https://github.com/DataDog/integrations-core/pull/15685))

## 4.0.0 / 2023-08-18

***Added***:

* Migrate `ddev release agent integrations` to `ddev` ([#15569](https://github.com/DataDog/integrations-core/pull/15569))
* Migrate documentation commands to ddev ([#15582](https://github.com/DataDog/integrations-core/pull/15582))
* Migrate `ddev release agent integrations-changelog` to `ddev` ([#15598](https://github.com/DataDog/integrations-core/pull/15598))

***Removed***:

* Remove the `ddev validate recommended-monitors` command ([#15563](https://github.com/DataDog/integrations-core/pull/15563))

## 3.5.0 / 2023-08-11

***Added***:

* Migrate `validate http` to ddev ([#15526](https://github.com/DataDog/integrations-core/pull/15526))
* Migrate `ddev validate licenses` command to ddev ([#15475](https://github.com/DataDog/integrations-core/pull/15475))

***Fixed***:

* Output changelog to stdout instead of stderr on `ddev release agent changelog` ([#15548](https://github.com/DataDog/integrations-core/pull/15548))
* Fix CI validation ([#15560](https://github.com/DataDog/integrations-core/pull/15560))

## 3.4.0 / 2023-08-10

***Added***:

* Add changelog enforcement ([#15459](https://github.com/DataDog/integrations-core/pull/15459))
* Upgrade datadog-checks-dev to 23.0.0 ([#15540](https://github.com/DataDog/integrations-core/pull/15540))

## 3.3.0 / 2023-07-20

***Added***:

* Upgrade datadog-checks-dev to 22.1 ([#15325](https://github.com/DataDog/integrations-core/pull/15325))
* Upgrade click to 8.1.6 ([#15272](https://github.com/DataDog/integrations-core/pull/15272))
* Update generated config models ([#15212](https://github.com/DataDog/integrations-core/pull/15212))

***Fixed***:

* Add logic for integration package files ([#14544](https://github.com/DataDog/integrations-core/pull/14544))
* Add `snmp/data/default_profiles` to matrix TESTABLE_FILE_PATTERN ([#15267](https://github.com/DataDog/integrations-core/pull/15267))

## 3.2.1 / 2023-07-10

***Fixed***:

* Exclude click 8.1.4 to solve mypy issues ([#15201](https://github.com/DataDog/integrations-core/pull/15201))

## 3.2.0 / 2023-07-05

***Added***:

* Bump the minimum supported version of datadog-checks-dev ([#15171](https://github.com/DataDog/integrations-core/pull/15171))
* Move CLI plugins to ddev ([#15166](https://github.com/DataDog/integrations-core/pull/15166))
* Add VerbosityLevels class for ddev cli/terminal use ([#14780](https://github.com/DataDog/integrations-core/pull/14780))
* Add utilities for GitHub ([#15036](https://github.com/DataDog/integrations-core/pull/15036))

## 3.1.0 / 2023-06-23

***Added***:

* Update version of datadog-checks-dev ([#14865](https://github.com/DataDog/integrations-core/pull/14865))
* Add Git utilities ([#14838](https://github.com/DataDog/integrations-core/pull/14838))
* Add pluggy to ddev dependencies ([#14821](https://github.com/DataDog/integrations-core/pull/14821))

## 3.0.0 / 2023-06-20

***Changed***:

* Remove `pyperclip` dependency and clipboard functionality ([#14782](https://github.com/DataDog/integrations-core/pull/14782))

***Added***:

* Bump the minimum version of datadog-checks-dev ([#14785](https://github.com/DataDog/integrations-core/pull/14785))
* Upgrade Pydantic model code generator ([#14779](https://github.com/DataDog/integrations-core/pull/14779))
* Use Git for versioning ([#14778](https://github.com/DataDog/integrations-core/pull/14778))
* Add validations for removed dependencies ([#14556](https://github.com/DataDog/integrations-core/pull/14556))
* Migrate `clean` command ([#14726](https://github.com/DataDog/integrations-core/pull/14726))
* Add `release list` command to list integration version releases ([#14687](https://github.com/DataDog/integrations-core/pull/14687))
* Migrate command to upgrade Python ([#14700](https://github.com/DataDog/integrations-core/pull/14700))

***Fixed***:

* Bump Python version from py3.8 to py3.9 ([#14701](https://github.com/DataDog/integrations-core/pull/14701))

## 2.1.0 / 2023-05-26

***Added***:

* Add validation for metric limit ([#14528](https://github.com/DataDog/integrations-core/pull/14528))

***Fixed***:

* Consider changes to `metadata.csv` as testable ([#14429](https://github.com/DataDog/integrations-core/pull/14429))
* Account for dependency upgrades in CI matrix logic ([#14366](https://github.com/DataDog/integrations-core/pull/14366))
* Fix edge case in CI matrix construction ([#14355](https://github.com/DataDog/integrations-core/pull/14355))

## 2.0.0 / 2023-04-11

***Changed***:

* Replace flake8 and isort with Ruff ([#14212](https://github.com/DataDog/integrations-core/pull/14212))

## 1.6.0 / 2023-03-31

***Added***:

* Add GitHub Actions workflows ([#14187](https://github.com/DataDog/integrations-core/pull/14187))

## 1.5.0 / 2023-03-23

***Added***:

* Bump datadog-checks-dev to 18.x ([#14225](https://github.com/DataDog/integrations-core/pull/14225))

## 1.4.3 / 2023-03-01

***Fixed***:

* Bump datadog_checks_dev dependency version ([#14064](https://github.com/DataDog/integrations-core/pull/14064))

## 1.4.2 / 2023-02-27

***Fixed***:

* Bump datadog_checks_dev dependency version ([#14040](https://github.com/DataDog/integrations-core/pull/14040))

## 1.4.1 / 2023-01-25

***Fixed***:

* Pin and bump the datadog_checks_dev version ([#13557](https://github.com/DataDog/integrations-core/pull/13557))

## 1.4.0 / 2023-01-20

***Added***:

* Update manifest validation ([#13637](https://github.com/DataDog/integrations-core/pull/13637))
* Standardize integration selection ([#13570](https://github.com/DataDog/integrations-core/pull/13570))

***Fixed***:

* And fallbacks to some org config options ([#13629](https://github.com/DataDog/integrations-core/pull/13629))

## 1.3.0 / 2022-12-09

***Added***:

* Add `validate license-header` subcommand ([#13417](https://github.com/DataDog/integrations-core/pull/13417))
* Add JSON Pointer utilities ([#13464](https://github.com/DataDog/integrations-core/pull/13464))
* Add utility for displaying warnings and errors ([#13427](https://github.com/DataDog/integrations-core/pull/13427))
* Add `config` commands ([#13412](https://github.com/DataDog/integrations-core/pull/13412))

***Fixed***:

* Bump datadog_checks_dev dependency to 17.5.0 ([#13490](https://github.com/DataDog/integrations-core/pull/13490))
* Output non-critical information to stderr ([#13459](https://github.com/DataDog/integrations-core/pull/13459))

## 1.2.0 / 2022-11-23

***Added***:

* Upgrade dependencies ([#13375](https://github.com/DataDog/integrations-core/pull/13375))

## 1.1.0 / 2022-10-28

***Added***:

* Add `status` command ([#13197](https://github.com/DataDog/integrations-core/pull/13197))
* Add Git utilities ([#13185](https://github.com/DataDog/integrations-core/pull/13185))
* Add utilities for filtering integrations ([#13156](https://github.com/DataDog/integrations-core/pull/13156))
* Add more utilities ([#13136](https://github.com/DataDog/integrations-core/pull/13136))

## 1.0.1 / 2022-09-16

***Fixed***:

* Fix legacy tooling initialization when using the --here flag ([#12823](https://github.com/DataDog/integrations-core/pull/12823))

## 1.0.0 / 2022-08-05

***Added***:

* Make ddev a standalone package ([#12565](https://github.com/DataDog/integrations-core/pull/12565))
