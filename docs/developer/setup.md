# Setup

-----

This will be relatively painless, we promise!

## Integrations

You will need to clone [integrations-core][] and/or [integrations-extras][] depending on which integrations
you intend to work on.

## Python

To work on any integration you must install Python 3.8.

After installation, restart your terminal and ensure that your newly installed Python comes first in your `PATH`.

=== "macOS"
    First update the formulae and [Homebrew][homebrew-home] itself:

    ```
    brew update
    ```

    then install Python:

    ```
    brew install python@3.8
    ```

    After it completes, check the output to see if it asked you to run any extra commands and if so, execute them.

    Verify successful `PATH` modification:

    ```
    which -a python
    ```

=== "Windows"
    Windows users have it the easiest.

    Simply download the [Python 3.8 64-bit executable installer](https://www.python.org/downloads/release/python-3810/) and run it.
    When prompted, be sure to select the option to add to your `PATH`. Also, it is recommended that you choose the per-user installation method.

    Verify successful `PATH` modification:

    ```
    where python
    ```

=== "Linux"
    Ah, you enjoy difficult things. Are you using Gentoo?

    We recommend using either [Miniconda][miniconda-docs] or [pyenv][pyenv-github] to install Python 3.8. Whatever you do, never modify the system Python.

    Verify successful `PATH` modification:

    ```
    which -a python
    ```

## pipx

To install certain command line tools, you'll need [pipx](https://github.com/pypa/pipx).

=== "macOS"
    Run:

    ```
    brew install pipx
    ```

    After it completes, check the output to see if it asked you to run any extra commands and if so, execute them.

    Verify successful `PATH` modification:

    ```
    which -a pipx
    ```

=== "Windows"
    Run:

    ```
    python -m pip install pipx
    ```

    Verify successful `PATH` modification:

    ```
    where pipx
    ```

=== "Linux"
    Run:

    ```
    python -m pip install --user pipx
    ```

    Verify successful `PATH` modification:

    ```
    which -a pipx
    ```

## ddev

### Installation

You have 2 options to install the CLI.

!!! warning
    For either option, if you are on macOS/Linux do not use `sudo`! Doing so will result in a broken installation.

#### Stable

The latest released version may be installed from [PyPI][].

=== "macOS"
    Remove any executables shown in the output of `which -a ddev` and make sure that there is no active virtual environment, then run:

    === "ARM"
        ```
        pipx install ddev --python /opt/homebrew/bin/python3.8
        ```
    === "Intel"
        ```
        pipx install ddev --python /usr/local/bin/python3.8
        ```

=== "Windows"
    Run:

    ```
    pipx install ddev
    ```

=== "Linux"
    Run:

    ```
    pipx install ddev
    ```

#### Development

This is if you cloned [integrations-core][] and want to always use the version based on the current branch.

=== "macOS"
    Remove any executables shown in the output of `which -a ddev` and make sure that there is no active virtual environment, then run:

    === "ARM"
        ```
        pipx install -e /path/to/integrations-core/ddev --python /opt/homebrew/opt/python@3.8/bin/python3.8
        ```
    === "Intel"
        ```
        pipx install -e /path/to/integrations-core/ddev --python /usr/local/opt/python@3.8/bin/python3.8
        ```

=== "Windows"
    Run:

    ```
    pipx install -e /path/to/integrations-core/ddev
    ```

=== "Linux"
    Run:

    ```
    pipx install -e /path/to/integrations-core/ddev
    ```

!!! note
    Be aware that this method does not keep track of dependencies so you will need to re-run the command if/when the required dependencies are changed.

### Upgrade

Upgrade (or re-sync dependencies for [development](#development) versions) at any time by running:

```
pipx upgrade ddev
```

### Configuration

Upon the first invocation, `ddev` will create its [config file](ddev/configuration.md) if it does not yet exist.

You will need to set the location of each cloned repository:

```
ddev config set <REPO> /path/to/integrations-<REPO>
```

The `<REPO>` may be either `core` or `extras`.

By default, the repo `core` will be the target of all commands. If you want to switch to `integrations-extras`, run:

```
ddev config set repo extras
```

## Docker

Docker is used in nearly every integration's test suite therefore we simply require it to avoid confusion.

=== "macOS"
    1. Install [Docker Desktop for Mac][docker-install-mac].
    1. Right-click the Docker taskbar item and update **Preferences > File Sharing** with any locations you need to open.

=== "Windows"
    1. Install [Docker Desktop for Windows][docker-install-windows].
    1. Right-click the Docker taskbar item and update **Settings > Shared Drives** with any locations you need to open e.g. `C:\`.

=== "Linux"
    1. Install Docker Engine for your distribution:

        === "Ubuntu"
            [Docker CE for Ubuntu][docker-install-ubuntu]
        === "Debian"
            [Docker CE for Debian][docker-install-debian]
        === "Fedora"
            [Docker CE for Fedora][docker-install-fedora]
        === "CentOS"
            [Docker CE for CentOS][docker-install-centos]

    1. Add your user to the `docker` group:

        ```bash
        sudo usermod -aG docker $USER
        ```

    1. Sign out and then back in again so your changes take effect.

After installation, restart your terminal one last time.
