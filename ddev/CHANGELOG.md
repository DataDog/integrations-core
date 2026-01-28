# CHANGELOG - ddev

<!-- towncrier release notes start -->

## 14.1.0 / 2025-12-18

***Added***:

* Bump datatog_checks_dev to get its latest features. ([#22171](https://github.com/DataDog/integrations-core/pull/22171))

***Fixed***:

* Ensure correct commit attribution when sending size metrics by requiring an explicit commit in the ddev size status command. ([#21993](https://github.com/DataDog/integrations-core/pull/21993))

## 14.0.2 / 2025-11-21

***Fixed***:

* Bump `datadog-checks-dev` to 35.3.1. ([#21944](https://github.com/DataDog/integrations-core/pull/21944))

## 14.0.1 / 2025-11-19

***Fixed***:

* Add a way for integrations to override their integration name used in the metadata file validation ([#21836](https://github.com/DataDog/integrations-core/pull/21836))
* Upgrade runners to macos-14 due to deprecation of macos-13 ([#21905](https://github.com/DataDog/integrations-core/pull/21905))

## 14.0.0 / 2025-11-10

***Changed***:

* Changed how `ddev` discovers integrations in the repository. Subdirectories are now identified as integrations based on the following rules:
  - Only non-hidden directories are considered for integration status; files are ignored.
  - A directory containing a `manifest.json` is always an integration.
  - A directory without a `manifest.json` is now considered an integration by default. To exclude such a directory, set it to `false` in the `.ddev/config.toml` file under the `[overrides.is-integration]` table. ([#21772](https://github.com/DataDog/integrations-core/pull/21772))
* Avoid relying on the existence of a manifest.json file to validate third party licenses ([#21783](https://github.com/DataDog/integrations-core/pull/21783))

***Added***:

* Ensure ddev understands and differentiate worktrees from other packages ignoring them as possible candidates as integrations source ([#20444](https://github.com/DataDog/integrations-core/pull/20444))
* Add support for the hatch env remove command and provide a method to list environments as models ([#21155](https://github.com/DataDog/integrations-core/pull/21155))
* Bump Python to 3.13 ([#21161](https://github.com/DataDog/integrations-core/pull/21161))
* Adds the new command `ddev ci codeowners` to check repository CODEOWNERS for pull requests, commits, or specific files. ([#21312](https://github.com/DataDog/integrations-core/pull/21312))
* Add option to `ddev size status` to compute dependency sizes from JSON or a commit’s GitHub Actions artifacts ([#21331](https://github.com/DataDog/integrations-core/pull/21331))
* Adds a new method `merge_base` in the `GitRepository` class. ([#21340](https://github.com/DataDog/integrations-core/pull/21340))
* Improve error message when Kind or other dependencies are missing; fix read_text signature for Python 3.12 mypy compatibility ([#21402](https://github.com/DataDog/integrations-core/pull/21402))
* Add context variable to CI validation when checking test-all ([#21441](https://github.com/DataDog/integrations-core/pull/21441))
* Adds a new method `log` in the `GitRepository` class. ([#21512](https://github.com/DataDog/integrations-core/pull/21512))
* Improved logging for the `ddev size` command output ([#21587](https://github.com/DataDog/integrations-core/pull/21587)), ([#21747](https://github.com/DataDog/integrations-core/pull/21747))
* Adds `upgrade-python-version` meta script to automate Python version updates ([#21694](https://github.com/DataDog/integrations-core/pull/21694))
* Bump datadog-checks-dev to 35.3.0+ ([#21815](https://github.com/DataDog/integrations-core/pull/21815))

***Fixed***:

* Fix agent image normalization on `ddev env start` that would force `-py3` suffix in `agent:latest` and confuse `servercore` with a release candidate. ([#20917](https://github.com/DataDog/integrations-core/pull/20917))
* Handle changelog generation for removed integrations ([#21167](https://github.com/DataDog/integrations-core/pull/21167))
* Removes duplicated os.path.join when defining the path for the resolved folder. ([#21234](https://github.com/DataDog/integrations-core/pull/21234))
* Removed the requirement for all files to be committed before sending size metrics to Datadog. ([#21486](https://github.com/DataDog/integrations-core/pull/21486))
* The `ddev size status` now stores temporary files in a temporary directory that is removed when the commands finishes. This prevents littering the local disk with unnecessary files. ([#21496](https://github.com/DataDog/integrations-core/pull/21496))
* Fixed retrieval of previous dependency size calculations so they can be used in CI runs on pushes to master. ([#21536](https://github.com/DataDog/integrations-core/pull/21536))
* Allow trace agent start on configuration override ([#21568](https://github.com/DataDog/integrations-core/pull/21568))
* Fixes duplicate results when filtering specific artifacts in the `ddev size` command ([#21774](https://github.com/DataDog/integrations-core/pull/21774))
* Support CI validation for workflows using pinned commit SHAs instead of @master ([#21818](https://github.com/DataDog/integrations-core/pull/21818))
* Allow the `validate metadata` command to get the metrics-prefix from the repo overrides config in case the manifest file does not exist ([#21820](https://github.com/DataDog/integrations-core/pull/21820))

## 13.0.0 / 2025-08-25

***Removed***:

* Remove `ddev size create-dashboard` ([#20766](https://github.com/DataDog/integrations-core/pull/20766))

***Added***:

* Add support for Vagrant VMs in testing ([#20353](https://github.com/DataDog/integrations-core/pull/20353))
* Adds logic to ensure `ddev size` filters integrations by the specified Python version. ([#20742](https://github.com/DataDog/integrations-core/pull/20742))
* Updated the set of allowed Metric Metadata units with the latest additions ([#21048](https://github.com/DataDog/integrations-core/pull/21048))
* Bump Datadog Checks Dev requirement in DDEV ([#21124](https://github.com/DataDog/integrations-core/pull/21124))
* Add a utils.hatch module to centralize hatch operations ([#21135](https://github.com/DataDog/integrations-core/pull/21135))
* Use ddev to target Agent branch in build_agent.yaml ([#21136](https://github.com/DataDog/integrations-core/pull/21136))

***Fixed***:

* Modify the CI matrix generation by spliting jobs in 2 groups: windows and linux tests. This is done to reduce the number of jobs each workflow runs. ([#20963](https://github.com/DataDog/integrations-core/pull/20963))
* Skip E2E test execution for packages that do not define them. ([#20967](https://github.com/DataDog/integrations-core/pull/20967))
* Add is:pull-request to pull request search to avoid 422s on private repos ([#21021](https://github.com/DataDog/integrations-core/pull/21021))
* Fix ddev env test to respect e2e-env config flag even when an environment is specified ([#21119](https://github.com/DataDog/integrations-core/pull/21119))

## 12.2.0 / 2025-07-31

***Added***:

* Run integration tests in parallel for single integrations ([#20816](https://github.com/DataDog/integrations-core/pull/20816))

## 12.1.0 / 2025-07-15

***Added***:

* Add back F401 rule to the linter ([#20661](https://github.com/DataDog/integrations-core/pull/20661))
* Update ci validation command to account for the new ddev test skip params ([#20705](https://github.com/DataDog/integrations-core/pull/20705))
* Add the skip-ddev option to ci validation script ([#20708](https://github.com/DataDog/integrations-core/pull/20708))

***Fixed***:

* Add rule to lint for relative imports from non parent packages ([#20646](https://github.com/DataDog/integrations-core/pull/20646))
* [MINPROC-2319] remove the integration exception mapper ([#20697](https://github.com/DataDog/integrations-core/pull/20697))

## 12.0.0 / 2025-07-01

***Changed***:

* Replaced multiple format flags with a single `--format` option in the `ddev size` command. ([#20330](https://github.com/DataDog/integrations-core/pull/20330))
* Remove Black dependency from the hatch environment collector in favor of Ruff ([#20451](https://github.com/DataDog/integrations-core/pull/20451))

***Added***:

* Update style dependencies. ([#20312](https://github.com/DataDog/integrations-core/pull/20312))
* - Added `ddev size create-dashboard` to visualize size metrics on the Datadog platform
  - Added `--to-dd-org` option to `ddev size status` to send metrics to Datadog ([#20330](https://github.com/DataDog/integrations-core/pull/20330))
* Add nanodollar as valid metric units ([#20341](https://github.com/DataDog/integrations-core/pull/20341))
* - Adds the required logic to upload historical size metrics to a specified Datadog organization.
  - Updates the CI pipeline to send metrics to Datadog on pushes to the master branch. Note that the metrics may not be fully accurate yet, as dependency sizes could be outdated since the lockfile updates are handled in a separate PR. ([#20431](https://github.com/DataDog/integrations-core/pull/20431))
* Add --fmt-unsafe and --lint-unsafe options to ddev test ([#20451](https://github.com/DataDog/integrations-core/pull/20451))

***Fixed***:

* Update ddev metadata validator to only error on required headers ([#20419](https://github.com/DataDog/integrations-core/pull/20419))
* Use non-dot-prefixed JUnit XML path to avoid ddtrace import errors ([#20435](https://github.com/DataDog/integrations-core/pull/20435))

## 11.4.0 / 2025-05-27

***Added***:

* Allow ddev to override configuration values from a local .ddev.toml file found either in the local directory or any parent directory. This allows modifying ddev behavior when running it in different directories. ([#19877](https://github.com/DataDog/integrations-core/pull/19877))
* Added new commands to track and analyze size changes in integrations and dependencies:
  - **`ddev size status`**: Shows current sizes of all modules.
  - **`ddev size diff [COMMIT_BEFORE] [COMMIT_AFTER]`**: Compares size changes between two commits.
  - **`ddev size timeline {integration | dependency} [INTEGRATION_NAME/DEPENDENCY_NAME]`**: Visualizes the size evolution of a module over time. ([#20128](https://github.com/DataDog/integrations-core/pull/20128))
* Add ZillizCloud requested metric units ([#20195](https://github.com/DataDog/integrations-core/pull/20195))
* Bump datadog-checks-dev version to 35.1 ([#20370](https://github.com/DataDog/integrations-core/pull/20370))

## 11.3.0 / 2025-04-30

***Added***:

* Add support for license-expression when retrieving licenses from PyPi ([#20117](https://github.com/DataDog/integrations-core/pull/20117))

***Fixed***:

* Diasble tag signing in unit tests for release agent CLI command ([#19971](https://github.com/DataDog/integrations-core/pull/19971))

## 11.2.0 / 2025-02-26

***Added***:

* Update version spec for datadog_checks_dev. This adds the new tls_ciphers configuration field and some fixes. ([#19720](https://github.com/DataDog/integrations-core/pull/19720))

***Fixed***:

* Validation error for unknown licenses says how to fix the validation. ([#19566](https://github.com/DataDog/integrations-core/pull/19566))
* Recreate release branch if it already exists. ([#19670](https://github.com/DataDog/integrations-core/pull/19670))

## 11.1.0 / 2025-01-21

***Security***:

* Add FIPS switch ([#19179](https://github.com/DataDog/integrations-core/pull/19179))

***Added***:

* First version of helper for creating logs saved views. ([#17353](https://github.com/DataDog/integrations-core/pull/17353))
* Add script to convert monitor export json into the JSON we can use ([#17936](https://github.com/DataDog/integrations-core/pull/17936))
* Add decimal/binary specific byte units ([#19252](https://github.com/DataDog/integrations-core/pull/19252))

***Fixed***:

* Stop generating Python 2 markers for dependency updates. ([#19386](https://github.com/DataDog/integrations-core/pull/19386))

## 11.0.0 / 2024-12-09

***Removed***:

* Remove manifest validation call that calls deprecated endpoint ([#19208](https://github.com/DataDog/integrations-core/pull/19208))

***Changed***:

* Ddev now uses the macos-13 runner instead of macos-13 for the generated test matrix, because the macos-12 runner is being discontinued by microsoft. ([#19163](https://github.com/DataDog/integrations-core/pull/19163))

***Added***:

* Add unit names for bolívar digital ([#19051](https://github.com/DataDog/integrations-core/pull/19051))
* Bump dependencies for checking and fixing code style ([#19126](https://github.com/DataDog/integrations-core/pull/19126))

## 10.4.0 / 2024-11-13

***Added***:

* Add MIT-0 license ([#18936](https://github.com/DataDog/integrations-core/pull/18936))
* Add units for all circulating currencies ([#18947](https://github.com/DataDog/integrations-core/pull/18947))
* Bump `datadog_checks_dev` to 34.1.0 ([#19049](https://github.com/DataDog/integrations-core/pull/19049))

***Fixed***:

* Don't hardcode location of payload file in script that serves static OpenMetrics payloads. ([#18993](https://github.com/DataDog/integrations-core/pull/18993))

## 10.3.0 / 2024-10-28

***Added***:

* Bump the python version from 3.11 to 3.12 ([#18207](https://github.com/DataDog/integrations-core/pull/18207))
* add bit family as valid units ([#18845](https://github.com/DataDog/integrations-core/pull/18845))
* Bumped datadog_checks_dev version to 34.0.0 ([#18918](https://github.com/DataDog/integrations-core/pull/18918))

## 10.2.0 / 2024-09-05

***Added***:

* Add command to tag the Agent release branch. It supports both RC and final tags, see `ddev release branch tag --help` for more details. ([#18413](https://github.com/DataDog/integrations-core/pull/18413))

## 10.1.0 / 2024-08-15

***Added***:

* Refactored integration name exclusion mapper and add new entries to exclusion mapper ([#18213](https://github.com/DataDog/integrations-core/pull/18213))
* Add new ddtrace license to known licenses ([#18221](https://github.com/DataDog/integrations-core/pull/18221))
* Bump `datadog_checks_dev` requirement ([#18346](https://github.com/DataDog/integrations-core/pull/18346))

***Fixed***:

* Enable local check only after installing it in agent docker container.
  This avoids crashing the container with a version of the check that comes bundled with the agent before we load the local version of the check.
  For now limited to docker since that addresses an immediate CI issue. We'll extend it to native agent once we observe it and iron out any kinks. ([#18271](https://github.com/DataDog/integrations-core/pull/18271))

## 10.0.0 / 2024-08-06

***Removed***:

* Remove `ddev release trello ...` commands. We no longer interact with trello during agent release QA. ([#17615](https://github.com/DataDog/integrations-core/pull/17615))

***Added***:

* Add cli option to override org config value at runtime ([#17932](https://github.com/DataDog/integrations-core/pull/17932))
* Support reading site and api key from org config setting in addition to cli flags. ([#17934](https://github.com/DataDog/integrations-core/pull/17934))
* Add validation for versions in __about__.py and CHANGELOG: `ddev validate version`. ([#18063](https://github.com/DataDog/integrations-core/pull/18063))
* Add joule as valid metric units ([#18147](https://github.com/DataDog/integrations-core/pull/18147))
* Bump datadog_checks_dev dependency to 33.0+ to get new features and bugfixes. ([#18206](https://github.com/DataDog/integrations-core/pull/18206))

***Fixed***:

* Improve messages around dependency spec management ([#17969](https://github.com/DataDog/integrations-core/pull/17969))

## 9.1.0 / 2024-06-25

***Security***:

* Update pydantic to 2.7.3 to address CVE-2024-3772 ([#17802](https://github.com/DataDog/integrations-core/pull/17802))

***Added***:

* Bump datadog_checks_dev requirement ([#17926](https://github.com/DataDog/integrations-core/pull/17926))

***Fixed***:

* Help docs for --compat flag mention it implies --recreate ([#17810](https://github.com/DataDog/integrations-core/pull/17810))
* Replace DD_LOGS_CONFIG_DD_URL with DD_LOGS_CONFIG_LOGS_DD_URL ([#17890](https://github.com/DataDog/integrations-core/pull/17890))

## 9.0.0 / 2024-05-13

***Changed***:

* Bump datadog_checks_dev dependency requirement ([#17551](https://github.com/DataDog/integrations-core/pull/17551))

***Added***:

* Add the ability to expose multiple payloads consecutively with the `serve-openmetrics-payload` command ([#16826](https://github.com/DataDog/integrations-core/pull/16826))
* Add a `config` option to the `serve-openmetrics-payload` script. ([#16836](https://github.com/DataDog/integrations-core/pull/16836))
* Add a constant class with the Agent env variables ([#16844](https://github.com/DataDog/integrations-core/pull/16844))
* Bump black version to 24.2.0 ([#16857](https://github.com/DataDog/integrations-core/pull/16857))
* Add the `all` argument to `ddev test` ([#16859](https://github.com/DataDog/integrations-core/pull/16859))
* Bump ruff to 0.2.1 ([#16866](https://github.com/DataDog/integrations-core/pull/16866))
* Add a command to create the release branch ([#16905](https://github.com/DataDog/integrations-core/pull/16905))
* Do not return an error when running test with `changed` if no integrations were modified ([#17030](https://github.com/DataDog/integrations-core/pull/17030))
* Enforce `metadata.csv` to be sorted by metric names in integrations-core ([#17176](https://github.com/DataDog/integrations-core/pull/17176))
* Allow stopping all running environments at once ([#17215](https://github.com/DataDog/integrations-core/pull/17215))
* Bump ruff to 0.3.3 ([#17244](https://github.com/DataDog/integrations-core/pull/17244))
* Collect all metrics by default for the OpenMetrics integration in the serve payload script ([#17316](https://github.com/DataDog/integrations-core/pull/17316))
* Add sample_tags to metadata validation ([#17521](https://github.com/DataDog/integrations-core/pull/17521))

***Fixed***:

* Github client gracefully handles empty PR descriptions ([#16807](https://github.com/DataDog/integrations-core/pull/16807))
* Extract hardcoded additional integrations from the `validate labeler` command to the config file ([#16845](https://github.com/DataDog/integrations-core/pull/16845))
* Extract hardcoded dependencies from the `dep updates` command to the config file ([#16846](https://github.com/DataDog/integrations-core/pull/16846))
* Remove references to the old validate manifest command ([#17019](https://github.com/DataDog/integrations-core/pull/17019))
* Fix a deprecation warning ([#17021](https://github.com/DataDog/integrations-core/pull/17021))
* Remove tox references ([#17068](https://github.com/DataDog/integrations-core/pull/17068))
* Fix the validation of metadata files ([#17136](https://github.com/DataDog/integrations-core/pull/17136))
* `ddev changelog new` docs say changelog entries are in Markdown format. ([#17222](https://github.com/DataDog/integrations-core/pull/17222))
* Bump datadog_checks_dev required version ([#17255](https://github.com/DataDog/integrations-core/pull/17255))
* Update the ruff command for ruff 0.3.3 ([#17257](https://github.com/DataDog/integrations-core/pull/17257))
* Fix sentence in test command docstring ([#17270](https://github.com/DataDog/integrations-core/pull/17270))
* Do not open the editor if no changelog should be generated in the changelog new command ([#17348](https://github.com/DataDog/integrations-core/pull/17348))

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
