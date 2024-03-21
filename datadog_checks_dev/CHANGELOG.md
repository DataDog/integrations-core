# CHANGELOG - Datadog Checks Dev

<!-- towncrier release notes start -->

## 32.0.0 / 2024-03-21

***Removed***:

* Remove commands that are migrated to the new `ddev` CLI. ([#17008](https://github.com/DataDog/integrations-core/pull/17008)), ([#16995](https://github.com/DataDog/integrations-core/pull/16995))

***Added***:

* Update the configuration file to include the new oauth options parameter. ([#16835](https://github.com/DataDog/integrations-core/pull/16835))
* Add a method to get the service check defined in the `service_checks.json` file for an integration. ([#16916](https://github.com/DataDog/integrations-core/pull/16916))
* update custom_queries configuration to support optional collection_interval. ([#16957](https://github.com/DataDog/integrations-core/pull/16957))
* Add utility function to assert service checks. ([#17071](https://github.com/DataDog/integrations-core/pull/17071))
* Added a check to the `ddev validate codeowners` to make sure that logs assets are owned by `@DatadDog/logs-backend`. ([#17185](https://github.com/DataDog/integrations-core/pull/17185))
* Allow the codeowners validation in integrations-core. ([#17199](https://github.com/DataDog/integrations-core/pull/17199))

***Fixed***:

* [ecos 1214] Remove old unused oauth manifest field. ([#16873](https://github.com/DataDog/integrations-core/pull/16873))
* Starting version in templates aligns with changelog type. ([#16917](https://github.com/DataDog/integrations-core/pull/16917))
* Bump the required python version in the integration templates. ([#16972](https://github.com/DataDog/integrations-core/pull/16972))
* Explicitly list `localhost` as the address when port-forwarding with kind to avoid opening a pop-up. ([#17016](https://github.com/DataDog/integrations-core/pull/17016))
* Pin pytest to fix `flaky` issues. ([#17042](https://github.com/DataDog/integrations-core/pull/17042))
* Update the configuration to include the `metric_prefix` option. ([#17065](https://github.com/DataDog/integrations-core/pull/17065))
* Print the info logs in the correct order in the `validate models -s` command. ([#17066](https://github.com/DataDog/integrations-core/pull/17066))
* Don't crash when integration configuration spec is missing default templates. ([#17214](https://github.com/DataDog/integrations-core/pull/17214))

## 31.0.0 / 2024-02-06

***Changed***:

* Rename template for new crawler integration. ([#16802](https://github.com/DataDog/integrations-core/pull/16802))

***Fixed***:

* Do not sign `ddev` after the release ([#16737](https://github.com/DataDog/integrations-core/pull/16737))
* Remove unsupported characters from README templates. ([#16759](https://github.com/DataDog/integrations-core/pull/16759))

## 30.0.0 / 2024-01-29

***Changed***:

* Remove legacy tox plugin ([#16696](https://github.com/DataDog/integrations-core/pull/16696))

***Added***:

* Bump towncrier version to support releasing with empty changelogs ([#16676](https://github.com/DataDog/integrations-core/pull/16676))
* Different changelog template depending on release process. Marketplace and Extras changelogs are static, integrations-core changelogs have towncrier header. ([#16693](https://github.com/DataDog/integrations-core/pull/16693))

***Fixed***:

* Pin black ([#16712](https://github.com/DataDog/integrations-core/pull/16712))
* Bump pytest-asyncio to be compatible with pytest 8 ([#16726](https://github.com/DataDog/integrations-core/pull/16726))

## 29.2.0 / 2024-01-22

***Added***:

* Set auto_install in 'manifest.json' when running 'ddev create' ([#16647](https://github.com/DataDog/integrations-core/pull/16647))

## 29.1.0 / 2024-01-17

***Added***:

* Autogenerate source_type_id in 'manifest.json' when running 'ddev create' ([#16544](https://github.com/DataDog/integrations-core/pull/16544))

***Fixed***:

* Fix a bug that prevents the `validate dep` command to fail if extra deps are found in the Agent file ([#16541](https://github.com/DataDog/integrations-core/pull/16541))

## 29.0.2 / 2024-01-09

***Fixed***:

* * Extend messages from dependency validation.
      1. Say which ddev command to run to fix particular type of error.
      2. Report success at the end. ([#15558](https://github.com/DataDog/integrations-core/pull/15558))
* Pin the `pytest-asyncio` version to 0.23.2 ([#16507](https://github.com/DataDog/integrations-core/pull/16507))
* Remove setuptools depedency for jmx and logs integrations. Make them consistent with the `check` template. ([#16527](https://github.com/DataDog/integrations-core/pull/16527))
* Update the template for logs integrations to not require a specific Python and base check version ([#16528](https://github.com/DataDog/integrations-core/pull/16528))

## 29.0.1 / 2024-01-02

***Fixed***:

* Set the Python version back to 3.9 in the templates ([#16504](https://github.com/DataDog/integrations-core/pull/16504))

## 29.0.0 / 2023-12-12

***Removed***:

* Remove pyro4 and serpent dependencies ([#16269](https://github.com/DataDog/integrations-core/pull/16269))

***Added***:

* Bump the Python version from py3.9 to py3.11 ([#15997](https://github.com/DataDog/integrations-core/pull/15997))
* Make the `spec.yaml` file mandatory in integrations-core if there are configuration files ([#16345](https://github.com/DataDog/integrations-core/pull/16345))

***Fixed***:

* Make the `config_models` files mandatory in integrations-core ([#16311](https://github.com/DataDog/integrations-core/pull/16311))

## 28.0.1 / 2023-11-10

***Fixed***:

* Exclude orjson when checking for dependency updates. ([#16166](https://github.com/DataDog/integrations-core/pull/16166))

## 28.0.0 / 2023-10-26

***Changed***:

* Generate changelogs from fragment files using towncrier.
  There are no changes to the ddev commands, only to their outputs.
  We are making this change to avoid merge conflicts in high-traffic packages where people used to have to modify one CHANGELOG.md file. ([#15983](https://github.com/DataDog/integrations-core/pull/15983))

## 27.0.1 / 2023-10-26

***Fixed***:

* Align package version in integration template with changelog. ([#16029](https://github.com/DataDog/integrations-core/pull/16029))
* Allow bumping the version of `pyodbc` ([#16030](https://github.com/DataDog/integrations-core/pull/16030))
* Display changes on `ddev show changes` when changes are found ([#16045](https://github.com/DataDog/integrations-core/pull/16045))
* Allow bumping the version of `pymysql` ([#16043](https://github.com/DataDog/integrations-core/pull/16043))
* Remove the `setup.py` file from the new integration template ([#16072](https://github.com/DataDog/integrations-core/pull/16072))

## 27.0.0 / 2023-10-12

***Changed***:

* Migrate E2E features ([#15931](https://github.com/DataDog/integrations-core/pull/15931))

## 26.0.1 / 2023-10-11

***Fixed***:

* Fix the manifest template file ([#15984](https://github.com/DataDog/integrations-core/pull/15984))

## 26.0.0 / 2023-10-02

***Changed***:

* Update eula validation to only occur if it is present in the manifest for marketplace prs to support private-offer-only listings ([#15935](https://github.com/DataDog/integrations-core/pull/15935))

## 25.1.2 / 2023-09-26

***Fixed***:

* Fix test output rewrite conditional ([#15915](https://github.com/DataDog/integrations-core/pull/15915))

## 25.1.1 / 2023-09-26

***Fixed***:

* Exclude psycopg2 from automatic upgrades ([#15864](https://github.com/DataDog/integrations-core/pull/15864))
* Upper-bound pydantic to quickly fix CI while we investigate what in the latest version breaks us. ([#15901](https://github.com/DataDog/integrations-core/pull/15901))
* Finalize pytest plugin logic for E2E refactor ([#15898](https://github.com/DataDog/integrations-core/pull/15898))
* Fix `ddev release make all` so that it won't stop on the first unchanged integration ([#15932](https://github.com/DataDog/integrations-core/pull/15932))

## 25.1.0 / 2023-09-15

***Added***:

* Added overview examples to the readme file ([#15817](https://github.com/DataDog/integrations-core/pull/15817))
* Added required classifier tag examples to template ([#15828](https://github.com/DataDog/integrations-core/pull/15828))
* Prepare E2E tooling for better message passing ([#15843](https://github.com/DataDog/integrations-core/pull/15843))

## 25.0.0 / 2023-09-13

***Changed***:

* Include support for `domain_regex` when validating JMX metric files ([#15761](https://github.com/DataDog/integrations-core/pull/15761))
* Adjust template and test collection based on new team guidelines ([#15078](https://github.com/DataDog/integrations-core/pull/15078))
    * `ddev create` produces initial test file named `test_unit.py` instead of `test_<integration>.py`.
    * Our pytest collection plugin attaches labels to tests based on their location. E.g. all tests in `test_unit.py` get the `unit` label.

***Added***:

* Add short hand for force-env-rebuild ([#15716](https://github.com/DataDog/integrations-core/pull/15716))

***Fixed***:

* Allow bumping the version of clickhouse-driver ([#15745](https://github.com/DataDog/integrations-core/pull/15745))
* Allow bumping the version of lz4 ([#15747](https://github.com/DataDog/integrations-core/pull/15747))
* Remove flup from the dependency bump exclusion list ([#15748](https://github.com/DataDog/integrations-core/pull/15748))
* Remove setuptools from the build-system for new integrations ([#15766](https://github.com/DataDog/integrations-core/pull/15766))
* Stop using the old GPG_COMMAND constant from securesystemslib ([#15776](https://github.com/DataDog/integrations-core/pull/15776))
* Override the default test options for some integrations ([#15779](https://github.com/DataDog/integrations-core/pull/15779))

## 24.1.0 / 2023-08-25

***Security***:

* Update security dependencies ([#15667](https://github.com/DataDog/integrations-core/pull/15667))
  * in-toto: 2.0.0
  * securesystemslib: 0.28.0

## 24.0.0 / 2023-08-18

***Removed***:

* Migrate `validate http` to ddev ([#15526](https://github.com/DataDog/integrations-core/pull/15526))
* Remove the `ddev validate recommended-monitors` command ([#15563](https://github.com/DataDog/integrations-core/pull/15563))
* Remove files in datadog_checks_dev for `validate ci, http, and metadata` ([#15546](https://github.com/DataDog/integrations-core/pull/15546))
* Migrate documentation commands to ddev ([#15582](https://github.com/DataDog/integrations-core/pull/15582))

***Added***:

* Print the metric list when parsing a Prometheus endpoint ([#15586](https://github.com/DataDog/integrations-core/pull/15586))
* Update dependencies for Agent 7.48 ([#15585](https://github.com/DataDog/integrations-core/pull/15585))

***Fixed***:

* Ignore `pydantic` when bumping the dependencies ([#15597](https://github.com/DataDog/integrations-core/pull/15597))
* Stop using the TOX_ENV_NAME variable ([#15528](https://github.com/DataDog/integrations-core/pull/15528))
* Prevent `command already in progress` errors in the Postgres integration ([#15489](https://github.com/DataDog/integrations-core/pull/15489))

## 23.0.0 / 2023-08-10

***Changed***:

* New changelog generation ([#15378](https://github.com/DataDog/integrations-core/pull/15378))

## 22.1.2 / 2023-08-10

***Fixed***:

* Bump datamodel-code-generator to address pydantic deprecations ([#15521](https://github.com/DataDog/integrations-core/pull/15521))

## 22.1.1 / 2023-08-08

***Fixed***:

* Change equality requirement to subset in dependency validation ([#15490](https://github.com/DataDog/integrations-core/pull/15490))
* Upgrade postgres check to psycopg3 ([#15411](https://github.com/DataDog/integrations-core/pull/15411))
* Bump the min base check version in the templates to 32.6.0 ([#15442](https://github.com/DataDog/integrations-core/pull/15442))
* Update formatting of changelog templates ([#15434](https://github.com/DataDog/integrations-core/pull/15434))
* Improvements on dependency validation ([#15416](https://github.com/DataDog/integrations-core/pull/15416))
* Fix types for generated config models ([#15334](https://github.com/DataDog/integrations-core/pull/15334))
* Remove `legal_email` field from Ecosystem template ([#15379](https://github.com/DataDog/integrations-core/pull/15379))
* Add new release notes below the Unreleased section of changelogs ([#15332](https://github.com/DataDog/integrations-core/pull/15332))

## 22.1.0 / 2023-07-20

***Added***:

* Upgrade click to 8.1.6 ([#15272](https://github.com/DataDog/integrations-core/pull/15272))
* Update generated config models ([#15212](https://github.com/DataDog/integrations-core/pull/15212))
* Prometheus parsing commands accept files in addition to endpoints ([#15071](https://github.com/DataDog/integrations-core/pull/15071))

***Fixed***:

* Do not attempt to upgrade dependencies that break our tests ([#15226](https://github.com/DataDog/integrations-core/pull/15226))
* Fix formatting of list in click command help string ([#15240](https://github.com/DataDog/integrations-core/pull/15240))

## 22.0.1 / 2023-07-10

***Fixed***:

* Exclude click 8.1.4 to solve mypy issues ([#15201](https://github.com/DataDog/integrations-core/pull/15201))
* Bump the minimal base check version in the integration templates ([#15178](https://github.com/DataDog/integrations-core/pull/15178))

## 22.0.0 / 2023-07-05

***Changed***:

* Move CLI plugins to ddev ([#15166](https://github.com/DataDog/integrations-core/pull/15166))

***Added***:

* Add step unit to metadata check ([#14862](https://github.com/DataDog/integrations-core/pull/14862))

***Fixed***:

* Update a log message to mention `hatch` instead of `tox` ([#15037](https://github.com/DataDog/integrations-core/pull/15037))

## 21.0.0 / 2023-06-22

***Removed***:

* Remove ddev script from datadog_checks_dev ([#14837](https://github.com/DataDog/integrations-core/pull/14837))

***Changed***:

* Reorder changelogs by priority ([#14836](https://github.com/DataDog/integrations-core/pull/14836))

***Added***:

* Update changelog generation to use a better formatting ([#14810](https://github.com/DataDog/integrations-core/pull/14810))

***Fixed***:

* Revert "Set the `marker` option to `not e2e` by default (#14804)" ([#14815](https://github.com/DataDog/integrations-core/pull/14815))
* Set the `marker` option to `not e2e` by default ([#14804](https://github.com/DataDog/integrations-core/pull/14804))

## 20.0.1 / 2023-06-20

***Fixed***:

* Fix ability to release ddev ([#14790](https://github.com/DataDog/integrations-core/pull/14790))

## 20.0.0 / 2023-06-16

***Changed***:

* Remove `pyperclip` dependency and clipboard functionality ([#14782](https://github.com/DataDog/integrations-core/pull/14782))

***Added***:

* Upgrade Pydantic model code generator ([#14779](https://github.com/DataDog/integrations-core/pull/14779))
* Add validations for removed dependencies ([#14556](https://github.com/DataDog/integrations-core/pull/14556))

***Fixed***:

* Update the expvar port and enable telemetry ([#14729](https://github.com/DataDog/integrations-core/pull/14729))

## 19.4.1 / 2023-06-08

***Fixed***:

* Revert "Capture stderr from docker compose to improve debugging experience" (#13949) ([#14714](https://github.com/DataDog/integrations-core/pull/14714))
* Bump Python version from py3.8 to py3.9 ([#14701](https://github.com/DataDog/integrations-core/pull/14701))
* Allow typed-ast to work for python3.11 ([#14689](https://github.com/DataDog/integrations-core/pull/14689))
* Rephrase the `--dev` description for the `start` command ([#14681](https://github.com/DataDog/integrations-core/pull/14681))

## 19.4.0 / 2023-06-06

***Added***:

* Update minimum base check version for templates ([#14643](https://github.com/DataDog/integrations-core/pull/14643))

***Fixed***:

* Keep pydantic version synced ([#14656](https://github.com/DataDog/integrations-core/pull/14656))
* Fix `generate-profile-from-mibs` ([#14676](https://github.com/DataDog/integrations-core/pull/14676))

## 19.3.1 / 2023-05-26

***Fixed***:

* Update dependencies ([#14594](https://github.com/DataDog/integrations-core/pull/14594))

## 19.3.0 / 2023-05-17

***Added***:

* Add `token` and `alert` as valid metric units ([#14575](https://github.com/DataDog/integrations-core/pull/14575))
* Add an ignore_connection_errors option to the openmetrics check ([#14504](https://github.com/DataDog/integrations-core/pull/14504))

***Fixed***:

* Fix format-style command when test custom_integration for tox ([#14547](https://github.com/DataDog/integrations-core/pull/14547)) Thanks [FeruBaco](https://github.com/FeruBaco).
* Remove unnecesary commas after type definition ([#14529](https://github.com/DataDog/integrations-core/pull/14529)) Thanks [FeruBaco](https://github.com/FeruBaco).
* Capture stderr from docker compose to improve debugging experience ([#13949](https://github.com/DataDog/integrations-core/pull/13949))

## 19.2.0 / 2023-04-27

***Added***:

* Remove Azure Pipelines from validation ([#14475](https://github.com/DataDog/integrations-core/pull/14475))

***Fixed***:

* Deprecate `use_latest_spec` option ([#14446](https://github.com/DataDog/integrations-core/pull/14446))
* Drop some kafka_consumer old dependencies from the `licenses` command ([#14244](https://github.com/DataDog/integrations-core/pull/14244))

## 19.1.0 / 2023-04-20

***Added***:

* Introduce initial entry in CHANGELOG during ddev create ([#14148](https://github.com/DataDog/integrations-core/pull/14148))

***Fixed***:

* Limit the version of `virtualenv` to continue testing Python 2 ([#14431](https://github.com/DataDog/integrations-core/pull/14431))
* Make license validation deterministic wrt dependency specification ([#14354](https://github.com/DataDog/integrations-core/pull/14354))

## 19.0.0 / 2023-04-11

***Changed***:

* Replace flake8 and isort with Ruff ([#14212](https://github.com/DataDog/integrations-core/pull/14212))

## 18.1.0 / 2023-03-31

***Added***:

* Get more insight into Agent E2E communication errors ([#14259](https://github.com/DataDog/integrations-core/pull/14259))
* Support GitHub Actions for testing ([#14237](https://github.com/DataDog/integrations-core/pull/14237))

***Fixed***:

* Fix a typo in the `disable_generic_tags` option description ([#14246](https://github.com/DataDog/integrations-core/pull/14246))
* Fix style ([#14230](https://github.com/DataDog/integrations-core/pull/14230))
* Fix traps db generation for expended representation ([#14002](https://github.com/DataDog/integrations-core/pull/14002))

## 18.0.0 / 2023-03-23

***Changed***:

* Upgrade openstacksdk dependency and drop py2 ([#14109](https://github.com/DataDog/integrations-core/pull/14109))

***Added***:

* Allow to specify the mode when creating a temp dir ([#14208](https://github.com/DataDog/integrations-core/pull/14208))
* Allow enabling of tracing for tests with an environment variable ([#14206](https://github.com/DataDog/integrations-core/pull/14206))
* Move CI setup scripts to a provider-agnostic location ([#14179](https://github.com/DataDog/integrations-core/pull/14179))

***Fixed***:

* Skip metadata validation for non-metrics integrations ([#14211](https://github.com/DataDog/integrations-core/pull/14211))
* Consider empty environment variables as unset ([#14210](https://github.com/DataDog/integrations-core/pull/14210))
* Fix `generate-traps-db` command on windows ([#14117](https://github.com/DataDog/integrations-core/pull/14117))

## 17.9.0 / 2023-03-01

***Added***:

* Add process and runtime to allowed prefixes ([#14058](https://github.com/DataDog/integrations-core/pull/14058))

***Fixed***:

* Fix dependency update logic for latest versions of `packaging` ([#14055](https://github.com/DataDog/integrations-core/pull/14055))

## 17.8.2 / 2023-02-27

***Fixed***:

* Update cryptography to 39.0.1 ([#13913](https://github.com/DataDog/integrations-core/pull/13913))
* Remove autodiscovery category from the SNMP template ([#13924](https://github.com/DataDog/integrations-core/pull/13924))
* Remove py2 from the default template ([#13838](https://github.com/DataDog/integrations-core/pull/13838))

## 17.8.1 / 2023-01-25

***Fixed***:

* Call hatch from `sys.executable` ([#13769](https://github.com/DataDog/integrations-core/pull/13769))
* Bump pydantic version to 1.10.4 ([#13764](https://github.com/DataDog/integrations-core/pull/13764))

## 17.8.0 / 2023-01-20

***Added***:

* Update style deps ([#13740](https://github.com/DataDog/integrations-core/pull/13740))

***Fixed***:

* Fix `ddev make release` when the `version` parameter is not provided ([#13717](https://github.com/DataDog/integrations-core/pull/13717))
* Improve startup time and fix some tests ([#13703](https://github.com/DataDog/integrations-core/pull/13703))
* Validate the new release version when provided ([#13687](https://github.com/DataDog/integrations-core/pull/13687))
* Always recreate the containers when using docker-compose in tests ([#13685](https://github.com/DataDog/integrations-core/pull/13685))
* Automatically delete the agent container when the container is stopped ([#13675](https://github.com/DataDog/integrations-core/pull/13675))
* Support license header validation for files encoded with utf8 with bom ([#13676](https://github.com/DataDog/integrations-core/pull/13676))
* Stop ignoring the `protobuf` dependency when updating them ([#13642](https://github.com/DataDog/integrations-core/pull/13642))
* Skip yanked artifacts from PyPi ([#13632](https://github.com/DataDog/integrations-core/pull/13632))
* Update the hatch env selection to act as the tox one ([#13644](https://github.com/DataDog/integrations-core/pull/13644))
* Rename TOX_SKIP_ENV to SKIP_ENV_NAME ([#13633](https://github.com/DataDog/integrations-core/pull/13633))

## 17.7.0 / 2022-12-27

***Added***:

* Add hidden option to ignore manifest schema validation ([#13569](https://github.com/DataDog/integrations-core/pull/13569))
* Add `--fix` flag to `ddev validate license-headers` for automatically fixing errors ([#13507](https://github.com/DataDog/integrations-core/pull/13507))

***Fixed***:

* Properly account for other integration repos ([#13581](https://github.com/DataDog/integrations-core/pull/13581))
* Make `ddev validate license-header` honor gitignore files ([#13439](https://github.com/DataDog/integrations-core/pull/13439))
* Fix style ([#13518](https://github.com/DataDog/integrations-core/pull/13518))

## 17.6.0 / 2022-12-13

***Added***:

* Update marketplace GitHub actions to validate new template fields ([#13267](https://github.com/DataDog/integrations-core/pull/13267))

***Fixed***:

* Fix style deps ([#13495](https://github.com/DataDog/integrations-core/pull/13495))
* Update integrations repo name ([#13494](https://github.com/DataDog/integrations-core/pull/13494))

## 17.5.1 / 2022-12-09

***Fixed***:

* Update dependencies ([#13478](https://github.com/DataDog/integrations-core/pull/13478))

## 17.5.0 / 2022-12-09

***Added***:

* Add `validate license-header` subcommand ([#13417](https://github.com/DataDog/integrations-core/pull/13417))
* Add new template for metrics crawler integrations ([#13411](https://github.com/DataDog/integrations-core/pull/13411))
* Add an option to ignore failed environments in env start ([#13443](https://github.com/DataDog/integrations-core/pull/13443))

***Fixed***:

* Fix parsing of E2E output for Hatch environments when warnings occur ([#13479](https://github.com/DataDog/integrations-core/pull/13479))
* Force the semver version to >=2.13.0 ([#13477](https://github.com/DataDog/integrations-core/pull/13477))
* Re-raise the exception when the environment failed to start ([#13472](https://github.com/DataDog/integrations-core/pull/13472))
* Remove the `--memray-show-report` option ([#13463](https://github.com/DataDog/integrations-core/pull/13463))
* Bump pytest-memray version ([#13462](https://github.com/DataDog/integrations-core/pull/13462))
* Do not force pytest version ([#13461](https://github.com/DataDog/integrations-core/pull/13461))
* Fix typo in platfrom-integrations team name ([#13368](https://github.com/DataDog/integrations-core/pull/13368))

## 17.4.0 / 2022-11-23

***Added***:

* Add a dummy `--memray` option to the pytest plugin ([#13352](https://github.com/DataDog/integrations-core/pull/13352))
* Add a dummy `--hide-memray-summary` option to the pytest plugin ([#13358](https://github.com/DataDog/integrations-core/pull/13358))
* Add an option to show the memray report ([#13351](https://github.com/DataDog/integrations-core/pull/13351))

***Fixed***:

* Support isolated installation ([#13366](https://github.com/DataDog/integrations-core/pull/13366))
* Allow `bench` as an env name for running benchmarks with hatch ([#13316](https://github.com/DataDog/integrations-core/pull/13316))
* Consider `hatch.toml` file in testable files for PR tests to run ([#13303](https://github.com/DataDog/integrations-core/pull/13303))

## 17.3.2 / 2022-11-08

***Fixed***:

* Update marketplace README template ([#13249](https://github.com/DataDog/integrations-core/pull/13249))
* [cli] Expand help text for --dev and --base options ([#13235](https://github.com/DataDog/integrations-core/pull/13235))
* Add the CHANGELOG.md template file to the new integration scaffolds ([#13257](https://github.com/DataDog/integrations-core/pull/13257))

## 17.3.1 / 2022-10-28

***Fixed***:

* Fix process signature report ([#13226](https://github.com/DataDog/integrations-core/pull/13226))

## 17.3.0 / 2022-10-26

***Added***:

* Add the memray option to the `test` command ([#13160](https://github.com/DataDog/integrations-core/pull/13160))

***Fixed***:

* Rename Tools and Libs team to Platform Integrations ([#13201](https://github.com/DataDog/integrations-core/pull/13201))
* Force pytest<7.2.0 to avoid test breakage ([#13198](https://github.com/DataDog/integrations-core/pull/13198))

## 17.2.0 / 2022-10-20

***Added***:

* Add the ability to retry kind environments ([#13106](https://github.com/DataDog/integrations-core/pull/13106))

***Fixed***:

* Add f5-distributed-cloud as tile without github team or username ([#13149](https://github.com/DataDog/integrations-core/pull/13149))
* Fix `release make` to include new integrations in the agent requirements file ([#13125](https://github.com/DataDog/integrations-core/pull/13125))
* Fix deprecation warnings with `semver` ([#12967](https://github.com/DataDog/integrations-core/pull/12967))
* Stop running `codecov` in the `test` command for integrations-core ([#13085](https://github.com/DataDog/integrations-core/pull/13085))

## 17.1.1 / 2022-10-14

***Fixed***:

* Allow 1e to have email-based codeowners ([#13121](https://github.com/DataDog/integrations-core/pull/13121))
* Remove the legacy docker-compose ([#13073](https://github.com/DataDog/integrations-core/pull/13073))
* Use specific endpoint to get all members from trello board at once ([#13074](https://github.com/DataDog/integrations-core/pull/13074))
* Make the `validate metadata` command fail if the metric prefix is invalid ([#12903](https://github.com/DataDog/integrations-core/pull/12903))
* Pin security deps in ddev ([#12956](https://github.com/DataDog/integrations-core/pull/12956))
* Fixed `validate manifest` command by providing default config for `dd_url` setting ([#13057](https://github.com/DataDog/integrations-core/pull/13057))

## 17.1.0 / 2022-10-04

***Added***:

* Support new `integrations` repo ([#13007](https://github.com/DataDog/integrations-core/pull/13007))

***Fixed***:

* Allow creating integrations with `--here` in an arbitrary folder ([#13026](https://github.com/DataDog/integrations-core/pull/13026))
* Do not include `ddev` in the `requirements-agent-release.txt` file ([#12947](https://github.com/DataDog/integrations-core/pull/12947))
* Avoid assigning QA cards to the main reviewers ([#12990](https://github.com/DataDog/integrations-core/pull/12990))

## 17.0.1 / 2022-09-19

***Fixed***:

* Do not fail the validation if `pr_labels_config_relative_path` is not defined ([#12965](https://github.com/DataDog/integrations-core/pull/12965))

## 17.0.0 / 2022-09-16

***Changed***:

* Use official labeler GH action ([#12546](https://github.com/DataDog/integrations-core/pull/12546))

***Added***:

* Refactor tooling for getting the current env name ([#12939](https://github.com/DataDog/integrations-core/pull/12939))
* Attempts default to 2 on ci ([#12867](https://github.com/DataDog/integrations-core/pull/12867))
* Update HTTP config spec templates ([#12890](https://github.com/DataDog/integrations-core/pull/12890))
* Add OAuth functionality to the HTTP util ([#12884](https://github.com/DataDog/integrations-core/pull/12884))
* Upgrade Hatch ([#12872](https://github.com/DataDog/integrations-core/pull/12872))
* Validate the `changelog` field in the manifest file ([#12829](https://github.com/DataDog/integrations-core/pull/12829))
* Upgrade dependencies for environment management ([#12785](https://github.com/DataDog/integrations-core/pull/12785))
* Make sure process_signatures gets migrated during V2 migrations ([#12589](https://github.com/DataDog/integrations-core/pull/12589))
* Enforce version 2 of manifests ([#12775](https://github.com/DataDog/integrations-core/pull/12775))
* Update templates for new integrations ([#12744](https://github.com/DataDog/integrations-core/pull/12744))
* Update new integration templates to use v2 manifests ([#12592](https://github.com/DataDog/integrations-core/pull/12592))

***Fixed***:

* Templatize the repository in the README links ([#12930](https://github.com/DataDog/integrations-core/pull/12930))
* Fix tile-only README template generation ([#12918](https://github.com/DataDog/integrations-core/pull/12918))
* Add case sensitive changelog validation ([#12920](https://github.com/DataDog/integrations-core/pull/12920))
* Add a validator for the manifest version ([#12788](https://github.com/DataDog/integrations-core/pull/12788))
* Make the manifest validation fail if the file is not found ([#12789](https://github.com/DataDog/integrations-core/pull/12789))
* Fix Hatch environment plugin ([#12769](https://github.com/DataDog/integrations-core/pull/12769))
* Templatize the README links ([#12742](https://github.com/DataDog/integrations-core/pull/12742))
* Bump dependencies for 7.40 ([#12896](https://github.com/DataDog/integrations-core/pull/12896))

## 16.7.0 / 2022-08-05

***Added***:

* Make ddev a standalone package ([#12565](https://github.com/DataDog/integrations-core/pull/12565))

***Fixed***:

* Dependency updates ([#12653](https://github.com/DataDog/integrations-core/pull/12653))
* Prevent metadata validation from crashing on missing columns ([#12680](https://github.com/DataDog/integrations-core/pull/12680))
* Update exclude list in metadata validation ([#12658](https://github.com/DataDog/integrations-core/pull/12658))

## 16.6.0 / 2022-08-02

***Added***:

* [SNMP Traps] Include BITS enums in traps DB ([#12581](https://github.com/DataDog/integrations-core/pull/12581))
* Include the conditions in the retry for the `docker_run` function ([#12527](https://github.com/DataDog/integrations-core/pull/12527))
* Update Hatch plugin ([#12518](https://github.com/DataDog/integrations-core/pull/12518))
* Add functionality to load the legacy version of the integration ([#12396](https://github.com/DataDog/integrations-core/pull/12396))
* Add validations for duplicate JMX bean entries ([#11505](https://github.com/DataDog/integrations-core/pull/11505))

***Fixed***:

* Make log_patterns match all logs ([#12623](https://github.com/DataDog/integrations-core/pull/12623))
* Add pymysql to dependency update exclude list ([#12631](https://github.com/DataDog/integrations-core/pull/12631))
* Better failed assertion message, print return code ([#12615](https://github.com/DataDog/integrations-core/pull/12615))
* Do not update docker compose ([#12576](https://github.com/DataDog/integrations-core/pull/12576))
* Better print the error on extra startup commands for e2e tests on Agent image set up ([#12578](https://github.com/DataDog/integrations-core/pull/12578))
* Fix nightly base package builds that use Hatch ([#12544](https://github.com/DataDog/integrations-core/pull/12544))

## 16.5.2 / 2022-07-08

***Fixed***:

* Update trello.py ([#12475](https://github.com/DataDog/integrations-core/pull/12475))
* Do not include Datadog licenses to community files ([#12445](https://github.com/DataDog/integrations-core/pull/12445))

## 16.5.1 / 2022-07-06

***Fixed***:

* Fix validation error message and wrong parameters ([#12428](https://github.com/DataDog/integrations-core/pull/12428))
* Use the correct team when using `ddev -a release trello testable` ([#12418](https://github.com/DataDog/integrations-core/pull/12418))

## 16.5.0 / 2022-06-27

***Added***:

* Add a `--debug` (`-d`) flag to `ddev env test` ([#12379](https://github.com/DataDog/integrations-core/pull/12379))

***Fixed***:

* Fix tooling to support v2 manifests ([#12411](https://github.com/DataDog/integrations-core/pull/12411))
* Fix agent changelog command for manifest v2 ([#12406](https://github.com/DataDog/integrations-core/pull/12406))
* Change `get_commits_since` so that it won't take commits from other branches ([#12376](https://github.com/DataDog/integrations-core/pull/12376))

## 16.4.0 / 2022-06-16

***Added***:

* Emulate an Agent shutdown after every test that uses the `dd_run_check` fixture by default ([#12371](https://github.com/DataDog/integrations-core/pull/12371))
* Adjust description character limits in manifest ([#12339](https://github.com/DataDog/integrations-core/pull/12339))
* Include information about the manifest migration in the docs build ([#12136](https://github.com/DataDog/integrations-core/pull/12136))

***Fixed***:

* Properly support E2E testing for Hatch envs ([#12362](https://github.com/DataDog/integrations-core/pull/12362))
* Fix validation for readme images ([#12351](https://github.com/DataDog/integrations-core/pull/12351))
* Fix `Configuration & Deployment` tag for v2 manifest migration ([#12348](https://github.com/DataDog/integrations-core/pull/12348))
* Fix manifest migration of macOS tag ([#12138](https://github.com/DataDog/integrations-core/pull/12138))

## 16.3.0 / 2022-06-02

***Added***:

* Move v2 manifest field `classifier_tags` under `tile` ([#12122](https://github.com/DataDog/integrations-core/pull/12122))
* Upgrade Hatch to latest version ([#12016](https://github.com/DataDog/integrations-core/pull/12016))

***Fixed***:

* Fix extra metrics description example ([#12043](https://github.com/DataDog/integrations-core/pull/12043))
* Fix tooling for v2 manifests ([#12040](https://github.com/DataDog/integrations-core/pull/12040))

## 16.2.1 / 2022-05-12

***Fixed***:

* Fix `enabled` for parent options ([#11707](https://github.com/DataDog/integrations-core/pull/11707))
* Don't look for `=== JSON ===` in e2e output ([#12004](https://github.com/DataDog/integrations-core/pull/12004))

## 16.2.0 / 2022-05-11

***Added***:

* Resolve integer enums when generating SNMP traps DB ([#11911](https://github.com/DataDog/integrations-core/pull/11911))
* Support dynamic bearer tokens (Bound Service Account Token Volume) ([#11915](https://github.com/DataDog/integrations-core/pull/11915))
* Support Hatch for managing test environments ([#11950](https://github.com/DataDog/integrations-core/pull/11950))
* Assign `triage` team cards to Agent Platform ([#11768](https://github.com/DataDog/integrations-core/pull/11768))
* Update metadata.csv to require curated_metric column ([#11770](https://github.com/DataDog/integrations-core/pull/11770))
* Update style dependencies ([#11764](https://github.com/DataDog/integrations-core/pull/11764))
* Add gssapi as a dependency ([#11725](https://github.com/DataDog/integrations-core/pull/11725))

***Fixed***:

* Fix IBM ACE validation ([#11964](https://github.com/DataDog/integrations-core/pull/11964))
* Pin types-simplejson==3.17.5 ([#11923](https://github.com/DataDog/integrations-core/pull/11923))
* Fix a keyerror in ddev generate-traps-db ([#11892](https://github.com/DataDog/integrations-core/pull/11892))
* Fix logic for loading minimum base package dependency for tests ([#11771](https://github.com/DataDog/integrations-core/pull/11771))
* Apply recent fix to new integration templates ([#11751](https://github.com/DataDog/integrations-core/pull/11751))
* Update error message in recommended monitor validation to include more context ([#11750](https://github.com/DataDog/integrations-core/pull/11750))

## 16.1.0 / 2022-03-29

***Added***:

* Add new README for Tile-only integrations ([#11712](https://github.com/DataDog/integrations-core/pull/11712))

***Fixed***:

* Support newer versions of `click` ([#11746](https://github.com/DataDog/integrations-core/pull/11746))
* Cap the version of virtualenv ([#11742](https://github.com/DataDog/integrations-core/pull/11742))

## 16.0.0 / 2022-03-25

***Changed***:

* Refactor dependency tooling ([#11720](https://github.com/DataDog/integrations-core/pull/11720))

***Added***:

* Add `metric_patterns` to base template ([#11696](https://github.com/DataDog/integrations-core/pull/11696))

***Fixed***:

* Update check template README ([#11719](https://github.com/DataDog/integrations-core/pull/11719))
* Better logging and usability of ddev 'generate-traps-db' ([#11544](https://github.com/DataDog/integrations-core/pull/11544))
* Remove check options from jmx template ([#11686](https://github.com/DataDog/integrations-core/pull/11686))

## 15.11.0 / 2022-03-16

***Added***:

* Add more allowed recommended monitor types ([#11669](https://github.com/DataDog/integrations-core/pull/11669))
* Prevent tags for unreleased integrations ([#11605](https://github.com/DataDog/integrations-core/pull/11605))
* Allow limiting released changes up to a specific ref ([#11596](https://github.com/DataDog/integrations-core/pull/11596))

***Fixed***:

* Add space above tag function ([#11623](https://github.com/DataDog/integrations-core/pull/11623))
* Don't ignore the last character of lines when validating ASCII ([#11548](https://github.com/DataDog/integrations-core/pull/11548))
* Remove unsupported schema properties ([#11585](https://github.com/DataDog/integrations-core/pull/11585))
* Fail releases for missing tags ([#11593](https://github.com/DataDog/integrations-core/pull/11593))
* Remove outdated warning in the description for the `tls_ignore_warning` option ([#11591](https://github.com/DataDog/integrations-core/pull/11591))
* Fix fallback case in trello card assignment algorithm ([#11533](https://github.com/DataDog/integrations-core/pull/11533))

## 15.10.1 / 2022-02-19

***Fixed***:

* Fix integration templates ([#11539](https://github.com/DataDog/integrations-core/pull/11539))
* Handle the case in models sync where a file does not have a license header ([#11535](https://github.com/DataDog/integrations-core/pull/11535))

## 15.10.0 / 2022-02-16

***Added***:

* Update templates for new integrations ([#11510](https://github.com/DataDog/integrations-core/pull/11510))
* Reintroduce ASCII validation for README files ([#11509](https://github.com/DataDog/integrations-core/pull/11509))

***Fixed***:

* Update new check template ([#11489](https://github.com/DataDog/integrations-core/pull/11489))
* Fix codecov report ([#11492](https://github.com/DataDog/integrations-core/pull/11492))

## 15.9.0 / 2022-02-10

***Added***:

* Add `pyproject.toml` file ([#11303](https://github.com/DataDog/integrations-core/pull/11303))

***Fixed***:

* Fix style format for Python checks defined by a pyproject.toml file  ([#11483](https://github.com/DataDog/integrations-core/pull/11483))
* Fix `pytest` and `tox` plugins for checks with only a `pyproject.toml` ([#11477](https://github.com/DataDog/integrations-core/pull/11477))
* Fix E2E for new base package versions ([#11473](https://github.com/DataDog/integrations-core/pull/11473))
* Fix package signing for checks with only a `pyproject.toml` ([#11474](https://github.com/DataDog/integrations-core/pull/11474))

## 15.8.0 / 2022-02-07

***Added***:

* Support Python checks defined by a `pyproject.toml` file ([#11233](https://github.com/DataDog/integrations-core/pull/11233))
* Add snmp build-traps-db command ([#11235](https://github.com/DataDog/integrations-core/pull/11235))
* Add curated_metric column to check validation ([#11168](https://github.com/DataDog/integrations-core/pull/11168))

***Fixed***:

* Safely check the dashboards key exists before trying to write to it ([#11285](https://github.com/DataDog/integrations-core/pull/11285))
* Validate all `curated_metric` rows and properly validate empty `metadata.csv` files ([#11273](https://github.com/DataDog/integrations-core/pull/11273))
* More specific config validation error message ([#11272](https://github.com/DataDog/integrations-core/pull/11272))
* Unpin black ([#11270](https://github.com/DataDog/integrations-core/pull/11270))

## 15.7.0 / 2022-01-31

***Added***:

* Add example image with requirements for media carousel ([#11145](https://github.com/DataDog/integrations-core/pull/11145))

***Fixed***:

* Pin black package ([#11240](https://github.com/DataDog/integrations-core/pull/11240))
* Don't overwrite year in license header when generating files ([#11188](https://github.com/DataDog/integrations-core/pull/11188))
* Add manual changelog entry for 7.30.1 ([#11142](https://github.com/DataDog/integrations-core/pull/11142))
* Fix the type of `bearer_token_auth` ([#11144](https://github.com/DataDog/integrations-core/pull/11144))

## 15.6.0 / 2022-01-08

***Added***:

* Add discovery options to `ddev env check` command ([#11044](https://github.com/DataDog/integrations-core/pull/11044))

## 15.5.0 / 2022-01-06

***Added***:

* Set coverage report to only core checks ([#10922](https://github.com/DataDog/integrations-core/pull/10922))
* Add support for manifest V2 to "ddev create" ([#11028](https://github.com/DataDog/integrations-core/pull/11028))
* Add validation for invalid characters and sequences for service names ([#10813](https://github.com/DataDog/integrations-core/pull/10813))
* Add detailed trace to all integrations ([#10679](https://github.com/DataDog/integrations-core/pull/10679))
* Support event platform events for e2e testing ([#10663](https://github.com/DataDog/integrations-core/pull/10663))

***Fixed***:

* Don't add new line to license header ([#11025](https://github.com/DataDog/integrations-core/pull/11025))
* Don't add autogenerated comments to deprecation files ([#11014](https://github.com/DataDog/integrations-core/pull/11014))
* Vendor flup client FCGIApp ([#10953](https://github.com/DataDog/integrations-core/pull/10953))
* Do not regenerate models on new year ([#11003](https://github.com/DataDog/integrations-core/pull/11003))
* Don't allow use of author, pricing, and terms fields for extras integrations ([#10680](https://github.com/DataDog/integrations-core/pull/10680))
* Add comment to autogenerated model files ([#10945](https://github.com/DataDog/integrations-core/pull/10945))
* Bump base check requirement for JMX template ([#10925](https://github.com/DataDog/integrations-core/pull/10925))
* Handle nested template name overrides in config specs ([#10910](https://github.com/DataDog/integrations-core/pull/10910))
* Move is_public validations inside v1 and v2 specific checks ([#10841](https://github.com/DataDog/integrations-core/pull/10841))
* Support new SNMP profiles without throwing errors in translate-profiles ([#10648](https://github.com/DataDog/integrations-core/pull/10648))
* Snmp profile validator refactoring ([#10650](https://github.com/DataDog/integrations-core/pull/10650))
* Add documentation to config models ([#10757](https://github.com/DataDog/integrations-core/pull/10757))
* Allow BaseModel keywords as option names ([#10715](https://github.com/DataDog/integrations-core/pull/10715))

## 15.4.0 / 2021-11-22

***Added***:

* Support non-executable files during pipeline setup ([#10684](https://github.com/DataDog/integrations-core/pull/10684))

## 15.3.1 / 2021-11-17

***Fixed***:

* Refactor annotations to console utility and use relative imports ([#10645](https://github.com/DataDog/integrations-core/pull/10645))

## 15.3.0 / 2021-11-13

***Added***:

* Document new include_labels option ([#10617](https://github.com/DataDog/integrations-core/pull/10617))
* Document new use_process_start_time option ([#10601](https://github.com/DataDog/integrations-core/pull/10601))
* Add new base class for monitoring Windows performance counters ([#10504](https://github.com/DataDog/integrations-core/pull/10504))
* Update dependencies ([#10580](https://github.com/DataDog/integrations-core/pull/10580))

***Fixed***:

* Update annotations util with relative imports ([#10613](https://github.com/DataDog/integrations-core/pull/10613))
* Remove integration style hostname submission validation ([#10609](https://github.com/DataDog/integrations-core/pull/10609))
* Update warning message about agent signature ([#10606](https://github.com/DataDog/integrations-core/pull/10606))

## 15.2.0 / 2021-11-10

***Added***:

* Update style dependencies ([#10582](https://github.com/DataDog/integrations-core/pull/10582))
* Add option to include security deps in dep command ([#10523](https://github.com/DataDog/integrations-core/pull/10523))
* Add some debug messages to release make command and some refactor ([#10535](https://github.com/DataDog/integrations-core/pull/10535))
* Adding to schema required field tags ([#9777](https://github.com/DataDog/integrations-core/pull/9777))
* Adding table metric tags validator ([#9820](https://github.com/DataDog/integrations-core/pull/9820))
* Allow passing multiple directories to the `validate-profile` SNMP command ([#10029](https://github.com/DataDog/integrations-core/pull/10029))
* Add --format-links flag to README validation ([#10469](https://github.com/DataDog/integrations-core/pull/10469))
* Add decimal bytes units to metric metadata validation ([#10378](https://github.com/DataDog/integrations-core/pull/10378))
* Add annotations to dep validation ([#10286](https://github.com/DataDog/integrations-core/pull/10286))
* Add new validation to warn on bad style ([#10430](https://github.com/DataDog/integrations-core/pull/10430))

***Fixed***:

* Fix location of config ([#10590](https://github.com/DataDog/integrations-core/pull/10590))
* Update README templates ([#10564](https://github.com/DataDog/integrations-core/pull/10564))
* Update ignored deps ([#10516](https://github.com/DataDog/integrations-core/pull/10516))
* Fix ddev dash export for manifest v2 ([#10503](https://github.com/DataDog/integrations-core/pull/10503))
* Update checks that do not make sense to have logs ([#10366](https://github.com/DataDog/integrations-core/pull/10366))
* Fix description of JMX options ([#10454](https://github.com/DataDog/integrations-core/pull/10454))

## 15.1.0 / 2021-10-15

***Added***:

* Annotate manifest validation ([#10022](https://github.com/DataDog/integrations-core/pull/10022))

***Fixed***:

* [OpenMetricsV2] Allow empty namespaces ([#10420](https://github.com/DataDog/integrations-core/pull/10420))
* Remove unused MIB_SOURCE_URL and use relative imports ([#10353](https://github.com/DataDog/integrations-core/pull/10353))

## 15.0.0 / 2021-10-13

***Changed***:

* Rename legacy PDH config spec ([#10412](https://github.com/DataDog/integrations-core/pull/10412))

## 14.5.1 / 2021-10-12

***Fixed***:

* Update dashboard validation for Manifest V2 ([#10398](https://github.com/DataDog/integrations-core/pull/10398))
* Ignore metadata and service-checks when no integration included ([#10399](https://github.com/DataDog/integrations-core/pull/10399))

## 14.5.0 / 2021-10-12

***Added***:

* Add meta command for browsing Windows performance counters ([#10385](https://github.com/DataDog/integrations-core/pull/10385))

## 14.4.1 / 2021-10-08

***Fixed***:

* Allow entire config templates to be hidden and include Openmetrics legacy config option in models ([#10348](https://github.com/DataDog/integrations-core/pull/10348))

## 14.4.0 / 2021-10-04

***Added***:

* Sync configs with new option and bump base requirement ([#10315](https://github.com/DataDog/integrations-core/pull/10315))
* Enable E2E logs agent by default if environments mount logs ([#10293](https://github.com/DataDog/integrations-core/pull/10293))
* Add annotations for ci ([#10260](https://github.com/DataDog/integrations-core/pull/10260))

***Fixed***:

* Fix scope of E2E state management fixtures ([#10316](https://github.com/DataDog/integrations-core/pull/10316))

## 14.3.0 / 2021-09-30

***Added***:

* Allow setting DD_SITE in org config ([#10285](https://github.com/DataDog/integrations-core/pull/10285))
* Update readme validation to check repo over support ([#10283](https://github.com/DataDog/integrations-core/pull/10283))
* Create and use new Manifest interface class for ddev commands ([#10261](https://github.com/DataDog/integrations-core/pull/10261))
* Still support python2 with mypy ([#10272](https://github.com/DataDog/integrations-core/pull/10272))
* Update style dependencies ([#10238](https://github.com/DataDog/integrations-core/pull/10238))
* Add HTTP option to control the size of streaming responses ([#10183](https://github.com/DataDog/integrations-core/pull/10183))

***Fixed***:

* Don't add null values to classifier tags ([#10279](https://github.com/DataDog/integrations-core/pull/10279))
* Set repo name after we process the `--here` flag ([#10259](https://github.com/DataDog/integrations-core/pull/10259))

## 14.2.0 / 2021-09-27

***Added***:

* Update AZP templates to take in a dd_url and small fixes to validator ([#10230](https://github.com/DataDog/integrations-core/pull/10230))
* Add batch option to `ddev dep updates` command ([#10229](https://github.com/DataDog/integrations-core/pull/10229))
* Add DDEV_E2E_AGENT_PY2 env option ([#10221](https://github.com/DataDog/integrations-core/pull/10221))

***Fixed***:

* Don't set empty asset values on migration ([#10231](https://github.com/DataDog/integrations-core/pull/10231))
* Forbid time_unit/time_unit metric metadata type ([#10236](https://github.com/DataDog/integrations-core/pull/10236))

## 14.1.0 / 2021-09-23

***Added***:

* Strengthen ImmutableAttributesValidator to check for manifest changes in asset short names ([#10199](https://github.com/DataDog/integrations-core/pull/10199))
* Add app_uuid to manifest migrator ([#10200](https://github.com/DataDog/integrations-core/pull/10200))
* Add more functionality to `MockResponse` testing utility ([#10194](https://github.com/DataDog/integrations-core/pull/10194))

***Fixed***:

* Update JMX integration template ([#10193](https://github.com/DataDog/integrations-core/pull/10193))
* Fix the description of the `allow_redirects` HTTP option ([#10195](https://github.com/DataDog/integrations-core/pull/10195))
* Catch exception for malformed requirement syntax ([#10189](https://github.com/DataDog/integrations-core/pull/10189))

## 14.0.0 / 2021-09-21

***Changed***:

* Update immutable attributes validator for manifest upgrades v2 ([#10175](https://github.com/DataDog/integrations-core/pull/10175))
* Update mib_source_url to a Datadog fork of mibs.snmplabs.com ([#9952](https://github.com/DataDog/integrations-core/pull/9952))

***Added***:

* Add allow_redirect option ([#10160](https://github.com/DataDog/integrations-core/pull/10160))
* Annotate imports validation ([#10112](https://github.com/DataDog/integrations-core/pull/10112))
* Annotate models validations ([#10131](https://github.com/DataDog/integrations-core/pull/10131))
* Meta command to migrate manifest to V2 ([#10088](https://github.com/DataDog/integrations-core/pull/10088))
* Allow Kubernetes port forwarding to support any resource ([#10127](https://github.com/DataDog/integrations-core/pull/10127))
* Annotate saved views validation ([#10130](https://github.com/DataDog/integrations-core/pull/10130))
* Annotate metadata validation ([#10128](https://github.com/DataDog/integrations-core/pull/10128))
* Annotate package validation ([#10115](https://github.com/DataDog/integrations-core/pull/10115))
* Annotate licenses ([#10114](https://github.com/DataDog/integrations-core/pull/10114))
* Annotate readme validations ([#10116](https://github.com/DataDog/integrations-core/pull/10116))
* Allow exclusion of specific branch for changelog generation ([#10106](https://github.com/DataDog/integrations-core/pull/10106))
* Annotate JMX metric validation ([#10113](https://github.com/DataDog/integrations-core/pull/10113))
* Annotate EULA and agent requirements validation ([#10108](https://github.com/DataDog/integrations-core/pull/10108))
* Annotate codeowners ([#10107](https://github.com/DataDog/integrations-core/pull/10107))
* Echo warning for unnecessary params used ([#10053](https://github.com/DataDog/integrations-core/pull/10053))
* Add borrower and PySMI logs to MIB compiler ([#10074](https://github.com/DataDog/integrations-core/pull/10074))
* Allow the use of ddtrace for E2E tests ([#10082](https://github.com/DataDog/integrations-core/pull/10082))
* Disable generic tags ([#10027](https://github.com/DataDog/integrations-core/pull/10027))
* Add support for manifest V2 validations ([#9968](https://github.com/DataDog/integrations-core/pull/9968))
* Add critical service check test to integration template ([#10063](https://github.com/DataDog/integrations-core/pull/10063))
* Add support for testing new versions of products ([#9945](https://github.com/DataDog/integrations-core/pull/9945))
* Update release tooling to support `datadog_checks_dependency_provider` ([#10046](https://github.com/DataDog/integrations-core/pull/10046))
* Add Pytest plugin dependency to handle flakes ([#10043](https://github.com/DataDog/integrations-core/pull/10043))
* Annotate dashboard and recommended monitors validation ([#9899](https://github.com/DataDog/integrations-core/pull/9899))
* Annotate display_queue ([#9944](https://github.com/DataDog/integrations-core/pull/9944))

***Fixed***:

* Add Avi Vantage to INTEGRATION_LOGS_NOT_POSSIBLE ([#9667](https://github.com/DataDog/integrations-core/pull/9667))
* Remove annotation for unnecessary warning ([#10124](https://github.com/DataDog/integrations-core/pull/10124))
* Fix Mypy tests ([#10134](https://github.com/DataDog/integrations-core/pull/10134))
* Bump Mypy ([#10119](https://github.com/DataDog/integrations-core/pull/10119))
* Use Regex to parse for HTTP wrapper instead of reading by line ([#10055](https://github.com/DataDog/integrations-core/pull/10055))
* Instantiate borrowers in snmp profile generator ([#10086](https://github.com/DataDog/integrations-core/pull/10086))
* Fix warning for snmp generate profile command ([#9967](https://github.com/DataDog/integrations-core/pull/9967))
* Allow double quote on requirement ([#10028](https://github.com/DataDog/integrations-core/pull/10028))
* Don't read from nonexistent manifest files ([#10041](https://github.com/DataDog/integrations-core/pull/10041))
* Prevent creation of datadog named integrations ([#10014](https://github.com/DataDog/integrations-core/pull/10014))
* Fix bug when PR body is empty and includes DBM team to selector ([#9951](https://github.com/DataDog/integrations-core/pull/9951))

## 13.0.1 / 2021-08-27

***Fixed***:

* Pin regex ([#10005](https://github.com/DataDog/integrations-core/pull/10005))

## 13.0.0 / 2021-08-22

***Removed***:

* Remove documentation specifications ([#9763](https://github.com/DataDog/integrations-core/pull/9763))

***Added***:

* Add support for specifying a config path to `kind_run` utility ([#9930](https://github.com/DataDog/integrations-core/pull/9930))
* Ignore `cluster-agent` trello cards ([#9933](https://github.com/DataDog/integrations-core/pull/9933))
* Add typos validation ([#9902](https://github.com/DataDog/integrations-core/pull/9902))
* Add annotations to legacy agent signature ([#9873](https://github.com/DataDog/integrations-core/pull/9873))
* Add annotations to http validation ([#9870](https://github.com/DataDog/integrations-core/pull/9870))
* Add commands to automatically update and sync dependencies ([#9811](https://github.com/DataDog/integrations-core/pull/9811))
* Add manifest validator for `supported_os` field ([#9871](https://github.com/DataDog/integrations-core/pull/9871))
* Add annotation utils and config spec annotation ([#9868](https://github.com/DataDog/integrations-core/pull/9868))
* [NDM] Validate SysObjectID Consistency ([#9806](https://github.com/DataDog/integrations-core/pull/9806))
* Add option to generate profile using custom MIB source ([#9761](https://github.com/DataDog/integrations-core/pull/9761))
* [OpenMetricsV2] Improve label sharing behavior ([#9804](https://github.com/DataDog/integrations-core/pull/9804))
* Allow extra 3rd party licenses  ([#9796](https://github.com/DataDog/integrations-core/pull/9796))
* Refactor profile validators ([#9741](https://github.com/DataDog/integrations-core/pull/9741))
* Use `display_default` as a fallback for `default` when validating config models ([#9739](https://github.com/DataDog/integrations-core/pull/9739))

***Fixed***:

* Fix typos in log lines ([#9907](https://github.com/DataDog/integrations-core/pull/9907))
* Update `metrics` option in legacy OpenMetrics example config ([#9891](https://github.com/DataDog/integrations-core/pull/9891))
* Update GitHub `agent-network` team name ([#9678](https://github.com/DataDog/integrations-core/pull/9678))
* Better 'Invalid url' error message in dash export ([#9837](https://github.com/DataDog/integrations-core/pull/9837))
* Wait for E2E Agent to be started when running Python 2 ([#9828](https://github.com/DataDog/integrations-core/pull/9828))
* Re-attempt to pull docker images ([#9823](https://github.com/DataDog/integrations-core/pull/9823))
* Validate all integrations for base and dev updates ([#9787](https://github.com/DataDog/integrations-core/pull/9787))

## 12.4.1 / 2021-07-20

***Fixed***:

* Support empty config options for job or codecov ([#9736](https://github.com/DataDog/integrations-core/pull/9736))

## 12.4.0 / 2021-07-20

***Added***:

* Upgrade `virtualenv` ([#9691](https://github.com/DataDog/integrations-core/pull/9691))
* Add database integrations team to tooling trello ([#9671](https://github.com/DataDog/integrations-core/pull/9671))
* Add marketplace section to CI validation ([#9679](https://github.com/DataDog/integrations-core/pull/9679))

***Fixed***:

* Validate changed check in ci ([#9638](https://github.com/DataDog/integrations-core/pull/9638))
* Use pattern for enforcing a URL structure for author->homepage in manifest ([#9697](https://github.com/DataDog/integrations-core/pull/9697))

## 12.3.0 / 2021-07-14

***Added***:

* Add command for validating SNMP profiles ([#9587](https://github.com/DataDog/integrations-core/pull/9587))

## 12.2.0 / 2021-07-12

***Added***:

* Support multiple instances in config specs ([#9615](https://github.com/DataDog/integrations-core/pull/9615))

***Fixed***:

* Fix `meta dash export` ([#9652](https://github.com/DataDog/integrations-core/pull/9652))

## 12.1.0 / 2021-06-29

***Added***:

* log collection category validation ([#9514](https://github.com/DataDog/integrations-core/pull/9514))
* Enable `new_gc_metrics` JMX config option for new installations ([#9501](https://github.com/DataDog/integrations-core/pull/9501))
* Add metric_to_check validation in pricing ([#9289](https://github.com/DataDog/integrations-core/pull/9289))
* Update 3rd party license validation ([#9450](https://github.com/DataDog/integrations-core/pull/9450))

***Fixed***:

* Allow example for anyOf configuration option ([#9474](https://github.com/DataDog/integrations-core/pull/9474))

## 12.0.0 / 2021-05-28

***Changed***:

* Add common check parsing for validations ([#9229](https://github.com/DataDog/integrations-core/pull/9229))

***Added***:

* Add validation for third-party licenses ([#9436](https://github.com/DataDog/integrations-core/pull/9436))
* Support "ignore_tags" configuration ([#9392](https://github.com/DataDog/integrations-core/pull/9392))
* Support running post-install commands for E2E ([#9399](https://github.com/DataDog/integrations-core/pull/9399))
* Support hidden duplicate options from templates ([#9347](https://github.com/DataDog/integrations-core/pull/9347))
* Replace CLI dependency `appdirs` with `platformdirs` ([#9356](https://github.com/DataDog/integrations-core/pull/9356))
* Upgrade click ([#9342](https://github.com/DataDog/integrations-core/pull/9342))
* Upgrade datamodel-code-generator ([#9335](https://github.com/DataDog/integrations-core/pull/9335))
* [OpenMetricsV2] Add an option to send sum and count information when using distribution metrics ([#9301](https://github.com/DataDog/integrations-core/pull/9301))
* Upgrade virtualenv ([#9330](https://github.com/DataDog/integrations-core/pull/9330))
* Allow skipping of E2E tests based on environment markers ([#9327](https://github.com/DataDog/integrations-core/pull/9327))
* Support new Synthetics `run` metric unit for validation ([#9313](https://github.com/DataDog/integrations-core/pull/9313))

***Fixed***:

* Fix defaults for `collect_default_metrics` JMX config option ([#9441](https://github.com/DataDog/integrations-core/pull/9441))
* Sign `requirements.in` for releases ([#9419](https://github.com/DataDog/integrations-core/pull/9419))
* Fix detection of E2E environments ([#9373](https://github.com/DataDog/integrations-core/pull/9373))
* Fix `load_jmx_config` utility ([#9369](https://github.com/DataDog/integrations-core/pull/9369))
* Fix JMX config spec ([#9364](https://github.com/DataDog/integrations-core/pull/9364))
* Fix `metrics` option type for legacy OpenMetrics config spec ([#9318](https://github.com/DataDog/integrations-core/pull/9318)) Thanks [jejikenwogu](https://github.com/jejikenwogu).
* Fix typing ([#9338](https://github.com/DataDog/integrations-core/pull/9338))
* Update validate all log line to use validation name ([#9319](https://github.com/DataDog/integrations-core/pull/9319))
* Stop collecting empty coverage reports for non-Python checks ([#9297](https://github.com/DataDog/integrations-core/pull/9297))

## 11.2.0 / 2021-05-05

***Added***:

* Avoid double periods at the end of PR titles ([#8442](https://github.com/DataDog/integrations-core/pull/8442))
* Bump mypy ([#9285](https://github.com/DataDog/integrations-core/pull/9285))

***Fixed***:

* Fix validator bugs ([#9290](https://github.com/DataDog/integrations-core/pull/9290))

## 11.1.0 / 2021-05-03

***Added***:

* [snmp] Add interactive option to generate profile tool ([#9259](https://github.com/DataDog/integrations-core/pull/9259))
* [SNMP] Invert interactive logic in validate mib files ([#9258](https://github.com/DataDog/integrations-core/pull/9258))
* Add `ddev env edit` command ([#9196](https://github.com/DataDog/integrations-core/pull/9196))
* [SNMP] Validate mib filenames in snmp tooling ([#9228](https://github.com/DataDog/integrations-core/pull/9228))

***Fixed***:

* Refactor manifest validation into a class system ([#9111](https://github.com/DataDog/integrations-core/pull/9111))

## 11.0.1 / 2021-04-21

***Fixed***:

* Reduce ascii validation for assets ([#9208](https://github.com/DataDog/integrations-core/pull/9208))
* Fix QA card assignment to be distributed randomly and equally ([#9190](https://github.com/DataDog/integrations-core/pull/9190))

## 11.0.0 / 2021-04-19

***Changed***:

* [SNMP] Remove metric_prefix from snmp_tile integrations ([#9172](https://github.com/DataDog/integrations-core/pull/9172))

***Added***:

* Include ascii validation in asset files ([#9169](https://github.com/DataDog/integrations-core/pull/9169))

***Fixed***:

* Upgrade flake8 ([#9177](https://github.com/DataDog/integrations-core/pull/9177))
* Upgrade isort ([#9176](https://github.com/DataDog/integrations-core/pull/9176))
* Allow the use of relative images and refactor readme validate to use … ([#9160](https://github.com/DataDog/integrations-core/pull/9160))
* [ddev] Skip cherry-pick commits in `ddev release trello testable` ([#9134](https://github.com/DataDog/integrations-core/pull/9134))

## 10.0.0 / 2021-04-13

***Changed***:

* Split utils into fileutils and ci ([#9023](https://github.com/DataDog/integrations-core/pull/9023))

***Added***:

* Add --ddtrace flag ([#9124](https://github.com/DataDog/integrations-core/pull/9124))
* Move function to utils ([#9145](https://github.com/DataDog/integrations-core/pull/9145))
* Support the `--changed` flag for E2E testing ([#9141](https://github.com/DataDog/integrations-core/pull/9141))
* Support running Windows containers for E2E ([#9119](https://github.com/DataDog/integrations-core/pull/9119))

***Fixed***:

* Fix default config validation to include openmetrics template ([#9151](https://github.com/DataDog/integrations-core/pull/9151))
* Enable metric to check validation on the marketplace ([#9146](https://github.com/DataDog/integrations-core/pull/9146))
* Fix refactored imports ([#9136](https://github.com/DataDog/integrations-core/pull/9136))
* Fix open import for fs util ([#9135](https://github.com/DataDog/integrations-core/pull/9135))
* Fix integration log checking ([#9118](https://github.com/DataDog/integrations-core/pull/9118))

## 9.4.1 / 2021-04-06

***Fixed***:

* Ignore validation for marketplace ([#9100](https://github.com/DataDog/integrations-core/pull/9100))

## 9.4.0 / 2021-04-06

***Added***:

* Add testing module for frequently used `pytest`-related utilities ([#9081](https://github.com/DataDog/integrations-core/pull/9081))
* Upgrade virtualenv to 20.4.3 ([#9086](https://github.com/DataDog/integrations-core/pull/9086))

***Fixed***:

* Ignore metric_to_check validation for extras ([#9098](https://github.com/DataDog/integrations-core/pull/9098))
* Update dashboards status ([#9083](https://github.com/DataDog/integrations-core/pull/9083))
* Better support for dashboard filename ([#9087](https://github.com/DataDog/integrations-core/pull/9087))

## 9.3.0 / 2021-04-05

***Added***:

* Update defaults for legacy OpenMetrics config spec template ([#9065](https://github.com/DataDog/integrations-core/pull/9065))
* Add "exception" unit to metadata ([#9063](https://github.com/DataDog/integrations-core/pull/9063)) Thanks [kevingosse](https://github.com/kevingosse).
* Add command to run all validations at once ([#9040](https://github.com/DataDog/integrations-core/pull/9040))

***Fixed***:

* Raise validation error if metadata.csv but no metric_to_check ([#9042](https://github.com/DataDog/integrations-core/pull/9042))
* Ignore secondary dashboards ([#9037](https://github.com/DataDog/integrations-core/pull/9037))
* Include new and legacy openmetrics template in http validation ([#9034](https://github.com/DataDog/integrations-core/pull/9034))

## 9.2.1 / 2021-03-22

***Fixed***:

* Fix models validation ([#8871](https://github.com/DataDog/integrations-core/pull/8871))

## 9.2.0 / 2021-03-22

***Added***:

* Add config spec data model consumer ([#8675](https://github.com/DataDog/integrations-core/pull/8675))

## 9.1.1 / 2021-03-18

***Fixed***:

* Improve error message ([#8788](https://github.com/DataDog/integrations-core/pull/8788))
* Fix infra-integrations team for testable ([#8784](https://github.com/DataDog/integrations-core/pull/8784))

## 9.1.0 / 2021-03-07

***Security***:

* Upgrade pyyaml python package ([#8707](https://github.com/DataDog/integrations-core/pull/8707))

***Added***:

* Check if integrations are logs only ([#8699](https://github.com/DataDog/integrations-core/pull/8699))

***Fixed***:

* Do not append -pyx for agent7 images ([#8746](https://github.com/DataDog/integrations-core/pull/8746))
* Avoid mounting check confd volume if there is no config ([#8722](https://github.com/DataDog/integrations-core/pull/8722))

## 9.0.0 / 2021-03-01

***Changed***:

* Create missing cards when using `--move-cards` ([#8595](https://github.com/DataDog/integrations-core/pull/8595))

***Added***:

* Add ddev example committer tool ([#8697](https://github.com/DataDog/integrations-core/pull/8697))

***Fixed***:

* Validate metric prefixes for all metric metadata ([#8672](https://github.com/DataDog/integrations-core/pull/8672))
* Remove marketplace option for ddev create ([#8649](https://github.com/DataDog/integrations-core/pull/8649))

## 8.0.1 / 2021-02-19

***Fixed***:

* Fix error printing json errors when error on list object ([#8650](https://github.com/DataDog/integrations-core/pull/8650))
* Fix validate readme command ([#8645](https://github.com/DataDog/integrations-core/pull/8645))
* Replace `oneOf` with `anyOf` for multi-type support ([#8626](https://github.com/DataDog/integrations-core/pull/8626))

## 8.0.0 / 2021-02-12

***Changed***:

* Rename config spec example consumer option `default` to `display_default` ([#8593](https://github.com/DataDog/integrations-core/pull/8593))

***Added***:

* Add config spec for the new OpenMetrics implementation ([#8452](https://github.com/DataDog/integrations-core/pull/8452))
* Support `additionalProperties` object field for config specs ([#8525](https://github.com/DataDog/integrations-core/pull/8525))
* Support bind mounting single files for Docker E2E on Windows ([#8516](https://github.com/DataDog/integrations-core/pull/8516))

***Fixed***:

* Fix the ids `done` in `progress` columns ([#8478](https://github.com/DataDog/integrations-core/pull/8478))
* Fix tabs in readme consumer ([#8551](https://github.com/DataDog/integrations-core/pull/8551))
* Remove metric alert from recommended monitors ([#8508](https://github.com/DataDog/integrations-core/pull/8508))
* Fix link referencing for append and prepend ([#8548](https://github.com/DataDog/integrations-core/pull/8548))
* Implement append and prepend options for docs validator ([#8542](https://github.com/DataDog/integrations-core/pull/8542))
* Normalize links in docs validator for nested sections ([#8541](https://github.com/DataDog/integrations-core/pull/8541))
* Update metrics template ([#8539](https://github.com/DataDog/integrations-core/pull/8539))
* Fix `oneOf` in config specs ([#8540](https://github.com/DataDog/integrations-core/pull/8540))
* Do not run base_check for any base package ([#8534](https://github.com/DataDog/integrations-core/pull/8534))
* fix nested sections for readme rendering ([#8524](https://github.com/DataDog/integrations-core/pull/8524))
* Avoid forcing base dependencies for base checks ([#8444](https://github.com/DataDog/integrations-core/pull/8444))
* fix nested sections in docs validator ([#8519](https://github.com/DataDog/integrations-core/pull/8519))
* Add test cases to docs validator ([#8503](https://github.com/DataDog/integrations-core/pull/8503))
* Bump minimum base package version ([#8443](https://github.com/DataDog/integrations-core/pull/8443))
* Fix handling of multiple nested types for the example config spec consumer ([#8465](https://github.com/DataDog/integrations-core/pull/8465))
* Fix validation of Agent deps when using single check ([#8461](https://github.com/DataDog/integrations-core/pull/8461))

## 7.0.1 / 2021-01-25

***Fixed***:

* Minor error message fix ([#8424](https://github.com/DataDog/integrations-core/pull/8424))

## 7.0.0 / 2021-01-22

***Changed***:

* Rename legacy OpenMetrics config spec ([#8413](https://github.com/DataDog/integrations-core/pull/8413))
* Small changes in template for "SNMP tiles" ([#8289](https://github.com/DataDog/integrations-core/pull/8289))

***Added***:

* Add --export-csv option ([#8350](https://github.com/DataDog/integrations-core/pull/8350))
* Add config spec support for options with multiple types ([#8378](https://github.com/DataDog/integrations-core/pull/8378))
* Add docs spec progress to docs status board ([#8357](https://github.com/DataDog/integrations-core/pull/8357))
* Add option to exclude release prs ([#8351](https://github.com/DataDog/integrations-core/pull/8351))
* Support installing minimum and unpinned datadog_checks_base dependencies for tests ([#8318](https://github.com/DataDog/integrations-core/pull/8318))
* Allow MockResponse method `iter_lines` to be called multiple times ([#8353](https://github.com/DataDog/integrations-core/pull/8353))
* [1/3] Add units to metadata check ([#8308](https://github.com/DataDog/integrations-core/pull/8308))
* Add version verification for datadog-checks-base ([#8255](https://github.com/DataDog/integrations-core/pull/8255))
* Support nightly datadog_checks_base package checks ([#8293](https://github.com/DataDog/integrations-core/pull/8293))
* Add snmp_tile template to ddev create --type ([#8216](https://github.com/DataDog/integrations-core/pull/8216))
* Add new global fixture to mock HTTP requests ([#8276](https://github.com/DataDog/integrations-core/pull/8276))
* Update Codecov config validation with new flag carryforward options ([#8085](https://github.com/DataDog/integrations-core/pull/8085))
* Ensure default templates are included in config spec ([#8232](https://github.com/DataDog/integrations-core/pull/8232))

***Fixed***:

* Update logs template with docs feedback ([#8412](https://github.com/DataDog/integrations-core/pull/8412))
* Fix conflicting link references in tile readme template ([#8409](https://github.com/DataDog/integrations-core/pull/8409))
* Update logs readme template ([#8399](https://github.com/DataDog/integrations-core/pull/8399))
* Increase indentation of log snippets ([#8360](https://github.com/DataDog/integrations-core/pull/8360))
* Fix dep validation to work on single checks for PRs ([#8297](https://github.com/DataDog/integrations-core/pull/8297))
* Fix ddev env test last error ([#8264](https://github.com/DataDog/integrations-core/pull/8264))
* Update prometheus_metrics_prefix documentation ([#8236](https://github.com/DataDog/integrations-core/pull/8236))

## 6.1.0 / 2020-12-22

***Added***:

* Add metric_to_check validation redirection for snmp_<vendor> integrations ([#8215](https://github.com/DataDog/integrations-core/pull/8215))
* Add exec command option to ddev env shell ([#8235](https://github.com/DataDog/integrations-core/pull/8235))
* Fail validation if metadata file is empty ([#8194](https://github.com/DataDog/integrations-core/pull/8194))

***Fixed***:

* Fix release ([#8237](https://github.com/DataDog/integrations-core/pull/8237))
* Update dogweb dashboard list ([#8191](https://github.com/DataDog/integrations-core/pull/8191))

## 6.0.0 / 2020-12-11

***Changed***:

* Use snmp mibs copy while mibs.snmplabs.com is down ([#7835](https://github.com/DataDog/integrations-core/pull/7835))
* Add sub-watt metric metadata units ([#7994](https://github.com/DataDog/integrations-core/pull/7994))

***Added***:

* Document new collect_default_jvm_metrics flag for JMXFetch integrations ([#8153](https://github.com/DataDog/integrations-core/pull/8153))
* Add support for tabular check output ([#8129](https://github.com/DataDog/integrations-core/pull/8129))
* Add test filter to env test ([#8101](https://github.com/DataDog/integrations-core/pull/8101))
* [SNMP] Generate profiles from MIBs ([#7925](https://github.com/DataDog/integrations-core/pull/7925))
* Validate partner integration readmes contain an h2 support section ([#8055](https://github.com/DataDog/integrations-core/pull/8055))
* Add 'since' flag to manually specify tag to look from ([#7950](https://github.com/DataDog/integrations-core/pull/7950))
* Support inline comment to skip http validation ([#8020](https://github.com/DataDog/integrations-core/pull/8020))
* Add config template for TLS helper ([#8014](https://github.com/DataDog/integrations-core/pull/8014))

***Fixed***:

* Refactor `has_logs` utility ([#8123](https://github.com/DataDog/integrations-core/pull/8123))
* Build developer docs in strict mode ([#8152](https://github.com/DataDog/integrations-core/pull/8152))
* Skip auto-setting Python version suffix if using an RC build ([#7653](https://github.com/DataDog/integrations-core/pull/7653))
* Remove active_directory references from config ([#8111](https://github.com/DataDog/integrations-core/pull/8111))
* Fix pdh configuration spec ([#8106](https://github.com/DataDog/integrations-core/pull/8106))
* Update small typo in tls-specific options documentation ([#8103](https://github.com/DataDog/integrations-core/pull/8103))
* [Config specs] Allow longer line in compact_example lists ([#8015](https://github.com/DataDog/integrations-core/pull/8015))
* Include openmetrics integrations in http validation ([#7999](https://github.com/DataDog/integrations-core/pull/7999))

## 5.1.0 / 2020-11-10

***Added***:

* Allow mechanism for handling duplicate option names for config specs ([#7968](https://github.com/DataDog/integrations-core/pull/7968))
* Add Infra Integrations to Trello release script ([#7906](https://github.com/DataDog/integrations-core/pull/7906))

***Fixed***:

* Fix http validator ([#7936](https://github.com/DataDog/integrations-core/pull/7936))
* Fix Trello release script ([#7909](https://github.com/DataDog/integrations-core/pull/7909))

## 5.0.0 / 2020-10-31

***Changed***:

* Use creation, update and closed date to detect user inactivity. ([#7771](https://github.com/DataDog/integrations-core/pull/7771))

***Added***:

* add options method for validation ([#7895](https://github.com/DataDog/integrations-core/pull/7895))
* Sync openmetrics config specs with new option ignore_metrics_by_labels ([#7823](https://github.com/DataDog/integrations-core/pull/7823))
* Tracemalloc: Rename white/blacklist to include/exclude ([#7626](https://github.com/DataDog/integrations-core/pull/7626))
* Detect and abort if there are tox errors ([#7801](https://github.com/DataDog/integrations-core/pull/7801))
* Add fixed_cards_mover.py ([#7724](https://github.com/DataDog/integrations-core/pull/7724))
* Add warning when running environment without dev flag for non-core integrations ([#7811](https://github.com/DataDog/integrations-core/pull/7811))

## 4.2.0 / 2020-10-14

***Added***:

* Validate JMX integrations metrics.yaml ([#7733](https://github.com/DataDog/integrations-core/pull/7733))
* Make inventories metadata testable in e2e ([#7761](https://github.com/DataDog/integrations-core/pull/7761))
* Validate metrics_metadata in manifest.json ([#7746](https://github.com/DataDog/integrations-core/pull/7746))
* Add ability to dynamically get authentication information ([#7660](https://github.com/DataDog/integrations-core/pull/7660))
* Check the git token scope when calling `get_team_members` ([#7712](https://github.com/DataDog/integrations-core/pull/7712))
* [doc] Add encoding in log config sample ([#7708](https://github.com/DataDog/integrations-core/pull/7708))

## 4.1.0 / 2020-10-01

***Added***:

* Added HTTP wrapper class validator ([#7676](https://github.com/DataDog/integrations-core/pull/7676))

***Fixed***:

* Added missing HTTP templates to existing config specs ([#7694](https://github.com/DataDog/integrations-core/pull/7694))
* Handle missing "eula" key in EULA validation ([#7640](https://github.com/DataDog/integrations-core/pull/7640))
* Check case of integration header in metadata.csv files for metadata validation ([#7643](https://github.com/DataDog/integrations-core/pull/7643))

## 4.0.1 / 2020-09-21

***Fixed***:

* Fix changed manifest validation for new integrations ([#7623](https://github.com/DataDog/integrations-core/pull/7623))

## 4.0.0 / 2020-09-16

***Changed***:

* Use `git diff` instead of GitHub's API to detect if manifest fields changed during validation ([#7599](https://github.com/DataDog/integrations-core/pull/7599))

## 3.25.0 / 2020-09-16

***Added***:

* Allow `ddev create` to create marketplace integration scaffolding ([#7543](https://github.com/DataDog/integrations-core/pull/7543))
* Remove transient dependency pin ([#7545](https://github.com/DataDog/integrations-core/pull/7545))
* [config specs] Support overrides for mappings when references start with a name ([#7557](https://github.com/DataDog/integrations-core/pull/7557))
* Add command to add Agent version to integrations CHANGELOG.md ([#7518](https://github.com/DataDog/integrations-core/pull/7518))

***Fixed***:

* Fix init_config/db config spec template ([#7583](https://github.com/DataDog/integrations-core/pull/7583))
* Use database config template in existing specs ([#7548](https://github.com/DataDog/integrations-core/pull/7548))
* Upgrade isort ([#7539](https://github.com/DataDog/integrations-core/pull/7539))

## 3.24.0 / 2020-09-08

***Added***:

* Add marketplace to repo choices and make -x set repo_choice ([#7508](https://github.com/DataDog/integrations-core/pull/7508))

***Fixed***:

* Pin transient dependency pyrsistent to < 0.17.0 ([#7546](https://github.com/DataDog/integrations-core/pull/7546))
* Add minItems to pricing and better validation error message ([#7514](https://github.com/DataDog/integrations-core/pull/7514))
* Do not render null defaults for config spec example consumer ([#7503](https://github.com/DataDog/integrations-core/pull/7503))

## 3.23.0 / 2020-09-04

***Added***:

* Add initial validations for EULA files ([#7473](https://github.com/DataDog/integrations-core/pull/7473))
* Add RequestsWrapper option to support UTF-8 for basic auth ([#7441](https://github.com/DataDog/integrations-core/pull/7441))
* Change old_payload warning to failure ([#7419](https://github.com/DataDog/integrations-core/pull/7419))
* Support service checks in recommended monitors ([#7423](https://github.com/DataDog/integrations-core/pull/7423))

***Fixed***:

* Apply overrides recursively to config specs ([#7497](https://github.com/DataDog/integrations-core/pull/7497))
* Pin style deps ([#7485](https://github.com/DataDog/integrations-core/pull/7485))
* Fix ddev create for jmx ([#7346](https://github.com/DataDog/integrations-core/pull/7346))
* Fix style for the latest release of Black ([#7438](https://github.com/DataDog/integrations-core/pull/7438))

## 3.22.0 / 2020-08-24

***Added***:

* Auto assign card ([#7347](https://github.com/DataDog/integrations-core/pull/7347))
* Use author_name instead of author_info object ([#7417](https://github.com/DataDog/integrations-core/pull/7417))
* Update dependency tooling to support multiple version/marker combinations ([#7391](https://github.com/DataDog/integrations-core/pull/7391))

***Fixed***:

* Add security team ([#7357](https://github.com/DataDog/integrations-core/pull/7357))
* Update proxy section in conf.yaml ([#7336](https://github.com/DataDog/integrations-core/pull/7336))
* Use consistent formatting for boolean values ([#7405](https://github.com/DataDog/integrations-core/pull/7405))

## 3.21.0 / 2020-08-18

***Added***:

* Update dash export command to use newer api ([#7365](https://github.com/DataDog/integrations-core/pull/7365))
* Allow the validation of the newer dashboard payload in integration boards ([#7362](https://github.com/DataDog/integrations-core/pull/7362))
* Add new package validation for `name` field in setup.py ([#7359](https://github.com/DataDog/integrations-core/pull/7359))
* Add monitor validation on allowed types and more friendly error messages ([#7356](https://github.com/DataDog/integrations-core/pull/7356))
* Validate integration column in metrics metadata ([#7372](https://github.com/DataDog/integrations-core/pull/7372))
* Support updating Agent /etc/hosts in E2E envs ([#7343](https://github.com/DataDog/integrations-core/pull/7343))

***Fixed***:

* Fix intg-tools-libs entry in trello.py ([#7335](https://github.com/DataDog/integrations-core/pull/7335))

## 3.20.0 / 2020-08-11

***Added***:

* Validate the monitor id isn't in the payload ([#7341](https://github.com/DataDog/integrations-core/pull/7341))

***Fixed***:

* ddev for extras must not rewrite line endings ([#7344](https://github.com/DataDog/integrations-core/pull/7344))
* Clean http config whitespaces ([#7339](https://github.com/DataDog/integrations-core/pull/7339))

## 3.19.0 / 2020-08-07

***Added***:

* Add show warnings option to validate metadata ([#7310](https://github.com/DataDog/integrations-core/pull/7310))
* Enable histogram for pytest-benchmark ([#7301](https://github.com/DataDog/integrations-core/pull/7301))

## 3.18.1 / 2020-08-05

***Fixed***:

* Update logs config service field to optional ([#7209](https://github.com/DataDog/integrations-core/pull/7209))

## 3.18.0 / 2020-08-05

***Added***:

* Add validation for recommended monitors ([#7280](https://github.com/DataDog/integrations-core/pull/7280))
* Refactor logic for getting assets ([#7282](https://github.com/DataDog/integrations-core/pull/7282))
* Convert jmx to in-app types for replay_check_run ([#7275](https://github.com/DataDog/integrations-core/pull/7275))
* Add minimum length to required strings in manifest validation ([#7281](https://github.com/DataDog/integrations-core/pull/7281))
* Add self.instance comment to check template ([#7256](https://github.com/DataDog/integrations-core/pull/7256))

***Fixed***:

* Make logs attribute optional in manifest ([#7287](https://github.com/DataDog/integrations-core/pull/7287))
* Fix TOX_SKIP_ENV filtering ([#7274](https://github.com/DataDog/integrations-core/pull/7274))
* Support TOX_SKIP_ENV var in e2e tests ([#7269](https://github.com/DataDog/integrations-core/pull/7269))

## 3.17.0 / 2020-08-03

***Added***:

* Validate dashboards are using the screen API ([#7237](https://github.com/DataDog/integrations-core/pull/7237))
* Update RC build cards when running `ddev release trello testable` ([#7082](https://github.com/DataDog/integrations-core/pull/7082))
* Add "ddev config edit" subcommand ([#7217](https://github.com/DataDog/integrations-core/pull/7217))

## 3.16.0 / 2020-07-24

***Added***:

* Add validation for readmes ([#7088](https://github.com/DataDog/integrations-core/pull/7088))
* Option to skip semver version validation in changelog command when specifying old version ([#7200](https://github.com/DataDog/integrations-core/pull/7200))
* Add more manifest validations for ddev ([#7142](https://github.com/DataDog/integrations-core/pull/7142))

***Fixed***:

* Allow codeowner validation to fail on CI  ([#7207](https://github.com/DataDog/integrations-core/pull/7207))

## 3.15.0 / 2020-07-22

***Added***:

* Add validation script for codeowners ([#6071](https://github.com/DataDog/integrations-core/pull/6071))
* Allow "noqa" for long spec descriptions ([#7177](https://github.com/DataDog/integrations-core/pull/7177))
* Support "*" wildcard in type_overrides configuration ([#7071](https://github.com/DataDog/integrations-core/pull/7071))
* Skip PRs tagged with skip-qa ([#7147](https://github.com/DataDog/integrations-core/pull/7147))
* Report process signatures status ([#7148](https://github.com/DataDog/integrations-core/pull/7148))

***Fixed***:

* DOCS-838 Template wording ([#7038](https://github.com/DataDog/integrations-core/pull/7038))

## 3.14.2 / 2020-07-14

***Fixed***:

* Allow ddev release to commit directly to master for extras integrations ([#7127](https://github.com/DataDog/integrations-core/pull/7127))

## 3.14.1 / 2020-07-14

***Fixed***:

* Fix ddev release extras ([#7124](https://github.com/DataDog/integrations-core/pull/7124))

## 3.14.0 / 2020-07-14

***Added***:

* Add ddev release-stats tool for agent's release ([#6850](https://github.com/DataDog/integrations-core/pull/6850))
* Add shell subcommand to ddev env ([#7067](https://github.com/DataDog/integrations-core/pull/7067))
* Add `Inbox` column to `ddev release trello status` output ([#7033](https://github.com/DataDog/integrations-core/pull/7033))

***Fixed***:

* Fix ddev release tag dryrun ([#7121](https://github.com/DataDog/integrations-core/pull/7121))
* Update ntlm_domain example ([#7118](https://github.com/DataDog/integrations-core/pull/7118))
* Remove validation on formatting of public title ([#7107](https://github.com/DataDog/integrations-core/pull/7107))
* Add empty example dashboards and images to ddev create templates ([#7039](https://github.com/DataDog/integrations-core/pull/7039))
* Add new_gc_metrics to all jmx integrations ([#7073](https://github.com/DataDog/integrations-core/pull/7073))
* Update docstring to use trello subcommand  ([#7009](https://github.com/DataDog/integrations-core/pull/7009))
* Add assert_metrics_using_metadata to template ([#7081](https://github.com/DataDog/integrations-core/pull/7081))
* Remove deprecated isort recursive option ([#7060](https://github.com/DataDog/integrations-core/pull/7060))
* Clean before building wheel ([#7052](https://github.com/DataDog/integrations-core/pull/7052))
* Sync example config with JMX template ([#7014](https://github.com/DataDog/integrations-core/pull/7014))
* Run manifest validations again ([#7015](https://github.com/DataDog/integrations-core/pull/7015))

## 3.13.0 / 2020-06-29

***Added***:

* Add note about warning concurrency ([#6967](https://github.com/DataDog/integrations-core/pull/6967))
* Add tools and libraries team to trello ([#6968](https://github.com/DataDog/integrations-core/pull/6968))

***Fixed***:

* Assert new jvm metrics ([#6996](https://github.com/DataDog/integrations-core/pull/6996))
* Fix elastic and redis dashboards name ([#6962](https://github.com/DataDog/integrations-core/pull/6962))
* More accurately determine if an integration has a dashboard ([#6946](https://github.com/DataDog/integrations-core/pull/6946))

## 3.12.0 / 2020-06-23

***Added***:

* Add `--dirty` option to speed up docs dev reloads ([#6939](https://github.com/DataDog/integrations-core/pull/6939))

***Fixed***:

* Expand user paths correctly for legacy E2E config ([#6940](https://github.com/DataDog/integrations-core/pull/6940))
* Fix template specs typos ([#6912](https://github.com/DataDog/integrations-core/pull/6912))

## 3.11.0 / 2020-06-11

***Added***:

* Add automated signing workflow for non-core integrations ([#6868](https://github.com/DataDog/integrations-core/pull/6868))
* Allow ddev release command to work for different organizations ([#6855](https://github.com/DataDog/integrations-core/pull/6855))
* Add extra validation to manifest files for fields that cannot change ([#6848](https://github.com/DataDog/integrations-core/pull/6848))
* Validate that dashboards have required fields ([#6833](https://github.com/DataDog/integrations-core/pull/6833))

***Fixed***:

* Provide helpful error message when releasing a project with missing or improper tags ([#6861](https://github.com/DataDog/integrations-core/pull/6861))
* Adjust jmxfetch config ([#6864](https://github.com/DataDog/integrations-core/pull/6864))
* Remove unused dashboard fields in export ([#6787](https://github.com/DataDog/integrations-core/pull/6787))

## 3.10.0 / 2020-06-08

***Added***:

* Add option to open DogStatsD port on agent ([#6777](https://github.com/DataDog/integrations-core/pull/6777))
* Support releasing non-core checks ([#6805](https://github.com/DataDog/integrations-core/pull/6805))

***Fixed***:

* Don't error when setting an invalid repo in config ([#6786](https://github.com/DataDog/integrations-core/pull/6786))
* Fix `ensure_default_envdir` tox plugin flag ([#6817](https://github.com/DataDog/integrations-core/pull/6817))

## 3.9.1 / 2020-06-03

***Fixed***:

* Fix new Check template ([#6811](https://github.com/DataDog/integrations-core/pull/6811))

## 3.9.0 / 2020-06-03

***Added***:

* Speed up test suites by using a single virtual environment per Python version ([#6789](https://github.com/DataDog/integrations-core/pull/6789))
* Add validation for saved views ([#6783](https://github.com/DataDog/integrations-core/pull/6783))

## 3.8.0 / 2020-06-01

***Added***:

* Update CLI dependencies ([#6784](https://github.com/DataDog/integrations-core/pull/6784))
* Update default E2E Agent configuration ([#6771](https://github.com/DataDog/integrations-core/pull/6771))
* Condense output of Trello release status command ([#6755](https://github.com/DataDog/integrations-core/pull/6755))
* Add Codecov config validation ([#6749](https://github.com/DataDog/integrations-core/pull/6749))
* Add ability to generate docs site as a PDF ([#6719](https://github.com/DataDog/integrations-core/pull/6719))
* Remove instance argument from new Check template ([#6673](https://github.com/DataDog/integrations-core/pull/6673))
* Add author and labels to Trello release cards ([#6694](https://github.com/DataDog/integrations-core/pull/6694))
* Better error output when CheckCommandOutput fails ([#6674](https://github.com/DataDog/integrations-core/pull/6674))

***Fixed***:

* Build packages with the current Python ([#6770](https://github.com/DataDog/integrations-core/pull/6770))

## 3.7.1 / 2020-05-18

***Fixed***:

* Sync JMX template example config ([#6676](https://github.com/DataDog/integrations-core/pull/6676))

## 3.7.0 / 2020-05-17

***Added***:

* Add send_monotonic_with_gauge config option and refactor test ([#6618](https://github.com/DataDog/integrations-core/pull/6618))
* Add developer docs ([#6623](https://github.com/DataDog/integrations-core/pull/6623))

## 3.6.0 / 2020-05-14

***Added***:

* Add Trello release status subcommand ([#6628](https://github.com/DataDog/integrations-core/pull/6628))
* Add environment runner for Kubernetes' `kind` ([#6522](https://github.com/DataDog/integrations-core/pull/6522))
* Update JMX template to use JMX config spec ([#6611](https://github.com/DataDog/integrations-core/pull/6611))
* Install checks' dependencies for E2E using `deps` extra feature ([#6599](https://github.com/DataDog/integrations-core/pull/6599))
* Allow optional dependency installation for all checks ([#6589](https://github.com/DataDog/integrations-core/pull/6589))
* Support more tag formats when generating changelogs ([#6584](https://github.com/DataDog/integrations-core/pull/6584))
* Add dedicated config section for E2E agent selection ([#6558](https://github.com/DataDog/integrations-core/pull/6558))
* Provide a good default for `service` field of E2E logs config ([#6557](https://github.com/DataDog/integrations-core/pull/6557))
* Add retry to docker_run ([#6514](https://github.com/DataDog/integrations-core/pull/6514))
* Include uncommitted git files to files_changed ([#6480](https://github.com/DataDog/integrations-core/pull/6480))
* Add constant for jmx default metrics ([#6507](https://github.com/DataDog/integrations-core/pull/6507))
* Make integration template adhere to file name conventions ([#6493](https://github.com/DataDog/integrations-core/pull/6493))
* Add rmi_connection_timeout & rmi_client_timeout to config spec ([#6459](https://github.com/DataDog/integrations-core/pull/6459))
* Update `release make` to avoid committing new files ([#6263](https://github.com/DataDog/integrations-core/pull/6263))
* Add validation for per_unit_name and line numbers for all errors ([#6394](https://github.com/DataDog/integrations-core/pull/6394))
* Validate metrics using metadata.csv ([#6027](https://github.com/DataDog/integrations-core/pull/6027))
* Add verbose mode to validate config ([#6302](https://github.com/DataDog/integrations-core/pull/6302))
* Validate metadata doesn't contain `|` ([#6333](https://github.com/DataDog/integrations-core/pull/6333))

***Fixed***:

* Fix style to account for new flake8 rules ([#6620](https://github.com/DataDog/integrations-core/pull/6620))
* Fix typo in README template for new community integrations ([#6585](https://github.com/DataDog/integrations-core/pull/6585))
* Remove metrics file from JMX template's config spec ([#6559](https://github.com/DataDog/integrations-core/pull/6559))
* Remove `dd_check_types` from check template ([#6460](https://github.com/DataDog/integrations-core/pull/6460))
* Remove `metrics.yaml` from non testable files ([#6280](https://github.com/DataDog/integrations-core/pull/6280))
* Hide openmetrics template options that are typically overridden ([#6338](https://github.com/DataDog/integrations-core/pull/6338))

## 3.5.0 / 2020-04-14

***Added***:

* Update documentation links in new integration templates ([#6294](https://github.com/DataDog/integrations-core/pull/6294))
* Add validation for Unicode characters in metric metadata ([#6318](https://github.com/DataDog/integrations-core/pull/6318))
* Add default template to openmetrics & jmx config ([#6328](https://github.com/DataDog/integrations-core/pull/6328))
* Add config spec ability to control whether options are enabled by default ([#6322](https://github.com/DataDog/integrations-core/pull/6322))
* Allow `dd_environment` fixtures to accept arbitrary arguments ([#6306](https://github.com/DataDog/integrations-core/pull/6306))

## 3.4.0 / 2020-04-08

***Added***:

* Add Container App team to ddev trello tool ([#6268](https://github.com/DataDog/integrations-core/pull/6268))

***Fixed***:

* Add `kerberos_cache` to HTTP config options ([#6279](https://github.com/DataDog/integrations-core/pull/6279))

## 3.3.1 / 2020-04-05

***Fixed***:

* Fix e2e config ([#6261](https://github.com/DataDog/integrations-core/pull/6261))

## 3.3.0 / 2020-04-04

***Added***:

* Allow arbitrary repos in CLI config ([#6254](https://github.com/DataDog/integrations-core/pull/6254))
* Add option to set SNI hostname via the `Host` header for RequestsWrapper ([#5833](https://github.com/DataDog/integrations-core/pull/5833))
* Add OpenMetrics config spec template ([#6142](https://github.com/DataDog/integrations-core/pull/6142))
* Add validation for checks to not use the legacy agent signature ([#6086](https://github.com/DataDog/integrations-core/pull/6086))
* Validate `metric_to_check` is listed in `metadata.csv` ([#6170](https://github.com/DataDog/integrations-core/pull/6170))
* Add `display_priority` to config spec ([#6229](https://github.com/DataDog/integrations-core/pull/6229))
* Add `jmx_url` to JMX config spec template ([#6230](https://github.com/DataDog/integrations-core/pull/6230))
* Trigger CI if contents of `tests/` changes ([#6223](https://github.com/DataDog/integrations-core/pull/6223))
* Add `service_check_prefix` config to jmx ([#6163](https://github.com/DataDog/integrations-core/pull/6163))
* Consider log collection for `meta catalog` ([#6191](https://github.com/DataDog/integrations-core/pull/6191))
* Add metadata to integrations catalog ([#6169](https://github.com/DataDog/integrations-core/pull/6169))
* Add `default` value field for config specs ([#6178](https://github.com/DataDog/integrations-core/pull/6178))
* Add utility for temporarily stopping Docker services ([#5715](https://github.com/DataDog/integrations-core/pull/5715))
* Add `ddev test` option to verify support of new metrics ([#6141](https://github.com/DataDog/integrations-core/pull/6141))

***Fixed***:

* Add `send_distribution_sums_as_monotonic` to openmetrics config spec ([#6247](https://github.com/DataDog/integrations-core/pull/6247))
* Include moved files to changed files for testing purposes ([#6174](https://github.com/DataDog/integrations-core/pull/6174))

## 3.2.0 / 2020-03-24

***Added***:

* Use Trello for QA release script ([#6125](https://github.com/DataDog/integrations-core/pull/6125))
* Add script to resolve username from email ([#6099](https://github.com/DataDog/integrations-core/pull/6099))
* Add validation to catch legacy imports ([#6081](https://github.com/DataDog/integrations-core/pull/6081))
* Upgrade and pin mypy to 0.770 ([#6090](https://github.com/DataDog/integrations-core/pull/6090))
* Add config spec option for compact YAML representations of nested arrays ([#6082](https://github.com/DataDog/integrations-core/pull/6082))
* Order changelog entries by type ([#5995](https://github.com/DataDog/integrations-core/pull/5995))
* Upgrade virtualenv to 20.0.8 ([#5980](https://github.com/DataDog/integrations-core/pull/5980))
* Add config spec templates for JMX integrations ([#5978](https://github.com/DataDog/integrations-core/pull/5978))
* Add meta command to fetch JMX info ([#5652](https://github.com/DataDog/integrations-core/pull/5652))
* Add `validate metadata` option to check for more duplicates ([#5803](https://github.com/DataDog/integrations-core/pull/5803))
* Add markdown output support to catalog tool ([#5946](https://github.com/DataDog/integrations-core/pull/5946))
* Bump `datadog-checks-base` version in new integration template ([#5858](https://github.com/DataDog/integrations-core/pull/5858))
* Add config spec support for logs-only integrations ([#5932](https://github.com/DataDog/integrations-core/pull/5932))

***Fixed***:

* Remove logs sourcecategory ([#6121](https://github.com/DataDog/integrations-core/pull/6121))
* Remove reference to check in logs-only template ([#6106](https://github.com/DataDog/integrations-core/pull/6106))
* Fix pathing issues with CI setup script ([#6100](https://github.com/DataDog/integrations-core/pull/6100))
* Bump classifiers ([#6083](https://github.com/DataDog/integrations-core/pull/6083))
* Make aggregator stub support multiple jmx instances ([#5966](https://github.com/DataDog/integrations-core/pull/5966))

## 3.1.0 / 2020-03-02

***Added***:

* Handle logs only integrations for legacy config validator ([#5900](https://github.com/DataDog/integrations-core/pull/5900))
* Allow excluding specific checks when performing bulk releases ([#5878](https://github.com/DataDog/integrations-core/pull/5878))

***Fixed***:

* Pin virtualenv to 20.0.5 ([#5891](https://github.com/DataDog/integrations-core/pull/5891))
* Fix E2E parsing of JMX collector output ([#5849](https://github.com/DataDog/integrations-core/pull/5849))

## 3.0.0 / 2020-02-22

***Changed***:

* Switch to comparing between arbitrary tags/release branches to `ddev release testable` ([#5556](https://github.com/DataDog/integrations-core/pull/5556))

***Added***:

* Add `service` option to default configuration ([#5805](https://github.com/DataDog/integrations-core/pull/5805))
* Add ability for config templates to reference other templates ([#5804](https://github.com/DataDog/integrations-core/pull/5804))
* Better error messages on config specs errors ([#5763](https://github.com/DataDog/integrations-core/pull/5763))
* Add an option to skip environment creation for tests ([#5760](https://github.com/DataDog/integrations-core/pull/5760))
* Create an integration catalog command in ddev ([#5660](https://github.com/DataDog/integrations-core/pull/5660))
* Add tag_prefix argument to the changelog command ([#5741](https://github.com/DataDog/integrations-core/pull/5741))
* Add type checking to integration check template ([#5711](https://github.com/DataDog/integrations-core/pull/5711))
* Refactor root initialization to common utils ([#5705](https://github.com/DataDog/integrations-core/pull/5705))
* Add `agent_requirements.in` to non testable files ([#5693](https://github.com/DataDog/integrations-core/pull/5693))
* Add git dep support to dep validation cmd ([#5692](https://github.com/DataDog/integrations-core/pull/5692))
* Add support for tab completion to CLI ([#5674](https://github.com/DataDog/integrations-core/pull/5674))
* Upgrade virtualenv dependency to 20.x ([#5680](https://github.com/DataDog/integrations-core/pull/5680))

***Fixed***:

* Fix error when scrubbing non-org secrets ([#5827](https://github.com/DataDog/integrations-core/pull/5827))
* Switch to Python 3.8 in check integration template ([#5717](https://github.com/DataDog/integrations-core/pull/5717))
* Switch to Agent 6+ signature in check integration test ([#5718](https://github.com/DataDog/integrations-core/pull/5718))

## 2.4.0 / 2020-02-05

***Added***:

* Upgrade coverage dependency ([#5647](https://github.com/DataDog/integrations-core/pull/5647))

## 2.3.0 / 2020-02-05

***Added***:

* Move CI setup script to ddev ([#5651](https://github.com/DataDog/integrations-core/pull/5651))
* Add `internal` to repo choices ([#5649](https://github.com/DataDog/integrations-core/pull/5649))
* Move remaining flake8 config to .flake8 ([#5635](https://github.com/DataDog/integrations-core/pull/5635))

## 2.2.0 / 2020-02-04

***Added***:

* Ignore `__path__` for type hinting of all integrations ([#5639](https://github.com/DataDog/integrations-core/pull/5639))
* Modify QA release script to create Jira issues instead of Trello cards ([#5457](https://github.com/DataDog/integrations-core/pull/5457))
* Add script to remove all labels from an issue or pull request ([#5636](https://github.com/DataDog/integrations-core/pull/5636))
* Always pass PROGRAM* to tox ([#5631](https://github.com/DataDog/integrations-core/pull/5631))
* Add meta command to upgrade the Python version of all test environments ([#5616](https://github.com/DataDog/integrations-core/pull/5616))
* Use the latest beta release of virtualenv for performance improvements ([#5617](https://github.com/DataDog/integrations-core/pull/5617))
* Add type checking support to Tox plugin ([#5595](https://github.com/DataDog/integrations-core/pull/5595))
* Update `validate agent-reqs` cmd to list unreleased checks ([#5610](https://github.com/DataDog/integrations-core/pull/5610))
* Allow specifying `release changelog` output file ([#5608](https://github.com/DataDog/integrations-core/pull/5608))
* Allow --help for `run` command ([#5602](https://github.com/DataDog/integrations-core/pull/5602))
* Update in-toto and its deps ([#5599](https://github.com/DataDog/integrations-core/pull/5599))

***Fixed***:

* Stop mounting the docker socket to allow jmx tests to pass ([#5601](https://github.com/DataDog/integrations-core/pull/5601))

## 2.1.0 / 2020-01-30

***Added***:

* Support CI validation for internal repo ([#5567](https://github.com/DataDog/integrations-core/pull/5567))
* Make new integrations use config specs ([#5580](https://github.com/DataDog/integrations-core/pull/5580))
* Add --org-name/-o to `env start` ([#5458](https://github.com/DataDog/integrations-core/pull/5458))
* Add some helpful output to ddev env ls command ([#5576](https://github.com/DataDog/integrations-core/pull/5576))
* Add Networks and Processes teams in ddev trello tool ([#5560](https://github.com/DataDog/integrations-core/pull/5560))

***Fixed***:

* Fix metric validation ([#5581](https://github.com/DataDog/integrations-core/pull/5581))
* Avoid long break in error message ([#5575](https://github.com/DataDog/integrations-core/pull/5575))

## 2.0.0 / 2020-01-27

***Changed***:

* Remove Python 2 support from CLI ([#5512](https://github.com/DataDog/integrations-core/pull/5512))

***Added***:

* Add validation for CI infrastructure configuration ([#5479](https://github.com/DataDog/integrations-core/pull/5479))
* Upgrade dependencies ([#5528](https://github.com/DataDog/integrations-core/pull/5528))
* Add service check name validator and sync ([#5501](https://github.com/DataDog/integrations-core/pull/5501))
* Run flake8 after formatting fixes ([#5492](https://github.com/DataDog/integrations-core/pull/5492))
* Add meta command to convert metadata.csv files to Markdown tables ([#5461](https://github.com/DataDog/integrations-core/pull/5461))

***Fixed***:

* Add support for in-toto >= 0.4.2 ([#5497](https://github.com/DataDog/integrations-core/pull/5497))

## 1.4.0 / 2020-01-13

***Added***:

* Validate metric names normalization in metadata.csv ([#5437](https://github.com/DataDog/integrations-core/pull/5437))

***Fixed***:

* Fix function call for `release testable` ([#5432](https://github.com/DataDog/integrations-core/pull/5432))

## 1.3.0 / 2020-01-09

***Added***:

* Add debug option to base ddev command ([#5386](https://github.com/DataDog/integrations-core/pull/5386))
* Add meta command to translate MIB names to OIDs in SNMP profiles ([#5397](https://github.com/DataDog/integrations-core/pull/5397))
* Update license years in integration templates ([#5384](https://github.com/DataDog/integrations-core/pull/5384))

***Fixed***:

* Fix a few style lints to handle Python 2 ([#5389](https://github.com/DataDog/integrations-core/pull/5389))

## 1.2.0 / 2019-12-31

***Changed***:

* Change `wrapper` arg for environment runners to `wrappers` ([#5361](https://github.com/DataDog/integrations-core/pull/5361))

***Added***:

* Add mechanism to cross-mount temporary log files between containers ([#5346](https://github.com/DataDog/integrations-core/pull/5346))

## 1.1.0 / 2019-12-27

***Added***:

* Refactor terraform configs ([#5339](https://github.com/DataDog/integrations-core/pull/5339))
* Make configuration specs an asset ([#5337](https://github.com/DataDog/integrations-core/pull/5337))
* Add meta command to export dashboards ([#5332](https://github.com/DataDog/integrations-core/pull/5332))
* Make changes and changelog command work with other repos ([#5331](https://github.com/DataDog/integrations-core/pull/5331))
* Decrease default verbosity of tracebacks in pytest ([#5291](https://github.com/DataDog/integrations-core/pull/5291))
* Add more global utilities the pytest plugin ([#5283](https://github.com/DataDog/integrations-core/pull/5283))
* Display Docker Compose logs when test environment fails to start ([#5258](https://github.com/DataDog/integrations-core/pull/5258))
* Implement configuration specifications ([#5072](https://github.com/DataDog/integrations-core/pull/5072))
* Add support for switching between multiple orgs' API/APP keys ([#5197](https://github.com/DataDog/integrations-core/pull/5197))

***Fixed***:

* Always pass USERNAME to tox ([#5335](https://github.com/DataDog/integrations-core/pull/5335))
* Fix agent status with ddev ([#5293](https://github.com/DataDog/integrations-core/pull/5293))
* Remove command to validate Python 3 compatibility ([#5246](https://github.com/DataDog/integrations-core/pull/5246))
* Pin coverage to 4.5.4 ([#5224](https://github.com/DataDog/integrations-core/pull/5224))

## 1.0.1 / 2019-12-06

***Fixed***:

* Fix a bug where we accidentally recorded git-ignored files in in-toto ([#5129](https://github.com/DataDog/integrations-core/pull/5129))

## 1.0.0 / 2019-12-02

***Changed***:

* Remove logos folder from template ([#4988](https://github.com/DataDog/integrations-core/pull/4988))
* Remove logo validation ([#4964](https://github.com/DataDog/integrations-core/pull/4964))

***Added***:

* Support downloading universal and pure Python wheels ([#4981](https://github.com/DataDog/integrations-core/pull/4981))
* Support more metric types for `ddev meta prom` ([#5071](https://github.com/DataDog/integrations-core/pull/5071))
* Improve prompts in `ddev clean` ([#5061](https://github.com/DataDog/integrations-core/pull/5061))
* Add command to navigate to config directory ([#5054](https://github.com/DataDog/integrations-core/pull/5054))
* Use a stub class for metadata testing ([#4919](https://github.com/DataDog/integrations-core/pull/4919))
* Add saved_views metadata field to integration templates ([#4584](https://github.com/DataDog/integrations-core/pull/4584))

***Fixed***:

* Handle formatting edge cases for `meta changes` ([#4970](https://github.com/DataDog/integrations-core/pull/4970))
* Never sign an empty release ([#4933](https://github.com/DataDog/integrations-core/pull/4933))
* Update requirements when updating check ([#4895](https://github.com/DataDog/integrations-core/pull/4895))

## 0.39.0 / 2019-10-25

***Added***:

* Add junit option to `ddev env e2e` command ([#4879](https://github.com/DataDog/integrations-core/pull/4879))

***Fixed***:

* Change the team label map for Trello card creation ([#4852](https://github.com/DataDog/integrations-core/pull/4852))
* Update metadata link in template ([#4869](https://github.com/DataDog/integrations-core/pull/4869))

## 0.38.3 / 2019-10-17

***Fixed***:

* Fix CHANGELOG.md template to make it work with `ddev release changelog` ([#4808](https://github.com/DataDog/integrations-core/pull/4808))

## 0.38.2 / 2019-10-17

***Fixed***:

* Handle the case of pylint returning empty output ([#4801](https://github.com/DataDog/integrations-core/pull/4801))

## 0.38.1 / 2019-10-15

***Fixed***:

* Fix ddev testable command to properly use the tag, fallback on the branch if absent ([#4775](https://github.com/DataDog/integrations-core/pull/4775))

## 0.38.0 / 2019-10-11

***Added***:

* Add option for device testing in e2e ([#4693](https://github.com/DataDog/integrations-core/pull/4693))
* Add flake8-logging-format ([#4711](https://github.com/DataDog/integrations-core/pull/4711))

***Fixed***:

* Fix lint flake8-logging-format command ([#4728](https://github.com/DataDog/integrations-core/pull/4728))

## 0.37.0 / 2019-10-09

***Added***:

* Increase default Agent flush timeout ([#4714](https://github.com/DataDog/integrations-core/pull/4714))

***Fixed***:

* Remove default version from env test ([#4718](https://github.com/DataDog/integrations-core/pull/4718))
* Handle other Agent images in E2E ([#4710](https://github.com/DataDog/integrations-core/pull/4710))

## 0.36.0 / 2019-10-07

***Added***:

* Update teams in ddev trello tool ([#4702](https://github.com/DataDog/integrations-core/pull/4702))
* Add dashboard validation ([#4694](https://github.com/DataDog/integrations-core/pull/4694))

***Fixed***:

* Don't use a7 ([#4680](https://github.com/DataDog/integrations-core/pull/4680))

## 0.35.1 / 2019-09-30

***Fixed***:

* Auto detect changes and run tests when yaml files change ([#4657](https://github.com/DataDog/integrations-core/pull/4657))

## 0.35.0 / 2019-09-30

***Added***:

* Support submitting memory profiling metrics during E2E ([#4635](https://github.com/DataDog/integrations-core/pull/4635))

## 0.34.0 / 2019-09-24

***Added***:

* Improve RetryError message ([#4619](https://github.com/DataDog/integrations-core/pull/4619))
* Reload environments if there are extra startup commands ([#4614](https://github.com/DataDog/integrations-core/pull/4614))
* Add warning to create command if name is lowercase ([#4564](https://github.com/DataDog/integrations-core/pull/4564))

## 0.33.0 / 2019-09-19

***Added***:

* Update tooling for Azure Pipelines ([#4536](https://github.com/DataDog/integrations-core/pull/4536))

***Fixed***:

* Stop identifying core vs extras from the working directory name ([#4583](https://github.com/DataDog/integrations-core/pull/4583))

## 0.32.0 / 2019-08-24

***Added***:

* Don't fail e2e on unsupported platforms ([#4398](https://github.com/DataDog/integrations-core/pull/4398))
* Add K8S e2e util ([#4203](https://github.com/DataDog/integrations-core/pull/4203))
* Add SSH port forward e2e util ([#4147](https://github.com/DataDog/integrations-core/pull/4147))
* Deployment environment with Terraform ([#4039](https://github.com/DataDog/integrations-core/pull/4039))
* Support Python 3 when calling pip for extra E2E start up commands ([#4213](https://github.com/DataDog/integrations-core/pull/4213))
* Make `docker_run` clean up volumes and orphaned containers ([#4212](https://github.com/DataDog/integrations-core/pull/4212))
* Allow multiple docker Agents to coexist for E2E by randomly assigning ports ([#4205](https://github.com/DataDog/integrations-core/pull/4205))
* Add docker_volumes option to E2E metadata ([#4178](https://github.com/DataDog/integrations-core/pull/4178))
* Add env check for jmx integrations ([#4146](https://github.com/DataDog/integrations-core/pull/4146))

***Fixed***:

* Use the new Python 2 / 3 Docker images ([#4246](https://github.com/DataDog/integrations-core/pull/4246))
* Don't put integer in environment ([#4234](https://github.com/DataDog/integrations-core/pull/4234))
* Use utcnow instead of now ([#4192](https://github.com/DataDog/integrations-core/pull/4192))

## 0.31.1 / 2019-07-19

***Fixed***:

* Fix get_current_agent_version sorting in ddev ([#4113](https://github.com/DataDog/integrations-core/pull/4113))

## 0.31.0 / 2019-07-13

***Added***:

* Add support for selecting an Agent build via environment ([#4112](https://github.com/DataDog/integrations-core/pull/4112))
* Add ways to control the colorization of output ([#4086](https://github.com/DataDog/integrations-core/pull/4086))
* Support multiple Python versions for E2E ([#4075](https://github.com/DataDog/integrations-core/pull/4075))

## 0.30.1 / 2019-07-04

***Fixed***:

* Fix metadata bootstrap workflow ([#4047](https://github.com/DataDog/integrations-core/pull/4047))

## 0.30.0 / 2019-07-04

***Added***:

* Remove timeout when stopping containers ([#3973](https://github.com/DataDog/integrations-core/pull/3973))

***Fixed***:

* Update wording on installing extras in ddev create command ([#4032](https://github.com/DataDog/integrations-core/pull/4032))

## 0.29.0 / 2019-06-24

***Added***:

* Only sign updated checks ([#3944](https://github.com/DataDog/integrations-core/pull/3944))

## 0.28.0 / 2019-06-19

***Added***:

* Print line number on validate metadata ([#3931](https://github.com/DataDog/integrations-core/pull/3931))

## 0.27.0 / 2019-06-18

***Added***:

* Support E2E testing ([#3896](https://github.com/DataDog/integrations-core/pull/3896))
* Allow releasing multiple checks at once ([#3881](https://github.com/DataDog/integrations-core/pull/3881))

***Fixed***:

* Validate interval in metadata validation ([#3857](https://github.com/DataDog/integrations-core/pull/3857))

## 0.26.1 / 2019-06-05

***Fixed***:

* Fix JMX template ([#3879](https://github.com/DataDog/integrations-core/pull/3879))
* Update APM team label ([#3878](https://github.com/DataDog/integrations-core/pull/3878))
* Fix logic to skip docs PRs for release testing ([#3877](https://github.com/DataDog/integrations-core/pull/3877))

## 0.26.0 / 2019-06-01

***Added***:

* Better error message when releasing on the wrong branch ([#3832](https://github.com/DataDog/integrations-core/pull/3832))

## 0.25.2 / 2019-05-28

***Fixed***:

* Fix tox plugin ([#3825](https://github.com/DataDog/integrations-core/pull/3825))

## 0.25.1 / 2019-05-24

***Fixed***:

* Use safe default when validating manifests ([#3810](https://github.com/DataDog/integrations-core/pull/3810))

## 0.25.0 / 2019-05-20

***Added***:

* Move all assets to a dedicated directory ([#3768](https://github.com/DataDog/integrations-core/pull/3768))
* Upgrade requests to 2.22.0 ([#3778](https://github.com/DataDog/integrations-core/pull/3778))

## 0.24.0 / 2019-05-14

***Added***:

* Ambari integration ([#3670](https://github.com/DataDog/integrations-core/pull/3670))
* Fail if service check file doesn't exist ([#3691](https://github.com/DataDog/integrations-core/pull/3691))
* Add default service check file to new checks templates ([#3726](https://github.com/DataDog/integrations-core/pull/3726))
* Adds ddev YAML config validator ([#3679](https://github.com/DataDog/integrations-core/pull/3679))
* Upgrade pyyaml to 5.1 ([#3698](https://github.com/DataDog/integrations-core/pull/3698))

## 0.23.2 / 2019-04-30

***Fixed***:

* Remove spurious debug line ([#3703](https://github.com/DataDog/integrations-core/pull/3703))

## 0.23.1 / 2019-04-30

***Fixed***:

* Fix creation of jmx & tile integrations ([#3701](https://github.com/DataDog/integrations-core/pull/3701))
* Fix template for new integration to use argument as display name ([#3664](https://github.com/DataDog/integrations-core/pull/3664))

## 0.23.0 / 2019-04-22

***Removed***:

* Remove `pre` from versioning scheme ([#3655](https://github.com/DataDog/integrations-core/pull/3655))

***Added***:

* Add extra type for manifest validation ([#3662](https://github.com/DataDog/integrations-core/pull/3662))
* Adhere to code style ([#3497](https://github.com/DataDog/integrations-core/pull/3497))

***Fixed***:

* Fix changelog generation for new checks ([#3634](https://github.com/DataDog/integrations-core/pull/3634))

## 0.22.0 / 2019-04-15

***Added***:

* Build releases automatically ([#3364](https://github.com/DataDog/integrations-core/pull/3364))
* Add validation on integration_id ([#3598](https://github.com/DataDog/integrations-core/pull/3598))
* Add ability to specify extra start-up commands for e2e ([#3594](https://github.com/DataDog/integrations-core/pull/3594))
* Add a pytest-args option to ddev test ([#3596](https://github.com/DataDog/integrations-core/pull/3596))
* Add posargs in tox.ini ([#3313](https://github.com/DataDog/integrations-core/pull/3313))
* Update version of datadog-checks-base for extras ([#3433](https://github.com/DataDog/integrations-core/pull/3433))

***Fixed***:

* Fixed language in template for integration extras readme ([#3606](https://github.com/DataDog/integrations-core/pull/3606))
* Ensure style envs support every platform ([#3482](https://github.com/DataDog/integrations-core/pull/3482))
* Fix breakpoint agent check flag ([#3447](https://github.com/DataDog/integrations-core/pull/3447))

## 0.21.0 / 2019-03-29

***Added***:

* Upgrade in-toto ([#3411](https://github.com/DataDog/integrations-core/pull/3411))

## 0.20.0 / 2019-03-28

***Added***:

* Remove flake8 from tox.ini template ([#3358](https://github.com/DataDog/integrations-core/pull/3358))
* Support all options for the Agent check command ([#3350](https://github.com/DataDog/integrations-core/pull/3350))
* Add ability to detect if using JMX based on metadata ([#3330](https://github.com/DataDog/integrations-core/pull/3330))
* Add style checker and formatter ([#3299](https://github.com/DataDog/integrations-core/pull/3299))
* Add env var support to E2E containers ([#3263](https://github.com/DataDog/integrations-core/pull/3263))
* Enforce new integration_id field ([#3264](https://github.com/DataDog/integrations-core/pull/3264))
* Add row length validation ([#3266](https://github.com/DataDog/integrations-core/pull/3266))
* Add logo validation ([#3246](https://github.com/DataDog/integrations-core/pull/3246))
* Default to Python 3.7 for new checks ([#3244](https://github.com/DataDog/integrations-core/pull/3244))

***Fixed***:

* Make the aggregator fixture lazily import the stub ([#3308](https://github.com/DataDog/integrations-core/pull/3308))
* Fix sdist build command ([#3252](https://github.com/DataDog/integrations-core/pull/3252))

## 0.19.1 / 2019-03-01

***Fixed***:

* Run upload command in the proper location ([#3239](https://github.com/DataDog/integrations-core/pull/3239))

## 0.19.0 / 2019-03-01

***Added***:

* Add integration_id to manifest validation ([#3232](https://github.com/DataDog/integrations-core/pull/3232))
* Add ability to pass -m & -k to pytest ([#3163](https://github.com/DataDog/integrations-core/pull/3163))
* Provide a way to update to the new agent build config format ([#3181](https://github.com/DataDog/integrations-core/pull/3181))
* Support datadog_checks_downloader ([#3164](https://github.com/DataDog/integrations-core/pull/3164))
* Add util to load jmx metric configs ([#3162](https://github.com/DataDog/integrations-core/pull/3162))

***Fixed***:

* Fix agent changelog command ([#3233](https://github.com/DataDog/integrations-core/pull/3233))
* Properly detect integration folder for py3 validation ([#3188](https://github.com/DataDog/integrations-core/pull/3188))
* Properly ship datadog-checks-downloader ([#3169](https://github.com/DataDog/integrations-core/pull/3169))

## 0.18.0 / 2019-02-18

***Added***:

* Add util to get the directory of current file ([#3135](https://github.com/DataDog/integrations-core/pull/3135))
* Add command to build package wheel ([#3067](https://github.com/DataDog/integrations-core/pull/3067))
* Add datadog-checks-downloader ([#3026](https://github.com/DataDog/integrations-core/pull/3026))
* Add `local` E2E  ([#3064](https://github.com/DataDog/integrations-core/pull/3064))
* Add command to show changes based on commit date ([#3063](https://github.com/DataDog/integrations-core/pull/3063))
* Add e2e command to restart the agent ([#3054](https://github.com/DataDog/integrations-core/pull/3054))
* Upgrade pytest-benchmark ([#2934](https://github.com/DataDog/integrations-core/pull/2934))
* Add description length metadata validation ([#2923](https://github.com/DataDog/integrations-core/pull/2923))
* Allow uploading of any Datadog python package ([#2907](https://github.com/DataDog/integrations-core/pull/2907))
* Upgrade pytest plugins ([#2884](https://github.com/DataDog/integrations-core/pull/2884))

***Fixed***:

* Update e2e start help text for extras integrations ([#3133](https://github.com/DataDog/integrations-core/pull/3133))
* Fix e2e package install order ([#3092](https://github.com/DataDog/integrations-core/pull/3092))

## 0.17.0 / 2019-01-07

***Added***:

* Use standalone py3 validation ([#2854][1])

***Fixed***:

* Fix root folder name when running 'validate' commands on integrations-extras ([#2879][2])
* Pin pytest because of a regression in pytest-benchmark ([#2878][3])

## 0.16.0 / 2018-12-22

***Changed***:

* Rename `ddev release freeze` to `ddev release agent_req_file`, refactor commands code ([#2765][12])

***Added***:

* Remove requirements.txt from check template ([#2816][4])
* Add ability to log warnings during pytest ([#2764][5])
* Update templates for new integrations ([#2794][7])
* Add python3 compatibility validation ([#2736][8])
* Validate checks dependencies against the embedded environment ([#2746][9])
* Add constant to check if platform is Linux ([#2782][10])
* Add validation for configuration files ([#2759][13])
* Add ability to pass state to e2e tear down ([#2724][14])
* Add ability to use dev version of base package for e2e ([#2689][15])

***Fixed***:

* Fix agent_changelog command ([#2808][6])
* Do not consider empty string as a version change ([#2771][11])

## 0.15.1 / 2018-11-30

***Fixed***:

* Handle unreleased checks for agent reqs validation ([#2664][16])

## 0.15.0 / 2018-11-27

***Added***:

* Added Watt units to metadata validation ([#2645][17])
* Added Heap and Volume units to metadata validation ([#2647][18])
* Added validation step for the agent-requirements file ([#2642][20])

***Fixed***:

* Gently handle Yubikey exceptions ([#2641][19])

## 0.14.1 / 2018-11-22

***Fixed***:

* Increase gpg timeout to give time to developers to interact with Yubikeys ([#2613][21])
* Fix requirements-agent-release.txt updating ([#2617][22])

## 0.14.0 / 2018-11-16

***Added***:

* Support agent repo ([#2600][23])
* Improve trello releasing ([#2599][24])
* Refactor validations under `validate` command ([#2593][25])
* Upgrade docker-compose and requests ([#2503][26])
* Disable pytest output capturing when debugging ([#2502][27])
* Support specifying type of semver version bumps ([#2491][28])
* Fix codecov error on appveyor ([#2474][30])
* Add service_checks.json files validation ([#2432][33])
* Make all tox envs available to E2E ([#2457][34])
* Ensure new checks include the E2E fixture ([#2455][35])
* Prevent misconfigured tox files ([#2447][37])

***Fixed***:

* Fixed off-by-one missing latest release ([#2478][29])
* Use raw string literals when \ is present ([#2465][31])
* Improve output of `ddev manifest verify` command ([#2444][32])
* Handle any clipboard errors for E2E ([#2454][36])
* Add `datadog-` prefix to packages name ([#2430][38])

## 0.13.0 / 2018-10-17

***Added***:

* Ensure new checks use editable install of datadog_checks_base for tests ([#2427][39])

***Fixed***:

* Relax e2e config parsing ([#2416][40])
* Fix sleep on WaitFor helper ([#2418][41])

## 0.12.1 / 2018-10-15

***Fixed***:

* Improve handling of github api errors for trello ([#2411][42])
* Make every check's `tests` directory path unique for coverage ([#2406][43])

## 0.12.0 / 2018-10-15

***Added***:

* Support the initial release of integrations ([#2399][45])

***Fixed***:

* Fix trello for issue number in commit message ([#2408][44])

## 0.11.0 / 2018-10-11

***Added***:

* Add E2E support ([#2375][46])
* Ensure new core checks use latest dev package for testing ([#2386][47])
* Support more teams for Trello test cards ([#2365][49])

***Fixed***:

* Normalize line endings for release signing ([#2364][48])

## 0.10.0 / 2018-10-04

***Added***:

* Update base package paths ([#2345][50])
* Add generic environment runner ([#2342][51])
* Add WaitFor environment condition ([#2343][52])
* Enable pytest plugin to control environments ([#2336][53])

## 0.9.0 / 2018-09-30

***Added***:

* Allow testing of specific environments ([#2312][54])
* Add run command ([#2319][55])
* Command to validate metadata ([#2269][58])

***Fixed***:

* Fix namespace overwriting ([#2311][56])
* Upgrade in-toto to gain full cross-platform release signing support ([#2315][57])

## 0.8.1 / 2018-09-25

***Fixed***:

* Fix Python 2 unicode handling for log pattern error message ([#2303][59])

## 0.8.0 / 2018-09-25

***Added***:

* Add new templates for other integration types ([#2285][60])
* Add release signing via in-toto ([#2224][61])
* Add prometheus metadata.csv and metric map auto-generation ([#2117][62])
* Keep track of the checks changed at every Datadog Agent release ([#2277][63])

## 0.7.0 / 2018-09-18

***Added***:

* Fix manifest validation policy ([#2258][64])
* Add config option to select the default repository ([#2243][65])

## 0.6.2 / 2018-09-14

***Fixed***:

* Revert "Update base package paths (#2235)" ([#2240][66])

## 0.6.1 / 2018-09-14

***Fixed***:

* Move datadog_checks_base code into sub base package ([#2167][67])

## 0.6.0 / 2018-09-14

***Added***:

* Update base package paths ([#2235][68])
* Add ability to add wait time in docker_run ([#2196][69])
* Add better debugging to test command ([#2194][70])
* Add ability to filter checks to test by changes ([#2163][73])

***Fixed***:

* Gracefully handle tags that already exist ([#2172][71])
* Fix release freeze command ([#2188][72])

## 0.5.0 / 2018-09-04

***Added***:

* Allow automated releasing by looking at github labels ([#2169][74])

***Fixed***:

* Handle character limit for Trello card descriptions ([#2162][75])

## 0.4.1 / 2018-08-31

***Fixed***:

* Fix trello command for other repos ([#2155][76])

## 0.4.0 / 2018-08-28

***Added***:

* Add code coverage ([#2105][77])
* Add command to create new integrations ([#2037][78])

## 0.3.1 / 2018-08-03

***Fixed***:

* Fix clean command ([#1992][79])

## 0.3.0 / 2018-07-30

***Added***:

* Allow passing --build to compose up ([#1962][80])
* Add command to create Trello test cards from Agent release diffs ([#1934][82])
* Add openldap to the list of agent integrations ([#1923][83])
* Update dep tooling to support environment markers ([#1921][84])

***Fixed***:

* When setting repo paths do not resolve home ([#1953][81])

## 0.2.2 / 2018-07-19

***Fixed***:

* Relax condition error handling to allow more time ([#1914][85])
* Do not skip release builds ([#1913][86])
* Fix packaging of agent requirements ([#1911][87])

## 0.2.1 / 2018-07-17

***Fixed***:

* make remove_path util more resilient to errors ([#1900][88])

## 0.2.0 / 2018-07-17

***Added***:

* improve docker tooling ([#1891][89])

## 0.1.1 / 2018-07-12

***Fixed***:

* fix changed-only test logic ([#1878][90])

## 0.1.0 / 2018-07-12

***Added***:

* Add developer package ([#1862][91])

[1]: https://github.com/DataDog/integrations-core/pull/2854
[2]: https://github.com/DataDog/integrations-core/pull/2879
[3]: https://github.com/DataDog/integrations-core/pull/2878
[4]: https://github.com/DataDog/integrations-core/pull/2816
[5]: https://github.com/DataDog/integrations-core/pull/2764
[6]: https://github.com/DataDog/integrations-core/pull/2808
[7]: https://github.com/DataDog/integrations-core/pull/2794
[8]: https://github.com/DataDog/integrations-core/pull/2736
[9]: https://github.com/DataDog/integrations-core/pull/2746
[10]: https://github.com/DataDog/integrations-core/pull/2782
[11]: https://github.com/DataDog/integrations-core/pull/2771
[12]: https://github.com/DataDog/integrations-core/pull/2765
[13]: https://github.com/DataDog/integrations-core/pull/2759
[14]: https://github.com/DataDog/integrations-core/pull/2724
[15]: https://github.com/DataDog/integrations-core/pull/2689
[16]: https://github.com/DataDog/integrations-core/pull/2664
[17]: https://github.com/DataDog/integrations-core/pull/2645
[18]: https://github.com/DataDog/integrations-core/pull/2647
[19]: https://github.com/DataDog/integrations-core/pull/2641
[20]: https://github.com/DataDog/integrations-core/pull/2642
[21]: https://github.com/DataDog/integrations-core/pull/2613
[22]: https://github.com/DataDog/integrations-core/pull/2617
[23]: https://github.com/DataDog/integrations-core/pull/2600
[24]: https://github.com/DataDog/integrations-core/pull/2599
[25]: https://github.com/DataDog/integrations-core/pull/2593
[26]: https://github.com/DataDog/integrations-core/pull/2503
[27]: https://github.com/DataDog/integrations-core/pull/2502
[28]: https://github.com/DataDog/integrations-core/pull/2491
[29]: https://github.com/DataDog/integrations-core/pull/2478
[30]: https://github.com/DataDog/integrations-core/pull/2474
[31]: https://github.com/DataDog/integrations-core/pull/2465
[32]: https://github.com/DataDog/integrations-core/pull/2444
[33]: https://github.com/DataDog/integrations-core/pull/2432
[34]: https://github.com/DataDog/integrations-core/pull/2457
[35]: https://github.com/DataDog/integrations-core/pull/2455
[36]: https://github.com/DataDog/integrations-core/pull/2454
[37]: https://github.com/DataDog/integrations-core/pull/2447
[38]: https://github.com/DataDog/integrations-core/pull/2430
[39]: https://github.com/DataDog/integrations-core/pull/2427
[40]: https://github.com/DataDog/integrations-core/pull/2416
[41]: https://github.com/DataDog/integrations-core/pull/2418
[42]: https://github.com/DataDog/integrations-core/pull/2411
[43]: https://github.com/DataDog/integrations-core/pull/2406
[44]: https://github.com/DataDog/integrations-core/pull/2408
[45]: https://github.com/DataDog/integrations-core/pull/2399
[46]: https://github.com/DataDog/integrations-core/pull/2375
[47]: https://github.com/DataDog/integrations-core/pull/2386
[48]: https://github.com/DataDog/integrations-core/pull/2364
[49]: https://github.com/DataDog/integrations-core/pull/2365
[50]: https://github.com/DataDog/integrations-core/pull/2345
[51]: https://github.com/DataDog/integrations-core/pull/2342
[52]: https://github.com/DataDog/integrations-core/pull/2343
[53]: https://github.com/DataDog/integrations-core/pull/2336
[54]: https://github.com/DataDog/integrations-core/pull/2312
[55]: https://github.com/DataDog/integrations-core/pull/2319
[56]: https://github.com/DataDog/integrations-core/pull/2311
[57]: https://github.com/DataDog/integrations-core/pull/2315
[58]: https://github.com/DataDog/integrations-core/pull/2269
[59]: https://github.com/DataDog/integrations-core/pull/2303
[60]: https://github.com/DataDog/integrations-core/pull/2285
[61]: https://github.com/DataDog/integrations-core/pull/2224
[62]: https://github.com/DataDog/integrations-core/pull/2117
[63]: https://github.com/DataDog/integrations-core/pull/2277
[64]: https://github.com/DataDog/integrations-core/pull/2258
[65]: https://github.com/DataDog/integrations-core/pull/2243
[66]: https://github.com/DataDog/integrations-core/pull/2240
[67]: https://github.com/DataDog/integrations-core/pull/2167
[68]: https://github.com/DataDog/integrations-core/pull/2235
[69]: https://github.com/DataDog/integrations-core/pull/2196
[70]: https://github.com/DataDog/integrations-core/pull/2194
[71]: https://github.com/DataDog/integrations-core/pull/2172
[72]: https://github.com/DataDog/integrations-core/pull/2188
[73]: https://github.com/DataDog/integrations-core/pull/2163
[74]: https://github.com/DataDog/integrations-core/pull/2169
[75]: https://github.com/DataDog/integrations-core/pull/2162
[76]: https://github.com/DataDog/integrations-core/pull/2155
[77]: https://github.com/DataDog/integrations-core/pull/2105
[78]: https://github.com/DataDog/integrations-core/pull/2037
[79]: https://github.com/DataDog/integrations-core/pull/1992
[80]: https://github.com/DataDog/integrations-core/pull/1962
[81]: https://github.com/DataDog/integrations-core/pull/1953
[82]: https://github.com/DataDog/integrations-core/pull/1934
[83]: https://github.com/DataDog/integrations-core/pull/1923
[84]: https://github.com/DataDog/integrations-core/pull/1921
[85]: https://github.com/DataDog/integrations-core/pull/1914
[86]: https://github.com/DataDog/integrations-core/pull/1913
[87]: https://github.com/DataDog/integrations-core/pull/1911
[88]: https://github.com/DataDog/integrations-core/pull/1900
[89]: https://github.com/DataDog/integrations-core/pull/1891
[90]: https://github.com/DataDog/integrations-core/pull/1878
[91]: https://github.com/DataDog/integrations-core/pull/1862
