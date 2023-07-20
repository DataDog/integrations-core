---
title: Create an Agent Integration
kind: documentation
aliases:
  - /developers/integrations/integration_sdk/
  - /developers/integrations/testing/
  - /integrations/datadog_checks_dev/
  - /guides/new_integration/
  - /developers/integrations/new_check_howto/
further_reading:
- link: "/developers/integrations/create_a_tile/"
  tag: "Documentation"
  text: "Create a tile"
- link: "/developers/integrations/python/"
  tag: "Documentation"
  text: "Python for Agent-based Integration Development"
- link: "/developers/"
  tag: "Documentation"
  text: "Learn how to develop on the Datadog platform"
---

## Overview

This page walks Technology Partners through how to create a Datadog Agent integration, which you can list as out-of-the-box on the [Integrations page][23], or for a price on the [Marketplace page][24]. 

## Agent-based integrations

Agent-based integrations use the [Datadog Agent][17] to submit data through checks written by the developer. Checks can emit [metrics][23], [events][24], and [service checks][25] into a customer's Datadog account. The Agent itself can submit [logs][26] as well, but that is configured outside of the check. 

The implementation code for these integrations is hosted by Datadog. Agent integrations are best suited for collecting data from systems or applications that live in a local area network (LAN) or virtual private cloud (VPC). Creating an Agent integration requires you to publish and deploy your solution as a Python wheel (`.whl`).

You can include out-of-the-box assets such as [monitors][27], [dashboards][28], and [log pipelines][29] with your Agent-based integration. When a user clicks **Install** on your integration tile, they are prompted to follow the setup instructions, and all out-of-the-box dashboards will appear in their account. Other assets, such as log pipelines, will appear for users after proper installation and configuration of the integration.

## Development process

The process to build an Agent-based integration looks like this: 

1. Once you've been accepted to the [Datadog Partner Network][32], you will meet with the Datadog Technology Partner team to discuss your offering and use cases.
2. Request a Datadog sandbox account for development through the Datadog Partner Network portal.
3. Begin development of your integration, which includes writing the integration code on your end as well as building and installing a Python wheel (`.whl`).
4. Test your integration in your Datadog sandbox account.
5. Once your development work is tested and complete, populate your tile assets by providing information like setup instructions, images, support information, and more that will make up your integration tile that's displayed on the **Integrations** or **Marketplace** page.
6. Once your pull request is submitted and approved, the Datadog Technology Partner team will schedule a demo for a final review of your integration.
7. You will have the option of testing the tile and integration in your Datadog sandbox account before publishing, or immediately publishing the integration for all customers.  

## Prerequisites

The required Datadog Agent integration development tools include the following:

- Python v3.9, [pipx][2], and the Agent Integration Developer Tool (`ddev`). For installation instructions, see [Install the Datadog Agent Integration Developer Tool][3].
- [Docker][4] to run the full test suite.
- The git [command line][5] or [GitHub Desktop client][19].

<div class="alert alert-info">Select a tab for instructions on building an out-of-the-box Agent-based integration on the Integrations page, or an Agent-based integration on the Marketplace page.</div>

{{< tabs >}}
{{% tab "Build an out-of-the-box integration" %}}

To build an out-of-the-box integration:

Create a `dd` directory:
   
```shell
mkdir $HOME/dd && cd $HOME/dd
```

   The Datadog Development Toolkit expects you to work in the `$HOME/dd/` directory. This is not mandatory, but working in a different directory requires additional configuration steps. 

1. Fork the [`integrations-extras` repository][101].

1. Clone your fork into the `dd` directory:
   ```shell
   git clone git@github.com:<YOUR USERNAME>/integrations-extras.git
   ```

1. Create a feature branch to work in:
   ```shell
   git switch -c <YOUR INTEGRATION NAME> origin/master
   ```

## Configure the developer tool

The Agent Integration Developer Tool allows you to create scaffolding when you are developing an integration by generating a skeleton of your integration tile's assets and metadata. For instructions on installing the tool, see [Install the Datadog Agent Integration Developer Tool][102].

To configure the tool for the `integrations-extras` repository:

1. Optionally, if your `integrations-extras` repo is somewhere other than `$HOME/dd/`, adjust the `ddev` configuration file:
   ```shell
   ddev config set extras "/path/to/integrations-extras"
   ```

1. Set `integrations-extras` as the default working repository:
   ```shell
   ddev config set repo extras
   ```

[101]: https://github.com/Datadog/integrations-extras
[102]: https://docs.datadoghq.com/developers/integrations/python

{{% /tab %}}

{{% tab "Build a Marketplace integration" %}}

To build an integration:

1. See [Build a Marketplace Offering][102] to request access to the [Marketplace repository][101].
1. Create a `dd` directory:

   ```shell
   mkdir $HOME/dd```

   The Datadog Development Toolkit command expects you to be working in the `$HOME/dd/` directory. This is not mandatory, but working in a different directory requires additional configuration steps.

1. Once you have been granted access to the Marketplace repository, create the `dd` directory and clone the `marketplace` repository:

   ```shell
   git clone git@github.com:DataDog/marketplace.git```

1. Create a feature branch to work in:

   ```shell
   git switch -c <YOUR INTEGRATION NAME> origin/master```

## Install and configure the Datadog development toolkit

The Agent Integration Developer Tool allows you to create scaffolding when you are developing an integration by generating a skeleton of your integration tile's assets and metadata. For instructions on installing the tool, see [Install the Datadog Agent Integration Developer Tool][103].

Once you have installed the Agent Integration Developer Tool, configure it for the Marketplace repository.

1. Set `marketplace` as the default working repository:

   ```shell

   ddev config set marketplace $HOME/dd/marketplace
   ddev config set repo marketplace
   ```

1. If you used a directory other than `$HOME/dd` to clone the `marketplace` directory, use the following command to set your working repository:

   ```shell

   ddev config set marketplace <PATH/TO/MARKETPLACE>
   ddev config set repo marketplace
   ```

[101]: https://github.com/Datadog/marketplace
[102]: https://docs.datadoghq.com/developers/integrations/marketplace_offering
[103]: https://docs.datadoghq.com/developers/integrations/python

{{% /tab %}}

{{< /tabs >}}

## Create your integration

Once you've downloaded Docker, installed an appropriate version of Python, and prepared your development environment, you can start creating an Agent-based integration. 

The following instructions use an example integration called `Awesome`. Follow along using the code from Awesome, or replace Awesome with your own code, as well as the name of your integration within the commands. For example, use `ddev create <your-integration-name>` instead of `ddev create Awesome`. 

### Create scaffolding for your integration

The `ddev create` command runs an interactive tool that creates the basic file and path structure (or scaffolding) necessary for an Agent-based integration.

1. Before you create your first integration directory, try a dry-run using the `-n/--dry-run` flag, which doesn't write anything to the disk:
   ```shell
   ddev create -n Awesome
   ```

   This command displays the path where the files would have been written, as well as the structure itself. Make sure the path in the first line of output matches your repository location.

1. Run the command without the `-n` flag. The tool asks you for an email and name and then creates the files you need to get started with an integration.

    <div class="alert alert-info">If you are creating an integration for the Datadog Marketplace, ensure that your directory follows the pattern of {partner name}_{integration name}.</div>

   ```shell
   ddev create Awesome
   ```

## Write an Agent check

At the core of each Agent-based integration is an *Agent Check* that periodically collects information and sends it to Datadog. 

[Checks][30] inherit their logic from the `AgentCheck` base class and have the following requirements:

- Integrations running on the Datadog Agent v7 or later must be compatible with Python 3. Integrations running on the Datadog Agent v5 and v6 still use Python 2.7.
- Checks must derive from `AgentCheck`.
- Checks must provide a method with this signature: `check(self, instance)`.
- Checks are organized in regular Python packages under the `datadog_checks` namespace. For example, the code for Awesome lives in the `awesome/datadog_checks/awesome/` directory.
- The name of the package must be the same as the check name.
- There are no restrictions on the name of the Python modules within that package, nor on the name of the class implementing the check.

### Implement check logic

For Awesome, the Agent Check is composed of a [service check][25] named `awesome.search` that searches for a string on a web page. It results in `OK` if the string is present, `WARNING` if the page is accessible but the string was not found, and `CRITICAL` if the page is inaccessible. 

To learn how to submit metrics with your Agent Check, see [Custom Agent Check][7].

The code contained within `awesome/datadog_checks/awesome/check.py` looks something like this:

{{< code-block lang="python" filename="check.py" collapsible="true" >}}

import requests

from datadog_checks.base import AgentCheck, ConfigurationError


class AwesomeCheck(AgentCheck):
    """AwesomeCheck derives from AgentCheck, and provides the required check method."""

    def check(self, instance):
        url = instance.get('url')
        search_string = instance.get('search_string')

        # It's a very good idea to do some basic sanity checking.
        # Try to be as specific as possible with the exceptions.
        if not url or not search_string:
            raise ConfigurationError('Configuration error, please fix awesome.yaml')

        try:
            response = requests.get(url)
            response.raise_for_status()
        # Something went horribly wrong
        except Exception as e:
            # Ideally we'd use a more specific message...
            self.service_check('awesome.search', self.CRITICAL, message=str(e))
        # Page is accessible
        else:
            # search_string is present
            if search_string in response.text:
                self.service_check('awesome.search', self.OK)
            # search_string was not found
            else:
                self.service_check('awesome.search', self.WARNING)
{{< /code-block >}}

