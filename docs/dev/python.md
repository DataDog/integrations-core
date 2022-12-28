---
title: Python for Agent Integration Development
kind: documentation

---

This document covers how to setup a Python environment to work on Agent-based Integrations, including installing the interpreter and ensuring all of the required dependencies are present.

## Install Python

Many operating systems come with a pre-installed version of Python. However, the version of Python installed by default may be older than the version used in the Agent, and may lack some required tools and dependencies. To ensure that you've everything you need to get an integration running, install a dedicated Python interpreter.

{{< tabs >}}

{{% tab "MacOS" %}}
Install Python 3.8 using [Homebrew][1]:

1. Update Homebrew:
   ```
   brew update
   ```
1. Install Python:
   ```
   brew install python@3.8
   ```
1. Check the Homebrew installation output and run any additional commands recommended by the installation script.
1. Verify that the Python binary is installed in your `PATH` and that you've installed the correct version:
   ```
   python --version
   ```

[1]: https://brew.sh/
{{% /tab %}}

{{% tab "Windows" %}}
1. Download the [Python 3.8 64-bit executable installer][1] and run it.
1. Select the option to add Python to your PATH.
1. Click **Install Now**.
1. After the installation has completed, restart your machine.
1. Verify that the Python binary is installed in your `PATH` and that you've installed the correct version:
   ```
   python --version
   ```

[1]: https://www.python.org/downloads/release/python-3810/
{{% /tab %}}

{{% tab "Linux" %}}
For Linux installations, avoid modifying your system Python. Datadog recommends installing Python 3.8 using [pyenv][1] or [miniconda][2].

[1]: https://github.com/pyenv/pyenv#automatic-installer
[2]: https://conda.io/projects/conda/en/stable/user-guide/install/linux.html
{{% /tab %}}

{{< /tabs >}}

## Install pipx

The `pipx` python package is required for the `ddev` command line tools.

{{< tabs >}}
{{% tab "MacOS" %}}
1. Install pipx:
   ```
   brew install pipx
   ```
1. Check the Homebrew installation output and run any additional commands recommended by the installation script.
1. Verify that pipx is installed:
   ```
   pipx --version
   ```
{{% /tab %}}

{{% tab "Windows" %}}
1. Install pipx:
   ```
   python -m pip install pipx
   ```
1. Verify that pipx is installed:
   ```
   pipx --version
   ```
{{% /tab %}}

{{% tab "Linux" %}}
1. Install pipx:
   ```
   python -m pip install pipx
   ```
1. Verify that pipx is installed:
   ```
   pipx --version
   ```
{{% /tab %}}
{{< /tabs >}}