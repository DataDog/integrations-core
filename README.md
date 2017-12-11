[![Build Status](https://travis-ci.org/DataDog/integrations-core.svg?branch=master)](https://travis-ci.org/DataDog/integrations-core)
[![Build status](https://ci.appveyor.com/api/projects/status/8w4s2bilp48n43gw?svg=true)](https://ci.appveyor.com/project/Datadog/integrations-core)
# Datadog Agent Core Integrations

This repository contains the Agent Integrations that Datadog officially develops and supports. To add a new integration, please see the [Integrations Extras](https://github.com/DataDog/integrations-extras) repository and the [accompanying documentation](http://docs.datadoghq.com/guides/integration_sdk/).


# Quick development Setup

To get started developing with the integrations-core repo you will need: `gem` and `python`.

We’ve written a gem and a set of scripts to help you get set up, ease development, and provide testing. To begin:

- Run `gem install bundler`
- Run `bundle install`

Once the required Ruby gems have been installed by Bundler, you can easily create a Python environment:

- Run `rake setup_env`. This will install a Python virtual environment along
  with all the components necessary for integration development (including the
  core agent used by the integrations). Some basic software might be needed to
  install the python dependencies like `gcc` and `libssl-dev`.
- Run `source venv/bin/activate` to activate the installed Python virtual
  environment. To exit the virtual environment, run `deactivate`. You can learn
  more about the Python virtual environment on the Virtualenv documentation.

This is a quick setup but from that point you should be able to run the default test suit `rake ci:run`.
To go beyond we advise you to read the full documentation [here](http://docs.datadoghq.com/guides/integration_sdk/).

# Installing the Integrations

The [Datadog Agent](https://github.com/DataDog/dd-agent) contains all core integrations from this repository, so to get started using them, simply install the `datadog-agent` package for your operating system.

Additionally, you may install any individual core integration via its own `dd-check-<integration_name>` package, e.g. `dd-check-nginx`. We build these packages from this repository and release them more often than `datadog-agent`. This allows us to distribute integration updates - and brand new integrations - in between releases of `datadog-agent`.

In other words: on the day of a new `datadog-agent` release, you'll likely get the same version of the nginx check from the agent package as you would from `dd-check-nginx`. But if we haven't released a new agent in 6 weeks and this repository contains a bugfix for the nginx check, install the latest `dd-check-nginx` to override the buggy check packaged with `datadog-agent`.

For a check with underscores in its name, its package name replaces underscores with dashes. For example, the `powerdns_recursor` check is packaged as `dd-check-powerdns-recursor`.

# Building the integrations as Python wheels (work in progress)

First, build our custom manylinux Docker image:

```
git clone git@github.com:trishankatdatadog/manylinux.git
cd manylinux/docker
git checkout trishank_kuppusamy/develop
time sudo docker build -t pypa/manylinux:trishankatdatadog -f Dockerfile-x86_64 .
```

Second, build the wheels using this Docker image:

```
git clone git@github.com:trishankatdatadog/integrations-core.git
cd integrations-core
git checkout trishank_kuppusamy/dockerize-build
# https://stackoverflow.com/a/31334443
time sudo docker run --rm -v `pwd`:/shared:Z pypa/manylinux:trishankatdatadog /shared/build-wheels.sh && ls wheelhouse
```

# Reporting Issues

For more information on integrations, please reference our [documentation](http://docs.datadoghq.com) and [knowledge base](https://help.datadoghq.com/hc/en-us). You can also visit our [help page](http://docs.datadoghq.com/help/) to connect with us.
