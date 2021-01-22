# CHANGELOG - Datadog Checks Dev

## 7.0.0 / 2021-01-22

* [Added] Add --export-csv option. See [#8350](https://github.com/DataDog/integrations-core/pull/8350).
* [Added] Add config spec support for options with multiple types. See [#8378](https://github.com/DataDog/integrations-core/pull/8378).
* [Added] Add docs spec progress to docs status board. See [#8357](https://github.com/DataDog/integrations-core/pull/8357).
* [Added] Add option to exclude release prs. See [#8351](https://github.com/DataDog/integrations-core/pull/8351).
* [Added] Support installing minimum and unpinned datadog_checks_base dependencies for tests. See [#8318](https://github.com/DataDog/integrations-core/pull/8318).
* [Added] Allow MockResponse method `iter_lines` to be called multiple times. See [#8353](https://github.com/DataDog/integrations-core/pull/8353).
* [Added] [1/3] Add units to metadata check. See [#8308](https://github.com/DataDog/integrations-core/pull/8308).
* [Added] Add version verification for datadog-checks-base. See [#8255](https://github.com/DataDog/integrations-core/pull/8255).
* [Added] Support nightly datadog_checks_base package checks. See [#8293](https://github.com/DataDog/integrations-core/pull/8293).
* [Added] Add snmp_tile template to ddev create --type. See [#8216](https://github.com/DataDog/integrations-core/pull/8216).
* [Added] Add new global fixture to mock HTTP requests. See [#8276](https://github.com/DataDog/integrations-core/pull/8276).
* [Added] Update Codecov config validation with new flag carryforward options. See [#8085](https://github.com/DataDog/integrations-core/pull/8085).
* [Added] Ensure default templates are included in config spec. See [#8232](https://github.com/DataDog/integrations-core/pull/8232).
* [Fixed] Update logs template with docs feedback. See [#8412](https://github.com/DataDog/integrations-core/pull/8412).
* [Fixed] Fix conflicting link references in tile readme template. See [#8409](https://github.com/DataDog/integrations-core/pull/8409).
* [Fixed] Update logs readme template. See [#8399](https://github.com/DataDog/integrations-core/pull/8399).
* [Fixed] Increase indentation of log snippets. See [#8360](https://github.com/DataDog/integrations-core/pull/8360).
* [Fixed] Fix dep validation to work on single checks for PRs. See [#8297](https://github.com/DataDog/integrations-core/pull/8297).
* [Fixed] Fix ddev env test last error. See [#8264](https://github.com/DataDog/integrations-core/pull/8264).
* [Fixed] Update prometheus_metrics_prefix documentation. See [#8236](https://github.com/DataDog/integrations-core/pull/8236).
* [Changed] Rename legacy OpenMetrics config spec. See [#8413](https://github.com/DataDog/integrations-core/pull/8413).
* [Changed] Small changes in template for "SNMP tiles". See [#8289](https://github.com/DataDog/integrations-core/pull/8289).

## 6.1.0 / 2020-12-22

* [Added] Add metric_to_check validation redirection for snmp_<vendor> integrations. See [#8215](https://github.com/DataDog/integrations-core/pull/8215).
* [Added] Add exec command option to ddev env shell. See [#8235](https://github.com/DataDog/integrations-core/pull/8235).
* [Added] Fail validation if metadata file is empty. See [#8194](https://github.com/DataDog/integrations-core/pull/8194).
* [Fixed] Fix release. See [#8237](https://github.com/DataDog/integrations-core/pull/8237).
* [Fixed] Update dogweb dashboard list. See [#8191](https://github.com/DataDog/integrations-core/pull/8191).

## 6.0.0 / 2020-12-11

* [Added] Document new collect_default_jvm_metrics flag for JMXFetch integrations. See [#8153](https://github.com/DataDog/integrations-core/pull/8153).
* [Added] Add support for tabular check output. See [#8129](https://github.com/DataDog/integrations-core/pull/8129).
* [Added] Add test filter to env test. See [#8101](https://github.com/DataDog/integrations-core/pull/8101).
* [Added] [SNMP] Generate profiles from MIBs. See [#7925](https://github.com/DataDog/integrations-core/pull/7925).
* [Added] Validate partner integration readmes contain an h2 support section. See [#8055](https://github.com/DataDog/integrations-core/pull/8055).
* [Added] Add 'since' flag to manually specify tag to look from. See [#7950](https://github.com/DataDog/integrations-core/pull/7950).
* [Added] Support inline comment to skip http validation. See [#8020](https://github.com/DataDog/integrations-core/pull/8020).
* [Added] Add config template for TLS helper. See [#8014](https://github.com/DataDog/integrations-core/pull/8014).
* [Fixed] Refactor `has_logs` utility. See [#8123](https://github.com/DataDog/integrations-core/pull/8123).
* [Fixed] Build developer docs in strict mode. See [#8152](https://github.com/DataDog/integrations-core/pull/8152).
* [Fixed] Skip auto-setting Python version suffix if using an RC build. See [#7653](https://github.com/DataDog/integrations-core/pull/7653).
* [Fixed] Remove active_directory references from config. See [#8111](https://github.com/DataDog/integrations-core/pull/8111).
* [Fixed] Fix pdh configuration spec. See [#8106](https://github.com/DataDog/integrations-core/pull/8106).
* [Fixed] Update small typo in tls-specific options documentation. See [#8103](https://github.com/DataDog/integrations-core/pull/8103).
* [Fixed] [Config specs] Allow longer line in compact_example lists. See [#8015](https://github.com/DataDog/integrations-core/pull/8015).
* [Fixed] Include openmetrics integrations in http validation. See [#7999](https://github.com/DataDog/integrations-core/pull/7999).
* [Changed] Use snmp mibs copy while mibs.snmplabs.com is down. See [#7835](https://github.com/DataDog/integrations-core/pull/7835).
* [Changed] Add sub-watt metric metadata units. See [#7994](https://github.com/DataDog/integrations-core/pull/7994).

## 5.1.0 / 2020-11-10

* [Added] Allow mechanism for handling duplicate option names for config specs. See [#7968](https://github.com/DataDog/integrations-core/pull/7968).
* [Added] Add Infra Integrations to Trello release script. See [#7906](https://github.com/DataDog/integrations-core/pull/7906).
* [Fixed] Fix http validator. See [#7936](https://github.com/DataDog/integrations-core/pull/7936).
* [Fixed] Fix Trello release script. See [#7909](https://github.com/DataDog/integrations-core/pull/7909).

## 5.0.0 / 2020-10-31

* [Added] add options method for validation. See [#7895](https://github.com/DataDog/integrations-core/pull/7895).
* [Added] Sync openmetrics config specs with new option ignore_metrics_by_labels. See [#7823](https://github.com/DataDog/integrations-core/pull/7823).
* [Added] Tracemalloc: Rename white/blacklist to include/exclude. See [#7626](https://github.com/DataDog/integrations-core/pull/7626).
* [Added] Detect and abort if there are tox errors. See [#7801](https://github.com/DataDog/integrations-core/pull/7801).
* [Added] Add fixed_cards_mover.py. See [#7724](https://github.com/DataDog/integrations-core/pull/7724).
* [Added] Add warning when running environment without dev flag for non-core integrations. See [#7811](https://github.com/DataDog/integrations-core/pull/7811).
* [Changed] Use creation, update and closed date to detect user inactivity.. See [#7771](https://github.com/DataDog/integrations-core/pull/7771).

## 4.2.0 / 2020-10-14

* [Added] Validate JMX integrations metrics.yaml. See [#7733](https://github.com/DataDog/integrations-core/pull/7733).
* [Added] Make inventories metadata testable in e2e. See [#7761](https://github.com/DataDog/integrations-core/pull/7761).
* [Added] Validate metrics_metadata in manifest.json. See [#7746](https://github.com/DataDog/integrations-core/pull/7746).
* [Added] Add ability to dynamically get authentication information. See [#7660](https://github.com/DataDog/integrations-core/pull/7660).
* [Added] Check the git token scope when calling `get_team_members`. See [#7712](https://github.com/DataDog/integrations-core/pull/7712).
* [Added] [doc] Add encoding in log config sample. See [#7708](https://github.com/DataDog/integrations-core/pull/7708).

## 4.1.0 / 2020-10-01

* [Added] Added HTTP wrapper class validator. See [#7676](https://github.com/DataDog/integrations-core/pull/7676).
* [Fixed] Added missing HTTP templates to existing config specs. See [#7694](https://github.com/DataDog/integrations-core/pull/7694).
* [Fixed] Handle missing "eula" key in EULA validation. See [#7640](https://github.com/DataDog/integrations-core/pull/7640).
* [Fixed] Check case of integration header in metadata.csv files for metadata validation. See [#7643](https://github.com/DataDog/integrations-core/pull/7643).

## 4.0.1 / 2020-09-21

* [Fixed] Fix changed manifest validation for new integrations. See [#7623](https://github.com/DataDog/integrations-core/pull/7623).

## 4.0.0 / 2020-09-16

* [Changed] Use `git diff` instead of GitHub's API to detect if manifest fields changed during validation. See [#7599](https://github.com/DataDog/integrations-core/pull/7599).

## 3.25.0 / 2020-09-16

* [Added] Allow `ddev create` to create marketplace integration scaffolding. See [#7543](https://github.com/DataDog/integrations-core/pull/7543).
* [Added] Remove transient dependency pin. See [#7545](https://github.com/DataDog/integrations-core/pull/7545).
* [Added] [config specs] Support overrides for mappings when references start with a name. See [#7557](https://github.com/DataDog/integrations-core/pull/7557).
* [Added] Add command to add Agent version to integrations CHANGELOG.md. See [#7518](https://github.com/DataDog/integrations-core/pull/7518).
* [Fixed] Fix init_config/db config spec template. See [#7583](https://github.com/DataDog/integrations-core/pull/7583).
* [Fixed] Use database config template in existing specs. See [#7548](https://github.com/DataDog/integrations-core/pull/7548).
* [Fixed] Upgrade isort. See [#7539](https://github.com/DataDog/integrations-core/pull/7539).

## 3.24.0 / 2020-09-08

* [Added] Add marketplace to repo choices and make -x set repo_choice. See [#7508](https://github.com/DataDog/integrations-core/pull/7508).
* [Fixed] Pin transient dependency pyrsistent to < 0.17.0. See [#7546](https://github.com/DataDog/integrations-core/pull/7546).
* [Fixed] Add minItems to pricing and better validation error message. See [#7514](https://github.com/DataDog/integrations-core/pull/7514).
* [Fixed] Do not render null defaults for config spec example consumer. See [#7503](https://github.com/DataDog/integrations-core/pull/7503).

## 3.23.0 / 2020-09-04

* [Added] Add initial validations for EULA files. See [#7473](https://github.com/DataDog/integrations-core/pull/7473).
* [Added] Add RequestsWrapper option to support UTF-8 for basic auth. See [#7441](https://github.com/DataDog/integrations-core/pull/7441).
* [Added] Change old_payload warning to failure. See [#7419](https://github.com/DataDog/integrations-core/pull/7419).
* [Added] Support service checks in recommended monitors. See [#7423](https://github.com/DataDog/integrations-core/pull/7423).
* [Fixed] Apply overrides recursively to config specs. See [#7497](https://github.com/DataDog/integrations-core/pull/7497).
* [Fixed] Pin style deps. See [#7485](https://github.com/DataDog/integrations-core/pull/7485).
* [Fixed] Fix ddev create for jmx. See [#7346](https://github.com/DataDog/integrations-core/pull/7346).
* [Fixed] Fix style for the latest release of Black. See [#7438](https://github.com/DataDog/integrations-core/pull/7438).

## 3.22.0 / 2020-08-24

* [Added] Auto assign card. See [#7347](https://github.com/DataDog/integrations-core/pull/7347).
* [Added] Use author_name instead of author_info object. See [#7417](https://github.com/DataDog/integrations-core/pull/7417).
* [Added] Update dependency tooling to support multiple version/marker combinations. See [#7391](https://github.com/DataDog/integrations-core/pull/7391).
* [Fixed] Add security team. See [#7357](https://github.com/DataDog/integrations-core/pull/7357).
* [Fixed] Update proxy section in conf.yaml. See [#7336](https://github.com/DataDog/integrations-core/pull/7336).
* [Fixed] Use consistent formatting for boolean values. See [#7405](https://github.com/DataDog/integrations-core/pull/7405).

## 3.21.0 / 2020-08-18

* [Added] Update dash export command to use newer api. See [#7365](https://github.com/DataDog/integrations-core/pull/7365).
* [Added] Allow the validation of the newer dashboard payload in integration boards. See [#7362](https://github.com/DataDog/integrations-core/pull/7362).
* [Added] Add new package validation for `name` field in setup.py. See [#7359](https://github.com/DataDog/integrations-core/pull/7359).
* [Added] Add monitor validation on allowed types and more friendly error messages. See [#7356](https://github.com/DataDog/integrations-core/pull/7356).
* [Added] Validate integration column in metrics metadata. See [#7372](https://github.com/DataDog/integrations-core/pull/7372).
* [Added] Support updating Agent /etc/hosts in E2E envs. See [#7343](https://github.com/DataDog/integrations-core/pull/7343).
* [Fixed] Fix intg-tools-libs entry in trello.py. See [#7335](https://github.com/DataDog/integrations-core/pull/7335).

## 3.20.0 / 2020-08-11

* [Added] Validate the monitor id isn't in the payload. See [#7341](https://github.com/DataDog/integrations-core/pull/7341).
* [Fixed] ddev for extras must not rewrite line endings. See [#7344](https://github.com/DataDog/integrations-core/pull/7344).
* [Fixed] Clean http config whitespaces. See [#7339](https://github.com/DataDog/integrations-core/pull/7339).

## 3.19.0 / 2020-08-07

* [Added] Add show warnings option to validate metadata. See [#7310](https://github.com/DataDog/integrations-core/pull/7310).
* [Added] Enable histogram for pytest-benchmark. See [#7301](https://github.com/DataDog/integrations-core/pull/7301).

## 3.18.1 / 2020-08-05

* [Fixed] Update logs config service field to optional. See [#7209](https://github.com/DataDog/integrations-core/pull/7209).

## 3.18.0 / 2020-08-05

* [Added] Add validation for recommended monitors. See [#7280](https://github.com/DataDog/integrations-core/pull/7280).
* [Added] Refactor logic for getting assets. See [#7282](https://github.com/DataDog/integrations-core/pull/7282).
* [Added] Convert jmx to in-app types for replay_check_run. See [#7275](https://github.com/DataDog/integrations-core/pull/7275).
* [Added] Add minimum length to required strings in manifest validation. See [#7281](https://github.com/DataDog/integrations-core/pull/7281).
* [Added] Add self.instance comment to check template. See [#7256](https://github.com/DataDog/integrations-core/pull/7256).
* [Fixed] Make logs attribute optional in manifest. See [#7287](https://github.com/DataDog/integrations-core/pull/7287).
* [Fixed] Fix TOX_SKIP_ENV filtering. See [#7274](https://github.com/DataDog/integrations-core/pull/7274).
* [Fixed] Support TOX_SKIP_ENV var in e2e tests. See [#7269](https://github.com/DataDog/integrations-core/pull/7269).

## 3.17.0 / 2020-08-03

* [Added] Validate dashboards are using the screen API. See [#7237](https://github.com/DataDog/integrations-core/pull/7237).
* [Added] Update RC build cards when running `ddev release trello testable`. See [#7082](https://github.com/DataDog/integrations-core/pull/7082).
* [Added] Add "ddev config edit" subcommand. See [#7217](https://github.com/DataDog/integrations-core/pull/7217).

## 3.16.0 / 2020-07-24

* [Added] Add validation for readmes. See [#7088](https://github.com/DataDog/integrations-core/pull/7088).
* [Added] Option to skip semver version validation in changelog command when specifying old version. See [#7200](https://github.com/DataDog/integrations-core/pull/7200).
* [Added] Add more manifest validations for ddev. See [#7142](https://github.com/DataDog/integrations-core/pull/7142).
* [Fixed] Allow codeowner validation to fail on CI . See [#7207](https://github.com/DataDog/integrations-core/pull/7207).

## 3.15.0 / 2020-07-22

* [Added] Add validation script for codeowners. See [#6071](https://github.com/DataDog/integrations-core/pull/6071).
* [Added] Allow "noqa" for long spec descriptions. See [#7177](https://github.com/DataDog/integrations-core/pull/7177).
* [Added] Support "*" wildcard in type_overrides configuration. See [#7071](https://github.com/DataDog/integrations-core/pull/7071).
* [Added] Skip PRs tagged with skip-qa. See [#7147](https://github.com/DataDog/integrations-core/pull/7147).
* [Added] Report process signatures status. See [#7148](https://github.com/DataDog/integrations-core/pull/7148).
* [Fixed] DOCS-838 Template wording. See [#7038](https://github.com/DataDog/integrations-core/pull/7038).

## 3.14.2 / 2020-07-14

* [Fixed] Allow ddev release to commit directly to master for extras integrations. See [#7127](https://github.com/DataDog/integrations-core/pull/7127).

## 3.14.1 / 2020-07-14

* [Fixed] Fix ddev release extras. See [#7124](https://github.com/DataDog/integrations-core/pull/7124).

## 3.14.0 / 2020-07-14

* [Added] Add ddev release-stats tool for agent's release. See [#6850](https://github.com/DataDog/integrations-core/pull/6850).
* [Added] Add shell subcommand to ddev env. See [#7067](https://github.com/DataDog/integrations-core/pull/7067).
* [Added] Add `Inbox` column to `ddev release trello status` output. See [#7033](https://github.com/DataDog/integrations-core/pull/7033).
* [Fixed] Fix ddev release tag dryrun. See [#7121](https://github.com/DataDog/integrations-core/pull/7121).
* [Fixed] Update ntlm_domain example. See [#7118](https://github.com/DataDog/integrations-core/pull/7118).
* [Fixed] Remove validation on formatting of public title. See [#7107](https://github.com/DataDog/integrations-core/pull/7107).
* [Fixed] Add empty example dashboards and images to ddev create templates. See [#7039](https://github.com/DataDog/integrations-core/pull/7039).
* [Fixed] Add new_gc_metrics to all jmx integrations. See [#7073](https://github.com/DataDog/integrations-core/pull/7073).
* [Fixed] Update docstring to use trello subcommand . See [#7009](https://github.com/DataDog/integrations-core/pull/7009).
* [Fixed] Add assert_metrics_using_metadata to template. See [#7081](https://github.com/DataDog/integrations-core/pull/7081).
* [Fixed] Remove deprecated isort recursive option. See [#7060](https://github.com/DataDog/integrations-core/pull/7060).
* [Fixed] Clean before building wheel. See [#7052](https://github.com/DataDog/integrations-core/pull/7052).
* [Fixed] Sync example config with JMX template. See [#7014](https://github.com/DataDog/integrations-core/pull/7014).
* [Fixed] Run manifest validations again. See [#7015](https://github.com/DataDog/integrations-core/pull/7015).

## 3.13.0 / 2020-06-29

* [Added] Add note about warning concurrency. See [#6967](https://github.com/DataDog/integrations-core/pull/6967).
* [Added] Add tools and libraries team to trello. See [#6968](https://github.com/DataDog/integrations-core/pull/6968).
* [Fixed] Assert new jvm metrics. See [#6996](https://github.com/DataDog/integrations-core/pull/6996).
* [Fixed] Fix elastic and redis dashboards name. See [#6962](https://github.com/DataDog/integrations-core/pull/6962).
* [Fixed] More accurately determine if an integration has a dashboard. See [#6946](https://github.com/DataDog/integrations-core/pull/6946).

## 3.12.0 / 2020-06-23

* [Added] Add `--dirty` option to speed up docs dev reloads. See [#6939](https://github.com/DataDog/integrations-core/pull/6939).
* [Fixed] Expand user paths correctly for legacy E2E config. See [#6940](https://github.com/DataDog/integrations-core/pull/6940).
* [Fixed] Fix template specs typos. See [#6912](https://github.com/DataDog/integrations-core/pull/6912).

## 3.11.0 / 2020-06-11

* [Added] Add automated signing workflow for non-core integrations. See [#6868](https://github.com/DataDog/integrations-core/pull/6868).
* [Added] Allow ddev release command to work for different organizations. See [#6855](https://github.com/DataDog/integrations-core/pull/6855).
* [Added] Add extra validation to manifest files for fields that cannot change. See [#6848](https://github.com/DataDog/integrations-core/pull/6848).
* [Added] Validate that dashboards have required fields. See [#6833](https://github.com/DataDog/integrations-core/pull/6833).
* [Fixed] Provide helpful error message when releasing a project with missing or improper tags. See [#6861](https://github.com/DataDog/integrations-core/pull/6861).
* [Fixed] Adjust jmxfetch config. See [#6864](https://github.com/DataDog/integrations-core/pull/6864).
* [Fixed] Remove unused dashboard fields in export. See [#6787](https://github.com/DataDog/integrations-core/pull/6787).

## 3.10.0 / 2020-06-08

* [Added] Add option to open DogStatsD port on agent. See [#6777](https://github.com/DataDog/integrations-core/pull/6777).
* [Added] Support releasing non-core checks. See [#6805](https://github.com/DataDog/integrations-core/pull/6805).
* [Fixed] Don't error when setting an invalid repo in config. See [#6786](https://github.com/DataDog/integrations-core/pull/6786).
* [Fixed] Fix `ensure_default_envdir` tox plugin flag. See [#6817](https://github.com/DataDog/integrations-core/pull/6817).

## 3.9.1 / 2020-06-03

* [Fixed] Fix new Check template. See [#6811](https://github.com/DataDog/integrations-core/pull/6811).

## 3.9.0 / 2020-06-03

* [Added] Speed up test suites by using a single virtual environment per Python version. See [#6789](https://github.com/DataDog/integrations-core/pull/6789).
* [Added] Add validation for saved views. See [#6783](https://github.com/DataDog/integrations-core/pull/6783).

## 3.8.0 / 2020-06-01

* [Added] Update CLI dependencies. See [#6784](https://github.com/DataDog/integrations-core/pull/6784).
* [Added] Update default E2E Agent configuration. See [#6771](https://github.com/DataDog/integrations-core/pull/6771).
* [Added] Condense output of Trello release status command. See [#6755](https://github.com/DataDog/integrations-core/pull/6755).
* [Added] Add Codecov config validation. See [#6749](https://github.com/DataDog/integrations-core/pull/6749).
* [Added] Add ability to generate docs site as a PDF. See [#6719](https://github.com/DataDog/integrations-core/pull/6719).
* [Added] Remove instance argument from new Check template. See [#6673](https://github.com/DataDog/integrations-core/pull/6673).
* [Added] Add author and labels to Trello release cards. See [#6694](https://github.com/DataDog/integrations-core/pull/6694).
* [Added] Better error output when CheckCommandOutput fails. See [#6674](https://github.com/DataDog/integrations-core/pull/6674).
* [Fixed] Build packages with the current Python. See [#6770](https://github.com/DataDog/integrations-core/pull/6770).

## 3.7.1 / 2020-05-18

* [Fixed] Sync JMX template example config. See [#6676](https://github.com/DataDog/integrations-core/pull/6676).

## 3.7.0 / 2020-05-17

* [Added] Add send_monotonic_with_gauge config option and refactor test. See [#6618](https://github.com/DataDog/integrations-core/pull/6618).
* [Added] Add developer docs. See [#6623](https://github.com/DataDog/integrations-core/pull/6623).

## 3.6.0 / 2020-05-14

* [Added] Add Trello release status subcommand. See [#6628](https://github.com/DataDog/integrations-core/pull/6628).
* [Added] Add environment runner for Kubernetes' `kind`. See [#6522](https://github.com/DataDog/integrations-core/pull/6522).
* [Added] Update JMX template to use JMX config spec. See [#6611](https://github.com/DataDog/integrations-core/pull/6611).
* [Added] Install checks' dependencies for E2E using `deps` extra feature. See [#6599](https://github.com/DataDog/integrations-core/pull/6599).
* [Added] Allow optional dependency installation for all checks. See [#6589](https://github.com/DataDog/integrations-core/pull/6589).
* [Added] Support more tag formats when generating changelogs. See [#6584](https://github.com/DataDog/integrations-core/pull/6584).
* [Added] Add dedicated config section for E2E agent selection. See [#6558](https://github.com/DataDog/integrations-core/pull/6558).
* [Added] Provide a good default for `service` field of E2E logs config. See [#6557](https://github.com/DataDog/integrations-core/pull/6557).
* [Added] Add retry to docker_run. See [#6514](https://github.com/DataDog/integrations-core/pull/6514).
* [Added] Include uncommitted git files to files_changed. See [#6480](https://github.com/DataDog/integrations-core/pull/6480).
* [Added] Add constant for jmx default metrics. See [#6507](https://github.com/DataDog/integrations-core/pull/6507).
* [Added] Make integration template adhere to file name conventions. See [#6493](https://github.com/DataDog/integrations-core/pull/6493).
* [Added] Add rmi_connection_timeout & rmi_client_timeout to config spec. See [#6459](https://github.com/DataDog/integrations-core/pull/6459).
* [Added] Update `release make` to avoid committing new files. See [#6263](https://github.com/DataDog/integrations-core/pull/6263).
* [Added] Add validation for per_unit_name and line numbers for all errors. See [#6394](https://github.com/DataDog/integrations-core/pull/6394).
* [Added] Validate metrics using metadata.csv. See [#6027](https://github.com/DataDog/integrations-core/pull/6027).
* [Added] Add verbose mode to validate config. See [#6302](https://github.com/DataDog/integrations-core/pull/6302).
* [Added] Validate metadata doesn't contain `|`. See [#6333](https://github.com/DataDog/integrations-core/pull/6333).
* [Fixed] Fix style to account for new flake8 rules. See [#6620](https://github.com/DataDog/integrations-core/pull/6620).
* [Fixed] Fix typo in README template for new community integrations. See [#6585](https://github.com/DataDog/integrations-core/pull/6585).
* [Fixed] Remove metrics file from JMX template's config spec. See [#6559](https://github.com/DataDog/integrations-core/pull/6559).
* [Fixed] Remove `dd_check_types` from check template. See [#6460](https://github.com/DataDog/integrations-core/pull/6460).
* [Fixed] Remove `metrics.yaml` from non testable files. See [#6280](https://github.com/DataDog/integrations-core/pull/6280).
* [Fixed] Hide openmetrics template options that are typically overridden. See [#6338](https://github.com/DataDog/integrations-core/pull/6338).

## 3.5.0 / 2020-04-14

* [Added] Update documentation links in new integration templates. See [#6294](https://github.com/DataDog/integrations-core/pull/6294).
* [Added] Add validation for Unicode characters in metric metadata. See [#6318](https://github.com/DataDog/integrations-core/pull/6318).
* [Added] Add default template to openmetrics & jmx config. See [#6328](https://github.com/DataDog/integrations-core/pull/6328).
* [Added] Add config spec ability to control whether options are enabled by default. See [#6322](https://github.com/DataDog/integrations-core/pull/6322).
* [Added] Allow `dd_environment` fixtures to accept arbitrary arguments. See [#6306](https://github.com/DataDog/integrations-core/pull/6306).

## 3.4.0 / 2020-04-08

* [Added] Add Container App team to ddev trello tool. See [#6268](https://github.com/DataDog/integrations-core/pull/6268).
* [Fixed] Add `kerberos_cache` to HTTP config options. See [#6279](https://github.com/DataDog/integrations-core/pull/6279).

## 3.3.1 / 2020-04-05

* [Fixed] Fix e2e config. See [#6261](https://github.com/DataDog/integrations-core/pull/6261).

## 3.3.0 / 2020-04-04

* [Added] Allow arbitrary repos in CLI config. See [#6254](https://github.com/DataDog/integrations-core/pull/6254).
* [Added] Add option to set SNI hostname via the `Host` header for RequestsWrapper. See [#5833](https://github.com/DataDog/integrations-core/pull/5833).
* [Added] Add OpenMetrics config spec template. See [#6142](https://github.com/DataDog/integrations-core/pull/6142).
* [Added] Add validation for checks to not use the legacy agent signature. See [#6086](https://github.com/DataDog/integrations-core/pull/6086).
* [Added] Validate `metric_to_check` is listed in `metadata.csv`. See [#6170](https://github.com/DataDog/integrations-core/pull/6170).
* [Added] Add `display_priority` to config spec. See [#6229](https://github.com/DataDog/integrations-core/pull/6229).
* [Added] Add `jmx_url` to JMX config spec template. See [#6230](https://github.com/DataDog/integrations-core/pull/6230).
* [Added] Trigger CI if contents of `tests/` changes. See [#6223](https://github.com/DataDog/integrations-core/pull/6223).
* [Added] Add `service_check_prefix` config to jmx. See [#6163](https://github.com/DataDog/integrations-core/pull/6163).
* [Added] Consider log collection for `meta catalog`. See [#6191](https://github.com/DataDog/integrations-core/pull/6191).
* [Added] Add metadata to integrations catalog. See [#6169](https://github.com/DataDog/integrations-core/pull/6169).
* [Added] Add `default` value field for config specs. See [#6178](https://github.com/DataDog/integrations-core/pull/6178).
* [Added] Add utility for temporarily stopping Docker services. See [#5715](https://github.com/DataDog/integrations-core/pull/5715).
* [Added] Add `ddev test` option to verify support of new metrics. See [#6141](https://github.com/DataDog/integrations-core/pull/6141).
* [Fixed] Add `send_distribution_sums_as_monotonic` to openmetrics config spec. See [#6247](https://github.com/DataDog/integrations-core/pull/6247).
* [Fixed] Include moved files to changed files for testing purposes. See [#6174](https://github.com/DataDog/integrations-core/pull/6174).

## 3.2.0 / 2020-03-24

* [Added] Use Trello for QA release script. See [#6125](https://github.com/DataDog/integrations-core/pull/6125).
* [Added] Add script to resolve username from email. See [#6099](https://github.com/DataDog/integrations-core/pull/6099).
* [Added] Add validation to catch legacy imports. See [#6081](https://github.com/DataDog/integrations-core/pull/6081).
* [Added] Upgrade and pin mypy to 0.770. See [#6090](https://github.com/DataDog/integrations-core/pull/6090).
* [Added] Add config spec option for compact YAML representations of nested arrays. See [#6082](https://github.com/DataDog/integrations-core/pull/6082).
* [Added] Order changelog entries by type. See [#5995](https://github.com/DataDog/integrations-core/pull/5995).
* [Added] Upgrade virtualenv to 20.0.8. See [#5980](https://github.com/DataDog/integrations-core/pull/5980).
* [Added] Add config spec templates for JMX integrations. See [#5978](https://github.com/DataDog/integrations-core/pull/5978).
* [Added] Add meta command to fetch JMX info. See [#5652](https://github.com/DataDog/integrations-core/pull/5652).
* [Added] Add `validate metadata` option to check for more duplicates. See [#5803](https://github.com/DataDog/integrations-core/pull/5803).
* [Added] Add markdown output support to catalog tool. See [#5946](https://github.com/DataDog/integrations-core/pull/5946).
* [Added] Bump `datadog-checks-base` version in new integration template. See [#5858](https://github.com/DataDog/integrations-core/pull/5858).
* [Added] Add config spec support for logs-only integrations. See [#5932](https://github.com/DataDog/integrations-core/pull/5932).
* [Fixed] Remove logs sourcecategory. See [#6121](https://github.com/DataDog/integrations-core/pull/6121).
* [Fixed] Remove reference to check in logs-only template. See [#6106](https://github.com/DataDog/integrations-core/pull/6106).
* [Fixed] Fix pathing issues with CI setup script. See [#6100](https://github.com/DataDog/integrations-core/pull/6100).
* [Fixed] Bump classifiers. See [#6083](https://github.com/DataDog/integrations-core/pull/6083).
* [Fixed] Make aggregator stub support multiple jmx instances. See [#5966](https://github.com/DataDog/integrations-core/pull/5966).

## 3.1.0 / 2020-03-02

* [Added] Handle logs only integrations for legacy config validator. See [#5900](https://github.com/DataDog/integrations-core/pull/5900).
* [Fixed] Pin virtualenv to 20.0.5. See [#5891](https://github.com/DataDog/integrations-core/pull/5891).
* [Added] Allow excluding specific checks when performing bulk releases. See [#5878](https://github.com/DataDog/integrations-core/pull/5878).
* [Fixed] Fix E2E parsing of JMX collector output. See [#5849](https://github.com/DataDog/integrations-core/pull/5849).

## 3.0.0 / 2020-02-22

* [Fixed] Fix error when scrubbing non-org secrets. See [#5827](https://github.com/DataDog/integrations-core/pull/5827).
* [Changed] Switch to comparing between arbitrary tags/release branches to `ddev release testable`. See [#5556](https://github.com/DataDog/integrations-core/pull/5556).
* [Added] Add `service` option to default configuration. See [#5805](https://github.com/DataDog/integrations-core/pull/5805).
* [Added] Add ability for config templates to reference other templates. See [#5804](https://github.com/DataDog/integrations-core/pull/5804).
* [Added] Better error messages on config specs errors. See [#5763](https://github.com/DataDog/integrations-core/pull/5763).
* [Added] Add an option to skip environment creation for tests. See [#5760](https://github.com/DataDog/integrations-core/pull/5760).
* [Added] Create an integration catalog command in ddev. See [#5660](https://github.com/DataDog/integrations-core/pull/5660).
* [Added] Add tag_prefix argument to the changelog command. See [#5741](https://github.com/DataDog/integrations-core/pull/5741).
* [Fixed] Switch to Python 3.8 in check integration template. See [#5717](https://github.com/DataDog/integrations-core/pull/5717).
* [Fixed] Switch to Agent 6+ signature in check integration test. See [#5718](https://github.com/DataDog/integrations-core/pull/5718).
* [Added] Add type checking to integration check template. See [#5711](https://github.com/DataDog/integrations-core/pull/5711).
* [Added] Refactor root initialization to common utils. See [#5705](https://github.com/DataDog/integrations-core/pull/5705).
* [Added] Add `agent_requirements.in` to non testable files. See [#5693](https://github.com/DataDog/integrations-core/pull/5693).
* [Added] Add git dep support to dep validation cmd. See [#5692](https://github.com/DataDog/integrations-core/pull/5692).
* [Added] Add support for tab completion to CLI. See [#5674](https://github.com/DataDog/integrations-core/pull/5674).
* [Added] Upgrade virtualenv dependency to 20.x. See [#5680](https://github.com/DataDog/integrations-core/pull/5680).

## 2.4.0 / 2020-02-05

* [Added] Upgrade coverage dependency. See [#5647](https://github.com/DataDog/integrations-core/pull/5647).

## 2.3.0 / 2020-02-05

* [Added] Move CI setup script to ddev. See [#5651](https://github.com/DataDog/integrations-core/pull/5651).
* [Added] Add `internal` to repo choices. See [#5649](https://github.com/DataDog/integrations-core/pull/5649).
* [Added] Move remaining flake8 config to .flake8. See [#5635](https://github.com/DataDog/integrations-core/pull/5635).

## 2.2.0 / 2020-02-04

* [Added] Ignore `__path__` for type hinting of all integrations. See [#5639](https://github.com/DataDog/integrations-core/pull/5639).
* [Added] Modify QA release script to create Jira issues instead of Trello cards. See [#5457](https://github.com/DataDog/integrations-core/pull/5457).
* [Added] Add script to remove all labels from an issue or pull request. See [#5636](https://github.com/DataDog/integrations-core/pull/5636).
* [Added] Always pass PROGRAM* to tox. See [#5631](https://github.com/DataDog/integrations-core/pull/5631).
* [Added] Add meta command to upgrade the Python version of all test environments. See [#5616](https://github.com/DataDog/integrations-core/pull/5616).
* [Added] Use the latest beta release of virtualenv for performance improvements. See [#5617](https://github.com/DataDog/integrations-core/pull/5617).
* [Added] Add type checking support to Tox plugin. See [#5595](https://github.com/DataDog/integrations-core/pull/5595).
* [Added] Update `validate agent-reqs` cmd to list unreleased checks. See [#5610](https://github.com/DataDog/integrations-core/pull/5610).
* [Added] Allow specifying `release changelog` output file. See [#5608](https://github.com/DataDog/integrations-core/pull/5608).
* [Added] Allow --help for `run` command. See [#5602](https://github.com/DataDog/integrations-core/pull/5602).
* [Fixed] Stop mounting the docker socket to allow jmx tests to pass. See [#5601](https://github.com/DataDog/integrations-core/pull/5601).
* [Added] Update in-toto and its deps. See [#5599](https://github.com/DataDog/integrations-core/pull/5599).

## 2.1.0 / 2020-01-30

* [Added] Support CI validation for internal repo. See [#5567](https://github.com/DataDog/integrations-core/pull/5567).
* [Fixed] Fix metric validation. See [#5581](https://github.com/DataDog/integrations-core/pull/5581).
* [Added] Make new integrations use config specs. See [#5580](https://github.com/DataDog/integrations-core/pull/5580).
* [Added] Add --org-name/-o to `env start`. See [#5458](https://github.com/DataDog/integrations-core/pull/5458).
* [Added] Add some helpful output to ddev env ls command. See [#5576](https://github.com/DataDog/integrations-core/pull/5576).
* [Fixed] Avoid long break in error message. See [#5575](https://github.com/DataDog/integrations-core/pull/5575).
* [Added] Add Networks and Processes teams in ddev trello tool. See [#5560](https://github.com/DataDog/integrations-core/pull/5560).

## 2.0.0 / 2020-01-27

* [Added] Add validation for CI infrastructure configuration. See [#5479](https://github.com/DataDog/integrations-core/pull/5479).
* [Fixed] Add support for in-toto >= 0.4.2. See [#5497](https://github.com/DataDog/integrations-core/pull/5497).
* [Added] Upgrade dependencies. See [#5528](https://github.com/DataDog/integrations-core/pull/5528).
* [Added] Add service check name validator and sync. See [#5501](https://github.com/DataDog/integrations-core/pull/5501).
* [Changed] Remove Python 2 support from CLI. See [#5512](https://github.com/DataDog/integrations-core/pull/5512).
* [Added] Run flake8 after formatting fixes. See [#5492](https://github.com/DataDog/integrations-core/pull/5492).
* [Added] Add meta command to convert metadata.csv files to Markdown tables. See [#5461](https://github.com/DataDog/integrations-core/pull/5461).

## 1.4.0 / 2020-01-13

* [Added] Validate metric names normalization in metadata.csv. See [#5437](https://github.com/DataDog/integrations-core/pull/5437).
* [Fixed] Fix function call for `release testable`. See [#5432](https://github.com/DataDog/integrations-core/pull/5432).

## 1.3.0 / 2020-01-09

* [Added] Add debug option to base ddev command. See [#5386](https://github.com/DataDog/integrations-core/pull/5386).
* [Added] Add meta command to translate MIB names to OIDs in SNMP profiles. See [#5397](https://github.com/DataDog/integrations-core/pull/5397).
* [Added] Update license years in integration templates. See [#5384](https://github.com/DataDog/integrations-core/pull/5384).
* [Fixed] Fix a few style lints to handle Python 2. See [#5389](https://github.com/DataDog/integrations-core/pull/5389).

## 1.2.0 / 2019-12-31

* [Changed] Change `wrapper` arg for environment runners to `wrappers`. See [#5361](https://github.com/DataDog/integrations-core/pull/5361).
* [Added] Add mechanism to cross-mount temporary log files between containers. See [#5346](https://github.com/DataDog/integrations-core/pull/5346).

## 1.1.0 / 2019-12-27

* [Added] Refactor terraform configs. See [#5339](https://github.com/DataDog/integrations-core/pull/5339).
* [Added] Make configuration specs an asset. See [#5337](https://github.com/DataDog/integrations-core/pull/5337).
* [Fixed] Always pass USERNAME to tox. See [#5335](https://github.com/DataDog/integrations-core/pull/5335).
* [Added] Add meta command to export dashboards. See [#5332](https://github.com/DataDog/integrations-core/pull/5332).
* [Added] Make changes and changelog command work with other repos. See [#5331](https://github.com/DataDog/integrations-core/pull/5331).
* [Fixed] Fix agent status with ddev. See [#5293](https://github.com/DataDog/integrations-core/pull/5293).
* [Added] Decrease default verbosity of tracebacks in pytest. See [#5291](https://github.com/DataDog/integrations-core/pull/5291).
* [Added] Add more global utilities the pytest plugin. See [#5283](https://github.com/DataDog/integrations-core/pull/5283).
* [Added] Display Docker Compose logs when test environment fails to start. See [#5258](https://github.com/DataDog/integrations-core/pull/5258).
* [Fixed] Remove command to validate Python 3 compatibility. See [#5246](https://github.com/DataDog/integrations-core/pull/5246).
* [Added] Implement configuration specifications. See [#5072](https://github.com/DataDog/integrations-core/pull/5072).
* [Fixed] Pin coverage to 4.5.4. See [#5224](https://github.com/DataDog/integrations-core/pull/5224).
* [Added] Add support for switching between multiple orgs' API/APP keys. See [#5197](https://github.com/DataDog/integrations-core/pull/5197).

## 1.0.1 / 2019-12-06

* [Fixed] Fix a bug where we accidentally recorded git-ignored files in in-toto. See [#5129](https://github.com/DataDog/integrations-core/pull/5129).

## 1.0.0 / 2019-12-02

* [Added] Support downloading universal and pure Python wheels. See [#4981](https://github.com/DataDog/integrations-core/pull/4981).
* [Added] Support more metric types for `ddev meta prom`. See [#5071](https://github.com/DataDog/integrations-core/pull/5071).
* [Added] Improve prompts in `ddev clean`. See [#5061](https://github.com/DataDog/integrations-core/pull/5061).
* [Added] Add command to navigate to config directory. See [#5054](https://github.com/DataDog/integrations-core/pull/5054).
* [Changed] Remove logos folder from template. See [#4988](https://github.com/DataDog/integrations-core/pull/4988).
* [Fixed] Handle formatting edge cases for `meta changes`. See [#4970](https://github.com/DataDog/integrations-core/pull/4970).
* [Changed] Remove logo validation. See [#4964](https://github.com/DataDog/integrations-core/pull/4964).
* [Added] Use a stub class for metadata testing. See [#4919](https://github.com/DataDog/integrations-core/pull/4919).
* [Fixed] Never sign an empty release. See [#4933](https://github.com/DataDog/integrations-core/pull/4933).
* [Fixed] Update requirements when updating check. See [#4895](https://github.com/DataDog/integrations-core/pull/4895).
* [Added] Add saved_views metadata field to integration templates. See [#4584](https://github.com/DataDog/integrations-core/pull/4584).

## 0.39.0 / 2019-10-25

* [Added] Add junit option to `ddev env e2e` command. See [#4879](https://github.com/DataDog/integrations-core/pull/4879).
* [Fixed] Change the team label map for Trello card creation. See [#4852](https://github.com/DataDog/integrations-core/pull/4852).
* [Fixed] Update metadata link in template. See [#4869](https://github.com/DataDog/integrations-core/pull/4869).

## 0.38.3 / 2019-10-17

* [Fixed] Fix CHANGELOG.md template to make it work with `ddev release changelog`. See [#4808](https://github.com/DataDog/integrations-core/pull/4808).

## 0.38.2 / 2019-10-17

* [Fixed] Handle the case of pylint returning empty output. See [#4801](https://github.com/DataDog/integrations-core/pull/4801).

## 0.38.1 / 2019-10-15

* [Fixed] Fix ddev testable command to properly use the tag, fallback on the branch if absent. See [#4775](https://github.com/DataDog/integrations-core/pull/4775).

## 0.38.0 / 2019-10-11

* [Added] Add option for device testing in e2e. See [#4693](https://github.com/DataDog/integrations-core/pull/4693).
* [Fixed] Fix lint flake8-logging-format command. See [#4728](https://github.com/DataDog/integrations-core/pull/4728).
* [Added] Add flake8-logging-format. See [#4711](https://github.com/DataDog/integrations-core/pull/4711).

## 0.37.0 / 2019-10-09

* [Added] Increase default Agent flush timeout. See [#4714](https://github.com/DataDog/integrations-core/pull/4714).
* [Fixed] Remove default version from env test. See [#4718](https://github.com/DataDog/integrations-core/pull/4718).
* [Fixed] Handle other Agent images in E2E. See [#4710](https://github.com/DataDog/integrations-core/pull/4710).

## 0.36.0 / 2019-10-07

* [Added] Update teams in ddev trello tool. See [#4702](https://github.com/DataDog/integrations-core/pull/4702).
* [Added] Add dashboard validation. See [#4694](https://github.com/DataDog/integrations-core/pull/4694).
* [Fixed] Don't use a7. See [#4680](https://github.com/DataDog/integrations-core/pull/4680).

## 0.35.1 / 2019-09-30

* [Fixed] Auto detect changes and run tests when yaml files change. See [#4657](https://github.com/DataDog/integrations-core/pull/4657).

## 0.35.0 / 2019-09-30

* [Added] Support submitting memory profiling metrics during E2E. See [#4635](https://github.com/DataDog/integrations-core/pull/4635).

## 0.34.0 / 2019-09-24

* [Added] Improve RetryError message. See [#4619](https://github.com/DataDog/integrations-core/pull/4619).
* [Added] Reload environments if there are extra startup commands. See [#4614](https://github.com/DataDog/integrations-core/pull/4614).
* [Added] Add warning to create command if name is lowercase. See [#4564](https://github.com/DataDog/integrations-core/pull/4564).

## 0.33.0 / 2019-09-19

* [Fixed] Stop identifying core vs extras from the working directory name. See [#4583](https://github.com/DataDog/integrations-core/pull/4583).
* [Added] Update tooling for Azure Pipelines. See [#4536](https://github.com/DataDog/integrations-core/pull/4536).

## 0.32.0 / 2019-08-24

* [Added] Don't fail e2e on unsupported platforms. See [#4398](https://github.com/DataDog/integrations-core/pull/4398).
* [Added] Add K8S e2e util. See [#4203](https://github.com/DataDog/integrations-core/pull/4203).
* [Added] Add SSH port forward e2e util. See [#4147](https://github.com/DataDog/integrations-core/pull/4147).
* [Added] Deployment environment with Terraform. See [#4039](https://github.com/DataDog/integrations-core/pull/4039).
* [Fixed] Use the new Python 2 / 3 Docker images. See [#4246](https://github.com/DataDog/integrations-core/pull/4246).
* [Fixed] Don't put integer in environment. See [#4234](https://github.com/DataDog/integrations-core/pull/4234).
* [Added] Support Python 3 when calling pip for extra E2E start up commands. See [#4213](https://github.com/DataDog/integrations-core/pull/4213).
* [Added] Make `docker_run` clean up volumes and orphaned containers. See [#4212](https://github.com/DataDog/integrations-core/pull/4212).
* [Fixed] Use utcnow instead of now. See [#4192](https://github.com/DataDog/integrations-core/pull/4192).
* [Added] Allow multiple docker Agents to coexist for E2E by randomly assigning ports. See [#4205](https://github.com/DataDog/integrations-core/pull/4205).
* [Added] Add docker_volumes option to E2E metadata. See [#4178](https://github.com/DataDog/integrations-core/pull/4178).
* [Added] Add env check for jmx integrations. See [#4146](https://github.com/DataDog/integrations-core/pull/4146).

## 0.31.1 / 2019-07-19

* [Fixed] Fix get_current_agent_version sorting in ddev. See [#4113](https://github.com/DataDog/integrations-core/pull/4113).

## 0.31.0 / 2019-07-13

* [Added] Add support for selecting an Agent build via environment. See [#4112](https://github.com/DataDog/integrations-core/pull/4112).
* [Added] Add ways to control the colorization of output. See [#4086](https://github.com/DataDog/integrations-core/pull/4086).
* [Added] Support multiple Python versions for E2E. See [#4075](https://github.com/DataDog/integrations-core/pull/4075).

## 0.30.1 / 2019-07-04

* [Fixed] Fix metadata bootstrap workflow. See [#4047](https://github.com/DataDog/integrations-core/pull/4047).

## 0.30.0 / 2019-07-04

* [Fixed] Update wording on installing extras in ddev create command. See [#4032](https://github.com/DataDog/integrations-core/pull/4032).
* [Added] Remove timeout when stopping containers. See [#3973](https://github.com/DataDog/integrations-core/pull/3973).

## 0.29.0 / 2019-06-24

* [Added] Only sign updated checks. See [#3944](https://github.com/DataDog/integrations-core/pull/3944).

## 0.28.0 / 2019-06-19

* [Added] Print line number on validate metadata. See [#3931](https://github.com/DataDog/integrations-core/pull/3931).

## 0.27.0 / 2019-06-18

* [Fixed] Validate interval in metadata validation. See [#3857](https://github.com/DataDog/integrations-core/pull/3857).
* [Added] Support E2E testing. See [#3896](https://github.com/DataDog/integrations-core/pull/3896).
* [Added] Allow releasing multiple checks at once. See [#3881](https://github.com/DataDog/integrations-core/pull/3881).

## 0.26.1 / 2019-06-05

* [Fixed] Fix JMX template. See [#3879](https://github.com/DataDog/integrations-core/pull/3879).
* [Fixed] Update APM team label. See [#3878](https://github.com/DataDog/integrations-core/pull/3878).
* [Fixed] Fix logic to skip docs PRs for release testing. See [#3877](https://github.com/DataDog/integrations-core/pull/3877).

## 0.26.0 / 2019-06-01

* [Added] Better error message when releasing on the wrong branch. See [#3832](https://github.com/DataDog/integrations-core/pull/3832).

## 0.25.2 / 2019-05-28

* [Fixed] Fix tox plugin. See [#3825](https://github.com/DataDog/integrations-core/pull/3825).

## 0.25.1 / 2019-05-24

* [Fixed] Use safe default when validating manifests. See [#3810](https://github.com/DataDog/integrations-core/pull/3810).

## 0.25.0 / 2019-05-20

* [Added] Move all assets to a dedicated directory. See [#3768](https://github.com/DataDog/integrations-core/pull/3768).
* [Added] Upgrade requests to 2.22.0. See [#3778](https://github.com/DataDog/integrations-core/pull/3778).

## 0.24.0 / 2019-05-14

* [Added] Ambari integration. See [#3670](https://github.com/DataDog/integrations-core/pull/3670).
* [Added] Fail if service check file doesn't exist. See [#3691](https://github.com/DataDog/integrations-core/pull/3691).
* [Added] Add default service check file to new checks templates. See [#3726](https://github.com/DataDog/integrations-core/pull/3726).
* [Added] Adds ddev YAML config validator. See [#3679](https://github.com/DataDog/integrations-core/pull/3679).
* [Added] Upgrade pyyaml to 5.1. See [#3698](https://github.com/DataDog/integrations-core/pull/3698).

## 0.23.2 / 2019-04-30

* [Fixed] Remove spurious debug line. See [#3703](https://github.com/DataDog/integrations-core/pull/3703).

## 0.23.1 / 2019-04-30

* [Fixed] Fix creation of jmx & tile integrations. See [#3701](https://github.com/DataDog/integrations-core/pull/3701).
* [Fixed] Fix template for new integration to use argument as display name. See [#3664](https://github.com/DataDog/integrations-core/pull/3664).

## 0.23.0 / 2019-04-22

* [Added] Add extra type for manifest validation. See [#3662](https://github.com/DataDog/integrations-core/pull/3662).
* [Added] Adhere to code style. See [#3497](https://github.com/DataDog/integrations-core/pull/3497).
* [Removed] Remove `pre` from versioning scheme. See [#3655](https://github.com/DataDog/integrations-core/pull/3655).
* [Fixed] Fix changelog generation for new checks. See [#3634](https://github.com/DataDog/integrations-core/pull/3634).

## 0.22.0 / 2019-04-15

* [Added] Build releases automatically. See [#3364](https://github.com/DataDog/integrations-core/pull/3364).
* [Fixed] Fixed language in template for integration extras readme. See [#3606](https://github.com/DataDog/integrations-core/pull/3606).
* [Added] Add validation on integration_id. See [#3598](https://github.com/DataDog/integrations-core/pull/3598).
* [Added] Add ability to specify extra start-up commands for e2e. See [#3594](https://github.com/DataDog/integrations-core/pull/3594).
* [Added] Add a pytest-args option to ddev test. See [#3596](https://github.com/DataDog/integrations-core/pull/3596).
* [Fixed] Ensure style envs support every platform. See [#3482](https://github.com/DataDog/integrations-core/pull/3482).
* [Added] Add posargs in tox.ini. See [#3313](https://github.com/DataDog/integrations-core/pull/3313).
* [Fixed] Fix breakpoint agent check flag. See [#3447](https://github.com/DataDog/integrations-core/pull/3447).
* [Added] Update version of datadog-checks-base for extras. See [#3433](https://github.com/DataDog/integrations-core/pull/3433).

## 0.21.0 / 2019-03-29

* [Added] Upgrade in-toto. See [#3411](https://github.com/DataDog/integrations-core/pull/3411).

## 0.20.0 / 2019-03-28

* [Added] Remove flake8 from tox.ini template. See [#3358](https://github.com/DataDog/integrations-core/pull/3358).
* [Added] Support all options for the Agent check command. See [#3350](https://github.com/DataDog/integrations-core/pull/3350).
* [Added] Add ability to detect if using JMX based on metadata. See [#3330](https://github.com/DataDog/integrations-core/pull/3330).
* [Fixed] Make the aggregator fixture lazily import the stub. See [#3308](https://github.com/DataDog/integrations-core/pull/3308).
* [Added] Add style checker and formatter. See [#3299](https://github.com/DataDog/integrations-core/pull/3299).
* [Added] Add env var support to E2E containers. See [#3263](https://github.com/DataDog/integrations-core/pull/3263).
* [Added] Enforce new integration_id field. See [#3264](https://github.com/DataDog/integrations-core/pull/3264).
* [Added] Add row length validation. See [#3266](https://github.com/DataDog/integrations-core/pull/3266).
* [Added] Add logo validation. See [#3246](https://github.com/DataDog/integrations-core/pull/3246).
* [Fixed] Fix sdist build command. See [#3252](https://github.com/DataDog/integrations-core/pull/3252).
* [Added] Default to Python 3.7 for new checks. See [#3244](https://github.com/DataDog/integrations-core/pull/3244).

## 0.19.1 / 2019-03-01

* [Fixed] Run upload command in the proper location. See [#3239](https://github.com/DataDog/integrations-core/pull/3239).

## 0.19.0 / 2019-03-01

* [Fixed] Fix agent changelog command. See [#3233](https://github.com/DataDog/integrations-core/pull/3233).
* [Added] Add integration_id to manifest validation. See [#3232](https://github.com/DataDog/integrations-core/pull/3232).
* [Added] Add ability to pass -m & -k to pytest. See [#3163](https://github.com/DataDog/integrations-core/pull/3163).
* [Fixed] Properly detect integration folder for py3 validation. See [#3188](https://github.com/DataDog/integrations-core/pull/3188).
* [Added] Provide a way to update to the new agent build config format. See [#3181](https://github.com/DataDog/integrations-core/pull/3181).
* [Fixed] Properly ship datadog-checks-downloader. See [#3169](https://github.com/DataDog/integrations-core/pull/3169).
* [Added] Support datadog_checks_downloader. See [#3164](https://github.com/DataDog/integrations-core/pull/3164).
* [Added] Add util to load jmx metric configs. See [#3162](https://github.com/DataDog/integrations-core/pull/3162).

## 0.18.0 / 2019-02-18

* [Added] Add util to get the directory of current file. See [#3135](https://github.com/DataDog/integrations-core/pull/3135).
* [Fixed] Update e2e start help text for extras integrations. See [#3133](https://github.com/DataDog/integrations-core/pull/3133).
* [Fixed] Fix e2e package install order. See [#3092](https://github.com/DataDog/integrations-core/pull/3092).
* [Added] Add command to build package wheel. See [#3067](https://github.com/DataDog/integrations-core/pull/3067).
* [Added] Add datadog-checks-downloader. See [#3026](https://github.com/DataDog/integrations-core/pull/3026).
* [Added] Add `local` E2E . See [#3064](https://github.com/DataDog/integrations-core/pull/3064).
* [Added] Add command to show changes based on commit date. See [#3063](https://github.com/DataDog/integrations-core/pull/3063).
* [Added] Add e2e command to restart the agent. See [#3054](https://github.com/DataDog/integrations-core/pull/3054).
* [Added] Upgrade pytest-benchmark. See [#2934](https://github.com/DataDog/integrations-core/pull/2934).
* [Added] Add description length metadata validation. See [#2923](https://github.com/DataDog/integrations-core/pull/2923).
* [Added] Allow uploading of any Datadog python package. See [#2907](https://github.com/DataDog/integrations-core/pull/2907).
* [Added] Upgrade pytest plugins. See [#2884](https://github.com/DataDog/integrations-core/pull/2884).

## 0.17.0 / 2019-01-07

* [Added] Use standalone py3 validation. See [#2854][1].
* [Fixed] Fix root folder name when running 'validate' commands on integrations-extras. See [#2879][2].
* [Fixed] Pin pytest because of a regression in pytest-benchmark. See [#2878][3].

## 0.16.0 / 2018-12-22

* [Added] Remove requirements.txt from check template. See [#2816][4].
* [Added] Add ability to log warnings during pytest. See [#2764][5].
* [Fixed] Fix agent_changelog command. See [#2808][6].
* [Added] Update templates for new integrations. See [#2794][7].
* [Added] Add python3 compatibility validation. See [#2736][8].
* [Added] Validate checks dependencies against the embedded environment. See [#2746][9].
* [Added] Add constant to check if platform is Linux. See [#2782][10].
* [Fixed] Do not consider empty string as a version change. See [#2771][11].
* [Changed] Rename `ddev release freeze` to `ddev release agent_req_file`, refactor commands code. See [#2765][12].
* [Added] Add validation for configuration files. See [#2759][13].
* [Added] Add ability to pass state to e2e tear down. See [#2724][14].
* [Added] Add ability to use dev version of base package for e2e. See [#2689][15].

## 0.15.1 / 2018-11-30

* [Fixed] Handle unreleased checks for agent reqs validation. See [#2664][16].

## 0.15.0 / 2018-11-27

* [Added] Added Watt units to metadata validation. See [#2645][17].
* [Added] Added Heap and Volume units to metadata validation. See [#2647][18].
* [Fixed] Gently handle Yubikey exceptions. See [#2641][19].
* [Added] Added validation step for the agent-requirements file. See [#2642][20].

## 0.14.1 / 2018-11-22

* [Fixed] Increase gpg timeout to give time to developers to interact with Yubikeys. See [#2613][21].
* [Fixed] Fix requirements-agent-release.txt updating. See [#2617][22].

## 0.14.0 / 2018-11-16

* [Added] Support agent repo. See [#2600][23].
* [Added] Improve trello releasing. See [#2599][24].
* [Added] Refactor validations under `validate` command. See [#2593][25].
* [Added] Upgrade docker-compose and requests. See [#2503][26].
* [Added] Disable pytest output capturing when debugging. See [#2502][27].
* [Added] Support specifying type of semver version bumps. See [#2491][28].
* [Fixed] Fixed off-by-one missing latest release. See [#2478][29].
* [Added] Fix codecov error on appveyor. See [#2474][30].
* [Fixed] Use raw string literals when \ is present. See [#2465][31].
* [Fixed] Improve output of `ddev manifest verify` command. See [#2444][32].
* [Added] Add service_checks.json files validation. See [#2432][33].
* [Added] Make all tox envs available to E2E. See [#2457][34].
* [Added] Ensure new checks include the E2E fixture. See [#2455][35].
* [Fixed] Handle any clipboard errors for E2E. See [#2454][36].
* [Added] Prevent misconfigured tox files. See [#2447][37].
* [Fixed] Add `datadog-` prefix to packages name. See [#2430][38].

## 0.13.0 / 2018-10-17

* [Added] Ensure new checks use editable install of datadog_checks_base for tests. See [#2427][39].
* [Fixed] Relax e2e config parsing. See [#2416][40].
* [Fixed] Fix sleep on WaitFor helper. See [#2418][41].

## 0.12.1 / 2018-10-15

* [Fixed] Improve handling of github api errors for trello. See [#2411][42].
* [Fixed] Make every check's `tests` directory path unique for coverage. See [#2406][43].

## 0.12.0 / 2018-10-15

* [Fixed] Fix trello for issue number in commit message. See [#2408][44].
* [Added] Support the initial release of integrations. See [#2399][45].

## 0.11.0 / 2018-10-11

* [Added] Add E2E support. See [#2375][46].
* [Added] Ensure new core checks use latest dev package for testing. See [#2386][47].
* [Fixed] Normalize line endings for release signing. See [#2364][48].
* [Added] Support more teams for Trello test cards. See [#2365][49].

## 0.10.0 / 2018-10-04

* [Added] Update base package paths. See [#2345][50].
* [Added] Add generic environment runner. See [#2342][51].
* [Added] Add WaitFor environment condition. See [#2343][52].
* [Added] Enable pytest plugin to control environments. See [#2336][53].

## 0.9.0 / 2018-09-30

* [Added] Allow testing of specific environments. See [#2312][54].
* [Added] Add run command. See [#2319][55].
* [Fixed] Fix namespace overwriting. See [#2311][56].
* [Fixed] Upgrade in-toto to gain full cross-platform release signing support. See [#2315][57].
* [Added] Command to validate metadata. See [#2269][58].

## 0.8.1 / 2018-09-25

* [Fixed] Fix Python 2 unicode handling for log pattern error message. See [#2303][59].

## 0.8.0 / 2018-09-25

* [Added] Add new templates for other integration types. See [#2285][60].
* [Added] Add release signing via in-toto. See [#2224][61].
* [Added] Add prometheus metadata.csv and metric map auto-generation. See [#2117][62].
* [Added] Keep track of the checks changed at every Datadog Agent release. See [#2277][63].

## 0.7.0 / 2018-09-18

* [Added] Fix manifest validation policy. See [#2258][64].
* [Added] Add config option to select the default repository. See [#2243][65].

## 0.6.2 / 2018-09-14

* [Fixed] Revert "Update base package paths (#2235)". See [#2240][66].

## 0.6.1 / 2018-09-14

* [Fixed] Move datadog_checks_base code into sub base package. See [#2167][67].

## 0.6.0 / 2018-09-14

* [Added] Update base package paths. See [#2235][68].
* [Added] Add ability to add wait time in docker_run. See [#2196][69].
* [Added] Add better debugging to test command. See [#2194][70].
* [Fixed] Gracefully handle tags that already exist. See [#2172][71].
* [Fixed] Fix release freeze command. See [#2188][72].
* [Added] Add ability to filter checks to test by changes. See [#2163][73].

## 0.5.0 / 2018-09-04

* [Added] Allow automated releasing by looking at github labels. See [#2169][74].
* [Fixed] Handle character limit for Trello card descriptions. See [#2162][75].

## 0.4.1 / 2018-08-31

* [Fixed] Fix trello command for other repos. See [#2155][76].

## 0.4.0 / 2018-08-28

* [Added] Add code coverage. See [#2105][77].
* [Added] Add command to create new integrations. See [#2037][78].

## 0.3.1 / 2018-08-03

* [Fixed] Fix clean command. See [#1992][79].

## 0.3.0 / 2018-07-30

* [Added] Allow passing --build to compose up. See [#1962][80].
* [Fixed] When setting repo paths do not resolve home. See [#1953][81].
* [Added] Add command to create Trello test cards from Agent release diffs. See [#1934][82].
* [Added] Add openldap to the list of agent integrations. See [#1923][83].
* [Added] Update dep tooling to support environment markers. See [#1921][84].

## 0.2.2 / 2018-07-19

* [Fixed] Relax condition error handling to allow more time. See [#1914][85].
* [Fixed] Do not skip release builds. See [#1913][86].
* [Fixed] Fix packaging of agent requirements. See [#1911][87].

## 0.2.1 / 2018-07-17

* [Fixed] make remove_path util more resilient to errors. See [#1900][88].

## 0.2.0 / 2018-07-17

* [Added] improve docker tooling. See [#1891][89].

## 0.1.1 / 2018-07-12

* [Fixed] fix changed-only test logic. See [#1878][90].

## 0.1.0 / 2018-07-12

* [Added] Add developer package. See [#1862][91].
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
