---
title: Working with Agent-based integrations
kind: documentation
---

## Overview

Being able to see all of your metrics from across your infrastructure is key within Datadog. There are currently three ways to get data into Datadog:

1. Push data from the source to Datadog
2. Crawl the data source's API
3. Have the Datadog Agent pick up the information from the source

This guide covers the latter option, providing the information needed to work with the Agent based integrations, also referred to as Checks. Checks make the Agent able to collect and send metrics, events and service checks to Datadog.

## Create a new integration

While we do have guides to submit [custom metrics][1] via our [API][2] and [code instrumentation][3], it's possible you might want to see a certain source become an integration available in the [official core repository][4] and bundled into the Agent package.

Overall, the largest deciding factor in what integrations we build is what our clients request. You have two options to propose an integration:

* [Reach out to support@datadoghq.com][5] and tell us what metrics you would like to see from a given source.
* Implement the integration yourself and submit the code to the [official extras repository][6].

If you want to create a new Check from scratch, start by looking at the [howto][10] documentation.

## Development guide

Follow these instructions to get a working copy of any check on your local Python environment; this is mostly useful to run tests or for tinkering in general.

### Prerequisites

* Python 2.7, see [this page][7] for more details.

### Quickstart

The project comes with a requirements file, pass it to `pip` to install all the dependencies needed to work with any check. From the root of the repo, run:

```
pip install -r requirements-dev.txt
```

To work with a specific check you need to install its own dependencies. The easiest way to iterate on a check development is installing the wheel itself in editable mode. For example, if you want to do this for the `disk` check run the following:

```
cd disk && pip install -e .
```

To double check everything is working as expected run:

```
python -c"from datadog_checks.disk import Disk"
```

if the commands ends without errors, you're good to go!

### Testing

To run the test suite for a given check, either use `tox`, like:

```
cd {integration} && tox
```

If you updated the test requirements for a check, run `tox --recreate` for changes to be effective.

### Building

`setup.py` provides the setuptools setup script that will help us package and build the wheel. To learn more about python packaging take a look at [the official python documentation][9]

Once your setup.py is ready, creating a wheel is a easy as:

```
  cd {integration}
  python setup.py bdist_wheel
```

[1]: https://docs.datadoghq.com/developers/metrics/
[2]: https://docs.datadoghq.com/api/
[3]: https://docs.datadoghq.com/developers/libraries/
[4]: https://github.com/DataDog/integrations-core
[5]: https://docs.datadoghq.com/help/
[6]: https://github.com/DataDog/integrations-extras
[7]: https://github.com/DataDog/integrations-core/blob/master/docs/dev/python.md
[8]: https://docs.pytest.org/en/latest/
[9]: https://packaging.python.org/tutorials/distributing-packages/
[10]: https://github.com/DataDog/integrations-core/blob/master/docs/dev/new_check_howto.md 
