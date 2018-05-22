# Datadog Agent Integrations - Core

[![Build Status][1]][2]
[![Build status][3]][4]

This repository contains the Agent Integrations (also known as checks) that Datadog
officially develops and supports. To add a new integration, please see the [Integrations Extras][5]
repository and the [accompanying documentation][6].

The [Datadog Agent][7] packages are equipped
with all the checks from this repository, so to get started using them, you can
simply [install the Agent][8] for your operating
system.

General documentation about the project can be [found here](docs/index.md)

## Integrations as Python wheels

When working with an integration, you will now be dealing with a more structured
python project. The new structure should help keep a more sane and modular codebase.
To help with the transition, please take a look at the following map to understand
where everything falls into place in the new approach.

| FORMER LOCATION | NEW LOCATION |
| --------------- | ------------ |
| {integration}/check.py | {integration}/datadog_checks/{integration}/{integration}.py |
| {integration}/conf.yaml.example | {integration}/datadog_checks/{integration}/conf.yaml.example |
| n/a | {integration}/datadog_checks/{integration}/\_\_init\_\_.py |
| {integration}/test_check.py | {integration}/test/test_{integration}.py |
| n/a | {integration}/test/\_\_init\_\_.py |
| n/a | {integration}/setup.py |

## A note about installing

Now that integrations are cleanly defined as python packages, we will soon be able
to ship them as Python wheels that will be pip-installable in the Python environment
embedded into the Datadog Agent. This presents a paradigm change in the way we will
be delivering standalone integration upgrades, moving away from OS-specific packages
to idiomatic Python package delivery.

Agent releases starting from version 5.21 bundle the latest wheels for any
integration, but at the moment you can't upgrade or downgrade between releases.

## Quick Start

Working with integrations is easy, the main page of the [development docs](docs/dev/README.md)
contains all the info you need to get your dev enviroment up and running in minutes
to run, test and build a Check.

**Important:** the instructions are only valid for a subset of the Checks in this
repository. Making all the checks work with the new build and test strategy is
a work in progress. You can find the list of the checks already updated [here][14]

## Reporting Issues

For more information on integrations, please reference our [documentation][11]
and [knowledge base][12]. You can also visit our
[help page][13] to connect with us.

[1]: https://travis-ci.org/DataDog/integrations-core.svg?branch=master
[2]: https://travis-ci.org/DataDog/integrations-core
[3]: https://ci.appveyor.com/api/projects/status/8w4s2bilp48n43gw?svg=true
[4]: https://ci.appveyor.com/project/Datadog/integrations-core
[5]: https://github.com/DataDog/integrations-extras
[6]: https://docs.datadoghq.com/developers/integrations/integration_sdk/
[7]: https://github.com/DataDog/datadog-agent
[8]: https://docs.datadoghq.com/agent/
[9]: https://docs.pytest.org/en/latest/
[10]: https://packaging.python.org/tutorials/distributing-packages/
[11]: http://docs.datadoghq.com
[12]: https://help.datadoghq.com/hc/en-us
[13]: http://docs.datadoghq.com/help/
[14]: https://github.com/DataDog/integrations-core/blob/master/tasks/constants.py#L15
