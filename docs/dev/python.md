---
title: Python environment for Agent integration development
kind: documentation
---

This document covers how to setup a Python environment to work on Agent-based Integrations, including installing the interpreter and ensuring all of the required dependencies are present.

## Python 2 or Python 3?

Integrations run either within the Agent's embedded Python environment or within the testing environment. The current version of the embedded environment is recorded in the [Omnibus code][1]. The Agent and testing environments are Python 2 for Agent v6, and Python 3 for Agent v7. Make sure your Integrations are compatible with both versions.

## Install Python

Many operating systems come with Python pre-installed. If your system Python is too old, or if it is not pre-installed, you must install an appropriate version. The installation and maintenance of Python in every operating system is outside the scope of this document, however, some pointers are provided for your benefit.

### macOS

Any recent version of macOS comes with Python pre-installed, however, it may be older than the version used in the Agent, and might also lack required tools and dependencies. You must install a fresh, dedicated Python interpreter that you can manage _without_ the App Store.

Some options include:

- [Homebrew][2]: Follow the "[Doing it Right][3]" instructions.
- [Miniconda][4]: Follow the "[Conda installation][5]" instructions.

It is recommended to install an [environment manager](#virtual-environment-manager) in order to preserve a clean system Python.

### Linux

All mainstream distributions of Linux come with Python pre-installed — likely one of an acceptable version level. It is recommended to install an [environment manager](#virtual-environment-manager) in order to preserve a clean system Python. Refer to your distribution's package management documentation for more information.

### Windows

Windows does not normally have a Python environment present. The [official Python documentation][6] contains detailed installation instructions and links to further documentation and tooling.

## Virtual environment manager

Each integration has its own set of dependencies that must be added to Python in order to run the tests, or just to try out the collection code. To avoid polluting your Python installation with libraries and packages that would only be used by an Integration, use a "virtual environment". A virtual environment is a self contained directory tree that contains an isolated Python installation. When a virtual environment is active, any package you install goes into that directory without affecting the system wide Python installation.

### Virtualenv and Virtualenvwrapper

Datadog recommends using [Virtualenv][7] to manage Python virtual environments, and [virtualenvwrapper][8] to make the process smoother. There's a [comprehensive guide][9] in the Hitchhiker's Guide to Python describing how to set up these two tools.

### Miniconda

If you're using Miniconda, a tool to manage virtual environments is included. Refer to the [official guide][10] for more information.

[1]: https://github.com/DataDog/omnibus-software/blob/master/config/software/python.rb#L21
[2]: https://brew.sh/#install
[3]: https://docs.python-guide.org/en/latest/starting/install/osx/#doing-it-right
[4]: https://repo.continuum.io/miniconda/Miniconda2-latest-MacOSX-x86_64.sh
[5]: https://conda.io/docs/user-guide/install/macos.html
[6]: https://docs.python.org/2.7/using/windows.html
[7]: https://pypi.python.org/pypi/virtualenv
[8]: https://virtualenvwrapper.readthedocs.io/en/latest/index.html
[9]: https://docs.python-guide.org/en/latest/dev/virtualenvs/#lower-level-virtualenv
[10]: https://conda.io/docs/user-guide/tasks/manage-environments.html
