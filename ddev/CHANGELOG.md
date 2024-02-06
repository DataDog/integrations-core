# CHANGELOG - ddev

<!-- towncrier release notes start -->

## 8.0.0 / 2024-02-06

***Changed***:

* Bump datadog_checks_dev dependency requirement ([#16806](https://github.com/DataDog/integrations-core/pull/16806))

***Added***:

* Add a `validate labeler` command ([#16774](https://github.com/DataDog/integrations-core/pull/16774))

## 7.0.0 / 2024-01-29

***Changed***:

* Bump the datadog_checks_dev version to 30.x ([#16728](https://github.com/DataDog/integrations-core/pull/16728))

***Fixed***:

* Clarify how to pass arguments to the testing commands ([#16691](https://github.com/DataDog/integrations-core/pull/16691))

## 6.4.0 / 2024-01-23

***Added***:

* Add a script to serve any openmetrics payload for any OM integration ([#16644](https://github.com/DataDog/integrations-core/pull/16644))
* Add the possibility to send specific values in the `generate_metrics` script ([#16672](https://github.com/DataDog/integrations-core/pull/16672))

***Fixed***:

* Fix a bug that prevents to run e2e tests in a non-default repository ([#16671](https://github.com/DataDog/integrations-core/pull/16671))
* Allow CI matrix script to run on apps that lack integration assets. ([#16682](https://github.com/DataDog/integrations-core/pull/16682))
* Prevent `ddev dep` to bump `cryptography` ([#16686](https://github.com/DataDog/integrations-core/pull/16686))
* Prevent `ddev dep` to bump `kubernetes` ([#16687](https://github.com/DataDog/integrations-core/pull/16687))

## 6.3.0 / 2024-01-17

***Added***:

* Add the `minimum-base-package` to all integrations in marketplace's `test-all.yml` file ([#16587](https://github.com/DataDog/integrations-core/pull/16587))

***Fixed***:

* Take into account all the checks when bumping or freezing the dependencies ([#16537](https://github.com/DataDog/integrations-core/pull/16537))
* Allow bumping the version of `psutil` ([#16548](https://github.com/DataDog/integrations-core/pull/16548))
* Allow bumping the version of `openstacksdk` ([#16550](https://github.com/DataDog/integrations-core/pull/16550))
* Allow bumping the version of `pyvmomi` ([#16553](https://github.com/DataDog/integrations-core/pull/16553))
* Allow bumping the version of `pymongo` ([#16555](https://github.com/DataDog/integrations-core/pull/16555))
* Allow bumping the version of `pymsql` ([#16556](https://github.com/DataDog/integrations-core/pull/16556))
* Allow bumping the version of `service-identity` ([#16559](https://github.com/DataDog/integrations-core/pull/16559))
* Use the correct version of Python in the `dep` command ([#16561](https://github.com/DataDog/integrations-core/pull/16561))
* Allow bumping the version of `pycryptodomex` ([#16562](https://github.com/DataDog/integrations-core/pull/16562))
* Allow bumping the version of `protobuf` ([#16575](https://github.com/DataDog/integrations-core/pull/16575))
* Allow bumping the version of `pyodbc` ([#16578](https://github.com/DataDog/integrations-core/pull/16578))

## 6.2.0 / 2024-01-02

***Added***:

* Fetch all the tags before generating the Agent changelog ([#16460](https://github.com/DataDog/integrations-core/pull/16460))
* Add a script to generate all the metrics for a given integration ([#16472](https://github.com/DataDog/integrations-core/pull/16472))

***Fixed***:

* Unpin the `hatch` version ([#16427](https://github.com/DataDog/integrations-core/pull/16427))
* Ignore `rethinkdb` when bumping the deps ([#16449](https://github.com/DataDog/integrations-core/pull/16449))
* Override the default configuration when environment vars are provided in the `env start` command ([#16474](https://github.com/DataDog/integrations-core/pull/16474))
* Update the CHANGELOG file for packages in the `integrations-changelog` command ([#16492](https://github.com/DataDog/integrations-core/pull/16492))
* Bump the `datadog-checks-dev` minimum version to 29.0.1 ([#16506](https://github.com/DataDog/integrations-core/pull/16506))

## 6.1.0 / 2023-12-14

***Added***:

* Bump the Python version from py3.9 to py3.11 ([#15997](https://github.com/DataDog/integrations-core/pull/15997))
* Bump the `datadog_checks_dev` version to 29 ([#16404](https://github.com/DataDog/integrations-core/pull/16404))

***Fixed***:

* Exclude orjson when checking for dependency updates ([#16190](https://github.com/DataDog/integrations-core/pull/16190))
* Exclude psycopg2 when checking for dependency updates ([#16194](https://github.com/DataDog/integrations-core/pull/16194))
* Fix and extend changelog validation:
  - handle invalid change type file extensions
  - handle unnecessary changelog entries
  - fix error message formatting ([#16283](https://github.com/DataDog/integrations-core/pull/16283))
* Take into account logs only integrations when bumping the Python version ([#16303](https://github.com/DataDog/integrations-core/pull/16303))
* Take into account the base check when bumping the dependencies ([#16365](https://github.com/DataDog/integrations-core/pull/16365))
* Pin the `hatch` version to 1.7.0 ([#16405](https://github.com/DataDog/integrations-core/pull/16405))
* Mount the logs volumes inside the agent with the `env start` command ([#16411](https://github.com/DataDog/integrations-core/pull/16411))

## 6.0.2 / 2023-11-10

***Fixed***:

* Add `oracledb` to the ignored dependencies when we bump them before a release ([#16155](https://github.com/DataDog/integrations-core/pull/16155))
* Allow bumping the version of `dnspython` ([#16156](https://github.com/DataDog/integrations-core/pull/16156))
* Add a retry mechanism when pulling the agent docker image ([#16157](https://github.com/DataDog/integrations-core/pull/16157))

## 6.0.1 / 2023-11-02

***Fixed***:

* Fix `ddev env start` to allow the use of stable releases ([#16077](https://github.com/DataDog/integrations-core/pull/16077))
* Stop automatically upgrading `lxml` when bumping the dependencies ([#16112](https://github.com/DataDog/integrations-core/pull/16112))
* Properly show extra output for failed Docker Agent E2E ([#16123](https://github.com/DataDog/integrations-core/pull/16123))
* Do not validate the codecov file in marketplace when running the `validate ci` command ([#16144](https://github.com/DataDog/integrations-core/pull/16144))

## 6.0.0 / 2023-10-26

***Changed***:

* Generate changelogs from fragment files using towncrier.
  There are no changes to the ddev commands, only to their outputs.
  We are making this change to avoid merge conflicts in high-traffic packages where people used to have to modify one CHANGELOG.md file. ([#15983](https://github.com/DataDog/integrations-core/pull/15983))
* Bump datadog_checks_dev dependency to 28.0+. ([#16098](https://github.com/DataDog/integrations-core/pull/16098))

## 5.3.0 / 2023-10-26

***Added***:

* Improve the upgrade-python script ([#16000](https://github.com/DataDog/integrations-core/pull/16000))

***Fixed***:

* Fix `ddev env test` so that tests run for all environments properly when no environment is specified ([#16054](https://github.com/DataDog/integrations-core/pull/16054))
* Fix e2e test env detection to use `platforms`, not `platform` ([#16063](https://github.com/DataDog/integrations-core/pull/16063))
* Include ddev's source code when measuring its coverage ([#16057](https://github.com/DataDog/integrations-core/pull/16057))
* Fix Github API search query ([#15943](https://github.com/DataDog/integrations-core/pull/15943))
* Do not modify the Agent build name if provided by the user when running the e2e environments ([#16052](https://github.com/DataDog/integrations-core/pull/16052))
* Bump the Python version in the dependency provider when bumping the Python version ([#16070](https://github.com/DataDog/integrations-core/pull/16070))

## 5.2.1 / 2023-10-12

***Fixed***:

* Fix environment metadata accessor ([#16009](https://github.com/DataDog/integrations-core/pull/16009))

## 5.2.0 / 2023-10-12

***Added***:

* Migrate E2E features ([#15931](https://github.com/DataDog/integrations-core/pull/15931))
* Bump the minimum supported version of datadog-checks-dev ([#16006](https://github.com/DataDog/integrations-core/pull/16006))

## 5.1.1 / 2023-09-29

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
