---
title: Create a new integration
kind: documentation
aliases:
    - /developers/integrations/integration_sdk/
    - /developers/integrations/testing/
    - /integrations/datadog_checks_dev/
    - /guides/new_integration/
---

To consider an Agent-based integration complete, and thus ready to be included in the core repository and bundled with the Agent package, a number of prerequisites must be met:

* A `README.md` file with the right format
* A battery of tests verifying metrics collection
* A set of images to be used in the UI tile
* A `metadata.csv` file listing all of the collected metrics
* A complete `manifest.json` file
* If the integration collects Service Checks, the `service_checks.json` must be complete as well

These requirements are used during the code review process as a checklist. This documentation covers the requirements and implementation details for a brand new integration.

## Prerequisites

* Python 3.7+ needs to be available on your system; Python 2.7 is optional but recommended.
* Docker to run the full test suite.

In general, creating and activating [Python virtual environments][1] to isolate the development environment is good practice; however, it is not mandatory. For more information, see the [Python Environment documentation][2].

## Setup

Clone the [integrations-extras repository][3]. By default, that tooling expects you to be working in the `$HOME/dd/` directory—this is optional and can be adjusted via configuration later.

```shell
mkdir $HOME/dd && cd $HOME/dd       # optional
git clone https://github.com/DataDog/integrations-extras.git
```

### Developer toolkit

The [Developer Toolkit][4] is comprehensive and includes a lot of functionality. Here's what you need to get started:

```
pip install "datadog-checks-dev[cli]"
```

If you chose to clone this repository to somewhere other than `$HOME/dd/`, you'll need to adjust the configuration file:

```
ddev config set extras "/path/to/integrations-extras"
```

If you intend to work primarily on `integrations-extras`, set it as the default working repository:

```
ddev config set repo extras
```

**Note**: If you do not do this step, you'll need to use `-e` for every invocation to ensure the context is `integrations-extras`:

```
ddev -e COMMAND [OPTIONS]
```

## Scaffolding

One of the developer toolkit features is the `create` command, which creates the basic file and path structure (or "scaffolding") necessary for a new integration.

### Dry-run

Let's try a dry-run using the `-n/--dry-run` flag, which won't write anything to disk.

```
ddev create -n awesome
```

This will display the path where the files would have been written, as well as the structure itself. For now, just make sure that the path in the *first line* of output matches your Extras repository.

### Interactive mode

The interactive mode is a wizard for creating new integrations. By answering a handful of questions, the scaffolding will be set up and lightly pre-configured for you.

```
ddev create awesome
```

After answering the questions, the output will match that of the dry-run above, except in this case the scaffolding for your new integration will actually exist!

## Write the check

### Intro

A Check is a Python class with the following requirements:

* It must derive from `AgentCheck`
* It must provide a method with this signature: `check(self, instance)`

Checks are organized in regular Python packages under the `datadog_checks` namespace, so your code should live under `awesome/datadog_checks/awesome`. The only requirement is that the name of the package has to be the same as the check name. There are no particular restrictions on the name of the Python modules within that package, nor on the name of the class implementing the check.

### Implement check logic

Let's say we want to create a Service Check named `awesome.search` that searches for a string on a web page. It will result in `OK` if the string is present, `WARNING` if the page is accessible but the string was not found, and `CRITICAL` if the page is inaccessible.

The code contained within `awesome/datadog_checks/awesome/awesome.py` would look something like this:

```python
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
```

To learn more about the base Python class, see the [Python API documentation][5].

### Writing tests

There are two basic types of tests: unit tests for specific functionality, and integration tests that execute the `check` method and verify proper metrics collection. Tests are _required_ if you want your integration to be included in `integrations-extras`. Note that [pytest][6] and [tox][7] are used to run the tests.

For more information, see the [Datadog Checks Dev documentation][8].

#### Unit test

The first part of the `check` method retrieves and verifies two pieces of information we need from the configuration file. This is a good candidate for a unit test. Open the file at `awesome/tests/test_awesome.py` and replace the contents with something like this:

```python
import pytest

# Don't forget to import your integration!
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
```

`pytest` has the concept of _markers_ that can be used to group tests into categories. Notice we've marked `test_config` as a `unit` test.

