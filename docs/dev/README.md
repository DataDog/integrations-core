# Working with Agent based integrations

## Overview

Being able to see all of your metrics from across your infrastructure is key
within Datadog. There are currently three options to get data into Datadog:

* Push data from the source to Datadog
* Crawl the data source's API
* Have the Datadog Agent pick up the information from the source

This guide covers the latter option, providing the informations needed to work
with the Agent based integrations, also referred to as Checks. Checks make the Agent
able to collect and send metrics, events and service checks to Datadog.

## Create a new integration

While we do have guides to submit
[custom metrics](https://docs.datadoghq.com/developers/metrics/) via our
[API](https://docs.datadoghq.com/api/) and
[code instrumentation](https://docs.datadoghq.com/developers/libraries/),
it's possible you might want to see a certain source become an integration
available in the [official core repository](https://github.com/DataDog/integrations-core)
and bundled into the Agent package.

Overall, the largest deciding factor in what integrations we build is what our
clients request. You have two options to propose an integration:

* Reach out to support@datadoghq.com and tell us what metrics you would like to
  see from a given source.
* Implement the integration yourself and submit the code to the
  [official extras repository](https://github.com/DataDog/integrations-extras)

If you want to create a new Check from scratch you can start by looking at the
[howto](new_check_howto.md).

## Development guide

You can follow these instructions to get a working copy of any check on your
local Python environment; this is mostly useful to run tests or for tinkering in
general.

### Prerequisites

* Python 2.7, see [this page](python.md) for more details.

### Quickstart

The project comes with a requirements file you can pass to `pip` to install all
the dependencies needed to work with any check. From the root of the repo, run:

```
pip install -r requirements-dev.txt
```

To work with a specific check you need to install its own dependencies. The easiest
way to iterate on a check development is installing the wheel itself in editable mode.
For example, if you want to do this for the `disk` check run the following:

```
cd disk && pip install -e .
```

To double check everything is working as expected you can run:

```
python -c"from datadog_checks.disk import Disk"
```

if the commands ends without errors, you're good to go!

### Testing

To run the testsuite for a given check you can either use `tox`, like:

```
cd {integration} && tox
```

or invoke [Pytest](https://docs.pytest.org/en/latest/) directly:

```
cd {integration} && py.test
```

If you updated the test requirements for a check, run `tox --recreate` for changes to be effective.

### Building

`setup.py` provides the setuptools setup script that will help us package and
build the wheel. If you wish to learn more about python packaging please take a
look at the official python documentation [here](https://packaging.python.org/tutorials/distributing-packages/)

Once your setup.py is ready, creating a wheel is a easy as:

```
cd {integration}
python setup.py bdist_wheel
```
