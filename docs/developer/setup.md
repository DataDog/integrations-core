# Setup

-----

This will be relatively painless, we promise!

## Integrations

You will need to clone [integrations-core](https://github.com/DataDog/integrations-core) and/or
[integrations-extras](https://github.com/DataDog/integrations-extras) depending on which integrations
you intend to work on.

## Python

To work on any integration you must install Python 3.8+.

After installation, restart your terminal and ensure that your newly installed Python comes first in your `PATH`.

=== "macOS"
    We recommend using [Homebrew](https://brew.sh).

    First update the formulae and Homebrew itself:

    ```
    brew update
    ```

    then either install Python:

    ```
    brew install python
    ```

    or upgrade it:

    ```
    brew upgrade python
    ```

    After it completes, check the output to see if it asked you to run any extra commands and if so, execute them.

    Verify successful `PATH` modification:

    ```
    which -a python
    ```

=== "Windows"
    Windows users have it the easiest.

    Simply download the latest x86-64 executable installer from https://www.python.org/downloads/windows and run it.
    When prompted, be sure to select the option to add to your `PATH`. Also, it is recommended that you choose the per-user installation method.

    Verify successful `PATH` modification:

    ```
    where python
    ```

=== "Linux"
    Ah, you enjoy difficult things. Are you using Gentoo?

    We recommend using either [Miniconda](https://docs.conda.io/en/latest/miniconda.html) or [pyenv](https://github.com/pyenv/pyenv). Whatever you do, never modify the system Python.

    Verify successful `PATH` modification:

    ```
    which -a python
    ```

## ddev

### Installation

You have 2 options to install the CLI provided by the package [datadog-checks-dev](ddev/layers.md).

!!! warning
    For either option, if you are on macOS/Linux do not use `sudo`! Doing so will result in a broken installation.

#### Development

If you cloned [integrations-core](https://github.com/DataDog/integrations-core) and want to always use the version based on the current branch, run:

```
python -m pip install -e "path/to/datadog_checks_dev[cli]"
```

!!! note
    Be aware that this method does not keep track of dependencies so you will need to re-run the command if/when the required dependencies are changed.

#### Stable

The latest released version may be installed from [PyPI](https://pypi.org):

```
python -m pip install --upgrade "datadog-checks-dev[cli]"
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
    1. Install [Docker Desktop for Mac](https://docs.docker.com/docker-for-mac/install).
    1. Right-click the Docker taskbar item and update **Preferences > File Sharing** with any locations you need to open.

=== "Windows"
    1. Install [Docker Desktop for Windows](https://docs.docker.com/docker-for-windows/install).
    1. Right-click the Docker taskbar item and update **Settings > Shared Drives** with any locations you need to open e.g. `C:\`.

=== "Linux"
    1. Install Docker Engine for your distribution:

        === "Ubuntu"
            [Docker CE for Ubuntu](https://docs.docker.com/install/linux/docker-ce/ubuntu)
        === "Debian"
            [Docker CE for Debian](https://docs.docker.com/install/linux/docker-ce/debian)
        === "Fedora"
            [Docker CE for Fedora](https://docs.docker.com/install/linux/docker-ce/fedora)
        === "CentOS"
            [Docker CE for CentOS](https://docs.docker.com/install/linux/docker-ce/centos)

    1. Add your user to the `docker` group:

        ```bash
        sudo usermod -aG docker $USER
        ```

    1. Sign out and then back in again so your changes take effect.

After installation, restart your terminal one last time.