The scaffolding has already been set up to run all tests located in `awesome/tests`. Run the tests:

```
ddev test awesome
```

#### Building an integration test

This test doesn't check our collection _logic_ though, so let's add an integration test. We use `docker` to spin up an Nginx container and let the check retrieve the welcome page. Create a compose file at `awesome/tests/docker-compose.yml` with the following contents:

```yaml
version: '3'

services:
  nginx:
    image: nginx:stable-alpine
    ports:
      - "8000:80"
```

Now, open the file at `awesome/tests/conftest.py` and replace the contents with something like this:

```python
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
```

#### Integration test

Finally, add an integration test to our `awesome/tests/test_awesome.py` file:

```python
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
```

Run only integration tests for faster development using the `-m/--marker` option:

```
ddev test -m integration awesome
```

The check is almost done. Let's add the final touches by adding the integration configurations.

## Configuration

### Populate the README

The `awesome/README.md` file provided by our scaffolding already has the correct format. You must fill out the document with the relevant information.

### Configuration file

When preparing a new integration, you must include an example configuration that contains the necessary options and reasonable defaults. The example configuration file, which in this case is located at `awesome/datadog_checks/awesome/data/conf.yaml.example`, has two top-level elements: `init_config` and `instances`. The configuration under `init_config` is applied to the integration globally, and is used in every instantiation of the integration, whereas anything within `instances` is specific to a given instantiation.

Configuration blocks in either section take the following form:

```yaml
## @<COMMAND> [- <ARGS>]
## <DESCRIPTION LINE 1>
## <DESCRIPTION LINE 2>
#
<KEY>: <VALUE>
```

Configuration blocks follow a few guidelines:

* Description must not be empty
* Placeholders should always follow this format: `<THIS_IS_A_PLACEHOLDER>`, as per the documentation [contributing guidelines][9]:
* All required parameters are **not** commented by default.
* All optional parameters are commented by default.
* If a placeholder has a default value for an integration (like the status endpoint of an integration), it can be used instead of a generic placeholder.

#### @param specification

Practically speaking, the only command is `@param`, which is used to describe configuration blocks—primarily for documentation purposes. `@param` is implemented using one of the following forms:

```
@param <name> - <type> - required
@param <name> - <type> - optional
@param <name> - <type> - optional - default: <defval>
```

Arguments:

* `name`: the name of the parameter, e.g. `search_string` (mandatory).
* `type`: the data type for the parameter value (mandatory). Possible values:
  * *boolean*
  * *string*
  * *integer*
  * *double*
  * *float*
  * *dictionary*
  * *list&#42;*
  * *object*
* `defval`: default value for the parameter; can be empty (optional).

`list` and `object` variables span over multiple lines and have special rules.

* In a `list`, individual elements are not documented with the `@param` specification
* In an `object` you can choose to either document elements individually with the `@param` specification or to have a common top-level description following the specification of the object itself.

#### Optional parameters

An optional parameter must be commented by default. Before every line the parameter spans on, add `# ` (note the space) with the same indentation as the `@param` specification.

#### Block comments

You can add a block comment anywhere in the configuration file with the following rules:

* Comments start with `## ` (note the space)
* Comments should be indented like any variable (the hyphen doesn't count)


#### Example configuration

The `awesome/datadog_checks/awesome/data/conf.yaml.example` for the Awesome service check:

```yaml
init_config:
  ## Block comment in the init_config
  ## part.

## Block comment outside
## of the init_config part.

instances:

    ## @param url - string - required
    ## The URL you want to check
    ## (Note the indentation with the hyphen)
    #
  - url: http://example.org

    ## @param search_string - string - required
    ## The string to search for
    #
    search_string: "Example Domain"

    ## @param user - object - optional
    ## The user should map to the structure
    ## {'name': ['<FIRST_NAME>', '<LAST_NAME>'], 'username': <USERNAME>, 'password': <PASSWORD>}
    #
    # user:
    #   name:
    #     - <FIRST_NAME>
    #     - <LAST_NAME>
    #   username: <USERNAME>
    #   password: <PASSWORD>

    ## @param options - object - required
    ## Optional flags you can set
    #
    options:

      ## @param follow_redirects - boolean - optional - default: false
      ## Set to true to follow 301 Redirect
      #
      # follow_redirects: false

```

For more information about YAML syntax, see [Wikipedia][17]. Feel free to play around with the [Online YAML Parser][18], too!

### Manifest file

Every integration contains a `manifest.json` file that describes operating parameters, positioning within the greater Datadog integration eco-system, and other such items.

The complete list of mandatory and optional attributes for the `manifest.json` file:

| Attribute                   | Type            | Mandatory/Optional | Description                                                                                                                                                                                                              |
| --------------------        | --------------- | ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `integration_id`            | String          | Mandatory          | The unique identifying name of this integration. Usually kebab case of the Display Name                                                                                                                                  |
| `categories`                | Array of String | Mandatory          | Integration categories used on the [public documentation integrations page][10].                                                                                                                                         |
| `creates_events`            | Boolean         | Mandatory          | If the integration should be able to create events. If this is set to `false`, attempting to create an event from the integration results in an error.                                                                   |
| `display_name`              | String          | Mandatory          | Title displayed on the corresponding integration tile in the Datadog application and on the [public documentation integrations page][10]                                                                                 |
| `guid`                      | String          | Mandatory          | Unique ID for the integration. [Generate a UUID][11]                                                                                                                                                                     |
| `is_public`                 | Boolean         | Mandatory          | If set to `false` the integration `README.md` content is not indexed by bots in the Datadog public documentation.                                                                                                        |
| `maintainer`                | String          | Mandatory          | Email of the owner of the integration.                                                                                                                                                                                   |
| `manifest_version`          | String          | Mandatory          | Version of the current manifest.                                                                                                                                                                                         |
| `name`                      | String          | Mandatory          | Unique name for the integration. Use the folder name for this parameter.                                                                                                                                                 |
| `public_title`              | String          | Mandatory          | Title of the integration displayed on the documentation. Should follow the following format: `Datadog-<INTEGRATION_NAME> integration`.                                                                                   |
| `short_description`         | String          | Mandatory          | This text appears at the top of the integration tile as well as the integration's rollover text on the integrations page. Maximum 80 characters.                                                                         |
| `support`                   | String          | Mandatory          | Owner of the integration.                                                                                                                                                                                                |
| `supported_os`              | Array of String | Mandatory          | List of supported OSs. Choose among `linux`,`mac_os`, and `windows`.                                                                                                                                                     |
| `type`                      | String          | Mandatory          | Type of the integration, should be set to `check`.                                                                                                                                                                       |
| `aliases`                   | Array of String | Optional           | A list of URL aliases for the Datadog documentation.                                                                                                                                                                     |
| `description`               | String          | Optional           | This text appears when sharing an integration documentation link.                                                                                                                                                        |
| `is_beta`                   | Boolean         | Optional           | Default `false`. If set to `true` the integration `README.md` content is not displayed in the Datadog public documentation.                                                                                              |
| `metric_to_check`           | String          | Optional           | The presence of this metric determines if this integration is working properly. If this metric is not being reported when this integration is installed, the integration is marked as broken in the Datadog application. |
| `metric_prefix`             | String          | Optional           | The namespace for this integration's metrics. Every metric reported by this integration will be prepended with this value.                                                                                               |
| `process_signatures`        | Array of String | Optional           | A list of signatures that matches the command line of this integration.                                                                                                                                                  |
| `assets`                    | Dictionary      | Mandatory          | Relative location of where certain asset files live and their respective names.                                                                                                                                          |
| `assets`-> `dashboards`     | Dictionary      | Mandatory          | Dictionary where the key is the name of the dashboard (must be globally unique across integrations) and the value is the relative file path where the dashboard definition lives.                                        |
| `assets`-> `monitors`       | Dictionary      | Mandatory          | Dictionary where the key is the name of the monitor (must be globally unique across integrations) and the value is the relative file path where the dashboard definition lives.                                          |
| `assets`-> `service_checks` | String          | Mandatory          | Relative location of where the `service_checks.json` file lives.                                                                                                                                                         |

##### Example manifest config

Our example integration has a very simple `awesome/manifest.json`, the bulk of which is generated by the tooling. Note that the `guid` must be unique (and valid), so do *not* use the one from this example—the tooling will generate one for you in any case.

```json
{
  "display_name": "awesome",
  "maintainer": "email@example.org",
  "manifest_version": "1.0.0",
  "name": "awesome",
  "metric_prefix": "awesome.",
  "metric_to_check": "",
  "creates_events": false,
  "short_description": "",
  "guid": "x16b8750-df1e-46c0-839a-2056461b604x",
  "support": "contrib",
  "supported_os": [
    "linux",
    "mac_os",
    "windows"
  ],
  "public_title": "Datadog-awesome Integration",
  "categories": [
    "web"
  ],
  "type": "check",
  "is_public": false,
  "integration_id": "awesome",
  "assets": {
    "dashboards": {
      "Awesome Overview": "assets/dashboards/overview.json",
      "Awesome Investigation Dashboard": "assets/dashboards/investigation.json"
    },
    "monitors": {},
    "service_checks": "assets/service_checks.json"
  }
}
```

#### Metrics metadata file

The `metadata.csv` file describes all of the metrics that can be collected by the integration.

Descriptions of each column of the `metadata.csv` file:

| Column name     | Mandatory/Optional | Description                                                                                                                                                                     |
| ---             | ----               | ----                                                                                                                                                                            |
| `metric_name`   | Mandatory          | Name of the metric.                                                                                                                                                             |
| `metric_type`   | Mandatory          | [Type of the metric][12].                                                                                                                                                       |
| `interval`      | Optional           | Collection interval of the metric in second.                                                                                                                                    |
| `unit_name`     | Optional           | Unit of the metric. [Complete list of supported units][13].                                                                                                                     |
| `per_unit_name` | Optional           | If there is a unit sub-division, i.e `request per second`                                                                                                                       |
| `description`   | Optional           | Description of the metric.                                                                                                                                                      |
| `orientation`   | Mandatory          | Set to `1` if the metric should go up, i.e `myapp.turnover`. Set to `0` if the metric variations are irrelevant. Set to `-1` if the metric should go down, i.e `myapp.latency`. |
| `integration`   | Mandatory          | Name of the integration that emits the metric. Must be the normalized version of the `display_name` from the `manifest.json` file. Any character besides letters, underscores, dashes and numbers are converted to underscores. E.g. `Openstack Controller` -> `openstack_controller`and `ASP.NET` -> `asp_net` and `CRI-o` -> `cri-o`.                                                                                                                                |
| `short_name`    | Mandatory          | Explicit Unique ID for the metric.                                                                                                                                              |

##### Example metadata config

Our example integration doesn't send any metrics, so in this case the generated `awesome/metadata.csv` contains only the row containing CSV column names.

#### Service check file

The `service_check.json` file describes the service checks made by the integration.

The `service_checks.json` file contains the following mandatory attributes:

| Attribute       | Description                                                                                                              |
| ----            | ----                                                                                                                     |
| `agent_version` | Minimum Agent version supported.                                                                                         |
| `integration`   | The name of the integration that emits this service check. Must be the non-normalized `display_name` from `manifest.json`.                                                                                                      |
| `check`         | Name of the Service Check. It must be unique.                                                                            |
| `statuses`      | List of different status of the check, to choose among `ok`, `warning`, and `critical`. `unknown` is also a possibility. |
| `groups`        | [Tags][14] sent with the Service Check.                                                                                  |
| `name`          | Displayed name of the Service Check. The displayed name must be self-explanatory and unique across all integrations.                             |
| `description`   | Description of the Service Check                                                                                         |

##### Example service check config

Our example integration contains a service check, so we need to add it to the `awesome/assets/service_checks.json` file:

```json
[
    {
        "agent_version": "6.0.0",
        "integration": "awesome",
        "check": "awesome.search",
        "statuses": ["ok", "warning", "critical"],
        "groups": [],
        "name": "Awesome search!",
        "description": "Returns `CRITICAL` if the check can't access the page, `WARNING` if the search string was not found, or `OK` otherwise."
    }
]
```

### Add images and logos

The directory structure for images and logos:

```
    awesome/
    ├── images
    │   └── an_awesome_image.png
    ├── assets
    │   └── logos/
            ├── avatars-bot.png
            ├── saas_logos-bot.png
            └── saas_logos-small.png
```

The `images` folder contains all images that are used in the integration tile. They must be referenced in the `## Overview` and/or `## Setup` sections in `README.md` as Markdown images using their public URLs. Because the `integrations-core` and `integrations-extras` repositories are public, a public URL can be obtained for any of these files via `https://raw.githubusercontent.com`:

```markdown
![snapshot](https://raw.githubusercontent.com/DataDog/integrations-extras/master/awesome/images/snapshot.png)
```

The `assets/logos/` directory must contain **three** images with filenames and sizes that match the following specifications _exactly_. Underneath each specification is a list of places where the images may appear in the web app.

#### saas_logos-bot.png (200 × 128)

* Integration tile images at `/account/settings`
* Description heading at `/account/settings#integrations/{integration_name}`
* Integration monitor tiles and search bar results images at `/monitors#create/integration`

#### saas_logos-small.png (120 × 60)

* Integration dashboards list images at `/dash/list`
* Some integration dashboards/screenboards at `/dash/integration/{integration_dash_name}`

#### avatars-bot.png (128 × 128)

* Event stream at `/event/stream`
* Notification icons at `/report/monitor`

### Building

`setup.py` provides the setuptools setup script that helps us package and build the wheel. To learn more about Python packaging, take a look at [the official Python documentation][15].

Once your `setup.py` is ready, create a wheel:

- With the `ddev` tooling (recommended): `ddev release build <INTEGRATION_NAME>`
- Without the `ddev` tooling: `cd <INTEGRATION_DIR> && python setup.py bdist_wheel`

#### What's in the wheel?

The wheel contains only the files necessary for the functioning of the integration itself. This includes the Check itself, the configuration example file, and some artifacts generated during the build of the wheel. All of the other elements, including images, metadata files, and so forth, are *not* meant to be contained within the wheel. These latter elements are used elsewhere by the greater Datadog platform and eco-system.

### Installing

The wheel is installed via the Agent `integration` command, available in [Agent v6.10.0 and up][16]. Depending on your environment, you may need to execute this command as a specific user or with particular privileges:

**Linux** (as `dd-agent`):
```
sudo -u dd-agent datadog-agent integration install -w /path/to/wheel.whl
```

**OSX** (as admin):
```
sudo datadog-agent integration install -w /path/to/wheel.whl
```

**Windows** (Ensure that your shell session has _administrator_ privileges):

For Agent versions <= 6.11:
```
"C:\Program Files\Datadog\Datadog Agent\embedded\agent.exe" integration install -w /path/to/wheel.whl
```

For Agent versions >= 6.12:
```
"C:\Program Files\Datadog\Datadog Agent\bin\agent.exe" integration install -w /path/to/wheel.whl
```


[1]: https://virtualenv.pypa.io/en/stable
[2]: https://github.com/DataDog/integrations-core/blob/master/docs/dev/python.md
[3]: https://github.com/DataDog/integrations-extras
[4]: https://github.com/DataDog/integrations-core/tree/master/datadog_checks_dev
[5]: https://github.com/DataDog/datadog-agent/blob/6.2.x/docs/dev/checks/python/check_api.md
[6]: https://docs.pytest.org/en/latest
[7]: https://tox.readthedocs.io/en/latest
[8]: https://github.com/DataDog/integrations-core/tree/master/datadog_checks_dev#development
[9]: https://github.com/DataDog/documentation/blob/master/CONTRIBUTING.md
[10]: https://docs.datadoghq.com/integrations
[11]: https://www.uuidgenerator.net
[12]: https://docs.datadoghq.com/developers/metrics/metrics_type/
[13]: https://docs.datadoghq.com/developers/metrics/metrics_units/
[14]: https://docs.datadoghq.com/getting_started/tagging
[15]: https://packaging.python.org/tutorials/distributing-packages
[16]: https://docs.datadoghq.com/agent/
[17]: https://en.wikipedia.org/wiki/YAML
[18]: http://yaml-online-parser.appspot.com/
