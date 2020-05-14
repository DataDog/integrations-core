# Datadog Agent Integrations - Core

[![Build status][1]][2]
[![Coverage status][17]][18]
[![Documentation Status][19]][20]
[![Code style - black][21]][22]

This repository contains the Agent Integrations that Datadog officially develops and supports.
To add a new integration, please see the [Integrations Extras][5] repository and the
[accompanying documentation][6].

The [Datadog Agent][7] packages are equipped with all the Integrations from this
repository, so to get started using them, you can simply [install the Agent][8]
for your operating system. The [AGENT_CHANGELOG](AGENT_CHANGELOG.md) file shows
which Integrations have been updated in each Agent version.

## Contributing

Working with integrations is easy, the main page of the [development docs][6]
contains all the info you need to get your dev environment up and running in minutes
to run, test and build a Check. More advanced documentation can be found [here][20].

## Reporting Issues

For more information on integrations, please reference our [documentation][11] and
[knowledge base][12]. You can also visit our [help page][13] to connect with us.

## GPG public keys

An up-to-date list of all developers authorized to sign releases can be found [here][23].

[1]: https://dev.azure.com/datadoghq/integrations-core/_apis/build/status/Master%20All?branchName=master
[2]: https://dev.azure.com/datadoghq/integrations-core/_build/latest?definitionId=29&branchName=master
[5]: https://github.com/DataDog/integrations-extras
[6]: https://docs.datadoghq.com/developers/integrations/
[7]: https://github.com/DataDog/datadog-agent
[8]: https://docs.datadoghq.com/agent/
[9]: https://docs.pytest.org/en/latest/
[10]: https://packaging.python.org/tutorials/distributing-packages/
[11]: https://docs.datadoghq.com
[12]: https://help.datadoghq.com/hc/en-us
[13]: https://docs.datadoghq.com/help/
[15]: https://github.com/DataDog/integrations-core/blob/6.2.1/requirements-integration-core.txt
[16]: https://github.com/DataDog/integrations-core/blob/ea2dfbf1e8859333af4c8db50553eb72a3b466f9/requirements-agent-release.txt
[17]: https://codecov.io/github/DataDog/integrations-core/coverage.svg?branch=master
[18]: https://codecov.io/github/DataDog/integrations-core?branch=master
[19]: https://readthedocs.org/projects/datadog-checks-base/badge/?version=latest
[20]: https://datadoghq.dev/integrations-core/
[21]: https://img.shields.io/badge/code%20style-black-000000.svg
[22]: https://github.com/ambv/black
[23]: https://datadoghq.dev/integrations-core/process/integration-release/#releasers