To learn more about the base Python class, see [Anatomy of a Python Check][8].

## Write validation tests

There are two types of tests:

- [Unit tests for specific functionality](#write-a-unit-test)
- [Integration tests that execute the `check` method and verify proper metrics collection](#write-an-integration-test)

[pytest][9] and [hatch][10] are used to run the tests. Tests are required in order to publish your integration.

### Write a unit test

The first part of the `check` method for Awesome retrieves and verifies two elements from the configuration file. This is a good candidate for a unit test. 

Open the file at `awesome/tests/test_awesome.py` and replace the contents with the following:

{{< code-block lang="python" filename="test_awesome.py" collapsible="true" >}}
import pytest

    # Don't forget to import your integration

from datadog_checks.awesome import AwesomeCheck
from datadog_checks.base import ConfigurationError


@pytest.mark.unit
def test_config():
    instance = {}
    c = AwesomeCheck('awesome', {}, [instance])

    # empty instance
    with pytest.raises(ConfigurationError):
        c.check(instance)

    # only the url
    with pytest.raises(ConfigurationError):
        c.check({'url': 'http://foobar'})

    # only the search string
    with pytest.raises(ConfigurationError):
        c.check({'search_string': 'foo'})

    # this should not fail
    c.check({'url': 'http://foobar', 'search_string': 'foo'})
{{< /code-block >}}

`pytest` has the concept of markers that can be used to group tests into categories. Notice that `test_config` is marked as a `unit` test.

The scaffolding is set up to run all the tests located in `awesome/tests`. To run the tests, run the following command:
```
ddev test awesome
```

### Write an integration test

The [unit test above](#write-a-unit-test) doesn't check the collection logic. To test the logic, you need to [create an environment for an integration test](#create-an-environment-for-the-integration-test) and [write an integration test](#add-an-integration-test).

#### Create an environment for the integration test

The toolkit uses `docker` to spin up an NGINX container and lets the check retrieve the welcome page.

To create an environment for the integration test, create a docker-compose file at `awesome/tests/docker-compose.yml` with the following contents:

{{< code-block lang="yaml" filename="docker-compose.yml" collapsible="true" >}}
version: "3"

services:
  nginx:
    image: nginx:stable-alpine
    ports:
      - "8000:80"

{{< /code-block >}}

Next, open the file at `awesome/tests/conftest.py` and replace the contents with the following:

{{< code-block lang="python" filename="conftest.py" collapsible="true" >}}
import os

import pytest

from datadog_checks.dev import docker_run, get_docker_hostname, get_here

URL = 'http://{}:8000'.format(get_docker_hostname())
SEARCH_STRING = 'Thank you for using nginx.'
INSTANCE = {'url': URL, 'search_string': SEARCH_STRING}


@pytest.fixture(scope='session')
def dd_environment():
    compose_file = os.path.join(get_here(), 'docker-compose.yml')

    # This does 3 things:
    #
    # 1. Spins up the services defined in the compose file
    # 2. Waits for the url to be available before running the tests
    # 3. Tears down the services when the tests are finished
    with docker_run(compose_file, endpoints=[URL]):
        yield INSTANCE


@pytest.fixture
def instance():
    return INSTANCE.copy()
{{< /code-block >}}

#### Add an integration test

After you've setup an environment for the integration test, add an integration test to the `awesome/tests/test_awesome.py` file:

{{< code-block lang="python" filename="test_awesome.py" collapsible="true" >}}
@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_service_check(aggregator, instance):
    c = AwesomeCheck('awesome', {}, [instance])

    # the check should send OK
    c.check(instance)
    aggregator.assert_service_check('awesome.search', AwesomeCheck.OK)

    # the check should send WARNING
    instance['search_string'] = 'Apache'
    c.check(instance)
    aggregator.assert_service_check('awesome.search', AwesomeCheck.WARNING)
{{< /code-block >}}

To speed up development, use the `-m/--marker` option to run integration tests only:
   ```
   ddev test -m integration awesome
   ```
Your integration is almost complete. Next, add the necessary check assets.

## Populate integration assets

The following set of assets created by the `ddev` scaffolding **must** be populated with relevant information to your integration:

`README.md`
: This contains the documentation for your Agent Check, how to set it up, which data it collects, and support information.

`spec.yaml`
: This is used to generate the `conf.yaml.example` using the `ddev` tooling. For more information, see [Configuration Specification][11].

`conf.yaml.example`
: This contains default (or example) configuration options for your Agent Check. **Do not edit this file by hand**. It is generated from the contents of `spec.yaml`. For more information, see the [Configuration file reference documentation][12].

`manifest.json`
: This contains the metadata for your Agent Check such as the title and categories. For more information, see the [Manifest file reference documentation][13].

`metadata.csv`
: This contains the list of all metrics collected by your Agent Check. For more information, see the [Metrics metadata file reference documentation][14].

`service_check.json`
: This contains the list of all Service Checks collected by your Agent Check. For more information, see the [Service check file reference documentation][15].

For more information about the `README.md` and `manifest.json` files, see [Create a Tile][20] and [Integrations Asset Reference][33].

## Build the wheel

The `pyproject.toml` file provides the metadata that is used to package and build the wheel. The wheel contains the files necessary for the functioning of the integration itself, which includes the Agent Check, configuration example file, and artifacts generated during the wheel build.

All additional elements, including the metadata files, are not meant to be contained within the wheel, and are used elsewhere by the Datadog platform and ecosystem. 

To learn more about Python packaging, see [Packaging Python Projects][16].

Once your `pyproject.toml` is ready, create a wheel using one of the following options:

- (Recommended) With the `ddev` tooling: `ddev release build <INTEGRATION_NAME>`.
- Without the `ddev` tooling: `cd <INTEGRATION_DIR> && pip wheel . --no-deps --wheel-dir dist`.

## Install the wheel

The wheel is installed using the Agent `integration` command, available in [Agent v6.10.0 or later][17]. Depending on your environment, you may need to execute this command as a specific user or with specific privileges:

**Linux** (as `dd-agent`):
```bash
sudo -u dd-agent datadog-agent integration install -w /path/to/wheel.whl
```

**OSX** (as admin):
```bash
sudo datadog-agent integration install -w /path/to/wheel.whl
```

**Windows PowerShell** (Ensure that your shell session has _administrator_ privileges):

<details>
  <summary>Agent <code>v6.11</code> or earlier</summary>
  
  ```ps
  & "C:\Program Files\Datadog\Datadog Agent\embedded\agent.exe" integration install -w /path/to/wheel.whl
  ```

</details>

<details open>
  <summary>Agent<code>v6.12</code> or later</summary>
  
  ```ps
  & "C:\Program Files\Datadog\Datadog Agent\bin\agent.exe" integration install -w /path/to/wheel.whl
  ```
</details>

## Populate your tile and publish your integration

Once you have created your Agent-based integration, see the [Create a tile][20] documentation for information on populating the remaining [required assets][31] that appear on your integration tile, and opening a pull request.


## Further reading

{{< partial name="whats-next/whats-next.html" >}}

[1]: https://docs.datadoghq.com/developers/#creating-your-own-solution
[2]: https://github.com/pypa/pipx
[3]: https://docs.datadoghq.com/developers/integrations/python/
[4]: https://docs.docker.com/get-docker/
[5]: https://git-scm.com/book/en/v2/Getting-Started-Installing-Git
[6]: https://github.com/datadog/integrations-extras
[7]: /metrics/custom_metrics/agent_metrics_submission/?tab=count
[8]: https://github.com/DataDog/datadog-agent/blob/6.2.x/docs/dev/checks/python/check_api.md
[9]: https://docs.pytest.org/en/latest
[10]: https://github.com/pypa/hatch
[11]: https://datadoghq.dev/integrations-core/meta/config-specs/
[12]: /developers/integrations/check_references/#configuration-file
[13]: /developers/integrations/check_references/#manifest-file
[14]: /developers/integrations/check_references/#metrics-metadata-file
[15]: /developers/integrations/check_references/#service-check-file
[16]: https://packaging.python.org/en/latest/tutorials/packaging-projects/
[17]: https://docs.datadoghq.com/agent/
[18]: https://docs.datadoghq.com/events/
[19]: https://desktop.github.com/
[20]: https://docs.datadoghq.com/developers/integrations/create_a_tile
[21]: https://github.com/Datadog/integrations-extras
[22]: https://github.com/Datadog/marketplace
[23]: https://app.datadoghq.com/integrations
[24]: https://app.datadoghq.com/marketplace
[25]: https://docs.datadoghq.com/developers/service_checks/
[26]: https://docs.datadoghq.com/logs/
[27]: https://docs.datadoghq.com/monitors/
[28]: https://docs.datadoghq.com/dashboards/
[29]: https://docs.datadoghq.com/logs/log_configuration/pipelines/
[30]: https://docs.datadoghq.com/glossary/#check
[31]: https://docs.datadoghq.com/developers/integrations/create_a_tile/#complete-the-necessary-integration-asset-files
[32]: https://partners.datadoghq.com/
[33]: https://docs.datadoghq.com/developers/integrations/check_references/