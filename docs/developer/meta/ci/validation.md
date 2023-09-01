# Validation

-----

Various validations are [ran](https://github.com/DataDog/integrations-core/blob/master/.github/workflows/validate.yml) to check for correctness. There is a [reusable workflow](https://github.com/DataDog/integrations-core/blob/master/.github/workflows/run-validations.yml) that repositories may call with input parameters defining which validations to use, with each input parameter corresponding to a subcommand under the `ddev validate` command group.

## Agent requirements

```
ddev validate agent-reqs
```

This validates that each integration version is in sync with the [`requirements-agent-release.txt`](https://github.com/DataDog/integrations-core/blob/master/requirements-agent-release.txt) file. It is uncommon for this to fail because the release process is automated.

## CI configuration

```
ddev validate ci
```

This validates that all CI entries for integrations are valid. This includes checking if the integration has the correct [Codecov config](https://github.com/DataDog/integrations-core/blob/master/.codecov.yml), and has a valid [CI entry](testing.md#target-enumeration) if it is testable.

!!! tip
    Run `ddev validate ci --sync` to resolve most errors.

## Codeowners

```
ddev validate codeowners
```

This validates that every integration has a [codeowner entry](https://docs.github.com/en/github/creating-cloning-and-archiving-repositories/about-code-owners). If this validation fails, add an entry in the [codewners file](https://github.com/DataDog/integrations-extras/blob/master/.github/CODEOWNERS) corresponding to any newly added integration.

!!! note
    This validation is only enabled for [integrations-extras](https://github.com/DataDog/integrations-extras).

## Default configuration files

```
ddev validate config
```

This verifies that the config specs for all integrations are valid by enforcing our configuration spec [schema](../config-specs.md#schema). The most common failure is some version of `File <INTEGRATION_SPEC> needs to be synced.` To resolve this issue, you can run `ddev validate config --sync`

If you see failures regarding formatting or missing parameters, see our [config spec](../config-specs.md#schema) documentation for more details on how to construct configuration specs.

## Dashboard definition files

```
ddev validate dashboards
```

This validates that dashboards are formatted correctly. This means that they need to be proper JSON and generated from Datadog's `/dashboard` [API](https://docs.datadoghq.com/api/v1/dashboards/).

!!! tip
    If you see a failure regarding use of the screen endpoint, consider using our dashboard [utility command](../../ddev/cli.md#ddev-meta-dash-export) to generate your dashboard payload.

## Dependencies

```
ddev validate dep
```

This command:

- Verifies the uniqueness of dependency versions across all checks.
- Verifies all the dependencies are pinned.
- Verifies the embedded Python environment defined in the base check and requirements listed in every integration are compatible.

This validation only applies if your work introduces new external dependencies.

## Manifest files

```
ddev validate manifest
```

This validates that the manifest files contain required fields, are formatted correctly, and don't contain common errors. See the [Datadog docs](https://docs.datadoghq.com/developers/integrations/check_references/#manifest-file) for more detailed constraints.

## Metadata

```
ddev validate metadata
```

This checks that every `metadata.csv` file is formatted correctly. See the [Datadog docs](https://docs.datadoghq.com/developers/integrations/check_references/#metrics-metadata-file) for more detailed constraints.

## README files

```
ddev validate readmes
```

This ensures that every integration's README.md file is formatted correctly. The main purpose of this validation is to ensure that any image linked in the readme exists and that all images are located in an integration's `/image` directory.

## Saved views data

```
ddev validate saved-views
```

This validates that saved views for an integration are formatted correctly and contain required fields, such as "type".

!!! tip
    View [example saved views](https://github.com/DataDog/integrations-core/tree/master/postgres/assets/saved_views) for inspiration and guidance.

## Service check data

```
ddev validate service-checks
```

This checks that every service check file is formatted correctly. See the [Datadog docs](https://docs.datadoghq.com/developers/integrations/check_references/#service-check-file) for more specific constraints.

## Imports

```
ddev validate imports
```

This verifies that all integrations import the base package in the correct way, such as:

```python
from datadog_checks.base.foo import bar
```

!!! tip
    See the [New Integration Instructions](https://docs.datadoghq.com/developers/integrations/new_check_howto/?tab=configurationtemplate#implement-check-logic) for more examples of how to use the base package.
