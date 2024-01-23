# Setup

-----

This will be relatively painless, we promise!

## Integrations

You will need to clone [integrations-core][] and/or [integrations-extras][] depending on which integrations
you intend to work on.

## Python

To work on any integration you must install Python 3.11.

After installation, restart your terminal and ensure that your newly installed Python comes first in your `PATH`.

=== "macOS"
    First update the formulae and [Homebrew][homebrew-home] itself:

    ```
    brew update
    ```

    then install Python:

    ```
    brew install python@3.11
    ```

    After it completes, check the output to see if it asked you to run any extra commands and if so, execute them.

    Verify successful `PATH` modification:

    ```
    which -a python
    ```

=== "Windows"
    Windows users have it the easiest.

    Download the [Python 3.11 64-bit executable installer](https://www.python.org/downloads/release/python-3115/) and run it.
    When prompted, be sure to select the option to add to your `PATH`. Also, it is recommended that you choose the per-user installation method.

    Verify successful `PATH` modification:

    ```
    where python
    ```

=== "Linux"
    Ah, you enjoy difficult things. Are you using Gentoo?

    We recommend using either [Miniconda][miniconda-docs] or [pyenv][pyenv-github] to install Python 3.11. Whatever you do, never modify the system Python.

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

You have 4 options to install the CLI.

#### Installers

=== "macOS"
    === "GUI installer"
        1. In your browser, download the `.pkg` file: [ddev-<docs-insert-ddev-version>.pkg](https://github.com/DataDog/integrations-core/releases/download/ddev-v<docs-insert-ddev-version>/ddev-<docs-insert-ddev-version>.pkg)
        2. Run your downloaded file and follow the on-screen instructions.
        3. Restart your terminal.
        4. To verify that the shell can find and run the `ddev` command in your `PATH`, use the following command.

            ```
            $ ddev --version
            <docs-insert-ddev-version>
            ```
    === "Command line installer"
        1. Download the file using the `curl` command. The `-o` option specifies the file name that the downloaded package is written to. In this example, the file is written to `ddev-<docs-insert-ddev-version>.pkg` in the current directory.

            ```
            curl -o ddev-<docs-insert-ddev-version>.pkg https://github.com/DataDog/integrations-core/releases/download/ddev-v<docs-insert-ddev-version>/ddev-<docs-insert-ddev-version>.pkg
            ```
        2. Run the standard macOS [`installer`](https://ss64.com/osx/installer.html) program, specifying the downloaded `.pkg` file as the source. Use the `-pkg` parameter to specify the name of the package to install, and the `-target /` parameter for the drive in which to install the package. The files are installed to `/usr/local/ddev`, and an entry is created at `/etc/paths.d/ddev` that instructs shells to add the `/usr/local/ddev` directory to. You must include sudo on the command to grant write permissions to those folders.

            ```
            sudo installer -pkg ./ddev-<docs-insert-ddev-version>.pkg -target /
            ```
        3. Restart your terminal.
        4. To verify that the shell can find and run the `ddev` command in your `PATH`, use the following command.

            ```
            $ ddev --version
            <docs-insert-ddev-version>
            ```

=== "Windows"
    === "GUI installer"
        1. In your browser, download one the `.msi` files:
              - [ddev-<docs-insert-ddev-version>-x64.msi](https://github.com/DataDog/integrations-core/releases/download/ddev-v<docs-insert-ddev-version>/ddev-<docs-insert-ddev-version>-x64.msi)
              - [ddev-<docs-insert-ddev-version>-x86.msi](https://github.com/DataDog/integrations-core/releases/download/ddev-v<docs-insert-ddev-version>/ddev-<docs-insert-ddev-version>-x86.msi)
        2. Run your downloaded file and follow the on-screen instructions.
        3. Restart your terminal.
        4. To verify that the shell can find and run the `ddev` command in your `PATH`, use the following command.

            ```
            $ ddev --version
            <docs-insert-ddev-version>
            ```
    === "Command line installer"
        1. Download and run the installer using the standard Windows [`msiexec`](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/msiexec) program, specifying one of the `.msi` files as the source. Use the `/passive` and `/i` parameters to request an unattended, normal installation.

            === "x64"
                ```
                msiexec /passive /i https://github.com/DataDog/integrations-core/releases/download/ddev-v<docs-insert-ddev-version>/ddev-<docs-insert-ddev-version>-x64.msi
                ```
            === "x86"
                ```
                msiexec /passive /i https://github.com/DataDog/integrations-core/releases/download/ddev-v<docs-insert-ddev-version>/ddev-<docs-insert-ddev-version>-x86.msi
                ```
        2. Restart your terminal.
        3. To verify that the shell can find and run the `ddev` command in your `PATH`, use the following command.

            ```
            $ ddev --version
            <docs-insert-ddev-version>
            ```

#### Standalone binaries

After downloading the archive corresponding to your platform and architecture, extract the binary to a directory that is on your PATH and rename to `ddev`.

=== "macOS"
    - [ddev-<docs-insert-ddev-version>-aarch64-apple-darwin.tar.gz](https://github.com/DataDog/integrations-core/releases/download/ddev-v<docs-insert-ddev-version>/ddev-<docs-insert-ddev-version>-aarch64-apple-darwin.tar.gz)
    - [ddev-<docs-insert-ddev-version>-x86_64-apple-darwin.tar.gz](https://github.com/DataDog/integrations-core/releases/download/ddev-v<docs-insert-ddev-version>/ddev-<docs-insert-ddev-version>-x86_64-apple-darwin.tar.gz)

=== "Windows"
    - [ddev-<docs-insert-ddev-version>-x86_64-pc-windows-msvc.zip](https://github.com/DataDog/integrations-core/releases/download/ddev-v<docs-insert-ddev-version>/ddev-<docs-insert-ddev-version>-x86_64-pc-windows-msvc.zip)
    - [ddev-<docs-insert-ddev-version>-i686-pc-windows-msvc.zip](https://github.com/DataDog/integrations-core/releases/download/ddev-v<docs-insert-ddev-version>/ddev-<docs-insert-ddev-version>-i686-pc-windows-msvc.zip)

=== "Linux"
    - [ddev-<docs-insert-ddev-version>-aarch64-unknown-linux-gnu.tar.gz](https://github.com/DataDog/integrations-core/releases/download/ddev-v<docs-insert-ddev-version>/ddev-<docs-insert-ddev-version>-aarch64-unknown-linux-gnu.tar.gz)
    - [ddev-<docs-insert-ddev-version>-x86_64-unknown-linux-gnu.tar.gz](https://github.com/DataDog/integrations-core/releases/download/ddev-v<docs-insert-ddev-version>/ddev-<docs-insert-ddev-version>-x86_64-unknown-linux-gnu.tar.gz)
    - [ddev-<docs-insert-ddev-version>-x86_64-unknown-linux-musl.tar.gz](https://github.com/DataDog/integrations-core/releases/download/ddev-v<docs-insert-ddev-version>/ddev-<docs-insert-ddev-version>-x86_64-unknown-linux-musl.tar.gz)
    - [ddev-<docs-insert-ddev-version>-i686-unknown-linux-gnu.tar.gz](https://github.com/DataDog/integrations-core/releases/download/ddev-v<docs-insert-ddev-version>/ddev-<docs-insert-ddev-version>-i686-unknown-linux-gnu.tar.gz)
    - [ddev-<docs-insert-ddev-version>-powerpc64le-unknown-linux-gnu.tar.gz](https://github.com/DataDog/integrations-core/releases/download/ddev-v<docs-insert-ddev-version>/ddev-<docs-insert-ddev-version>-powerpc64le-unknown-linux-gnu.tar.gz)

#### PyPI

=== "macOS"
    Remove any executables shown in the output of `which -a ddev` and make sure that there is no active virtual environment, then run:

    === "ARM"
        ```
        pipx install ddev --python /opt/homebrew/bin/python3.11
        ```
    === "Intel"
        ```
        pipx install ddev --python /usr/local/bin/python3.11
        ```

    !!! warning
        Do not use `sudo` as it may result in a broken installation!

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

    !!! warning
        Do not use `sudo` as it may result in a broken installation!

Upgrade at any time by running:

```
pipx upgrade ddev
```

#### Development

This is if you cloned [integrations-core][] and want to always use the version based on the current branch.

=== "macOS"
    Remove any executables shown in the output of `which -a ddev` and make sure that there is no active virtual environment, then run:

    === "ARM"
        ```
        pipx install -e /path/to/integrations-core/ddev --python /opt/homebrew/opt/python@3.11/bin/python3.11
        ```
    === "Intel"
        ```
        pipx install -e /path/to/integrations-core/ddev --python /usr/local/opt/python@3.11/bin/python3.11
        ```

    !!! warning
        Do not use `sudo` as it may result in a broken installation!

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

    !!! warning
        Do not use `sudo` as it may result in a broken installation!

Re-sync dependencies at any time by running:

```
pipx upgrade ddev
```

!!! note
    Be aware that this method does not keep track of dependencies so you will need to re-run the command if/when the required dependencies are changed.

!!! note
    Also be aware that this method does not get any changes from `datadog_checks_dev`, so if you have unreleased changes from `datadog_checks_dev` that may affect `ddev`, you will need to run the following to get the most recent changes from `datadog_checks_dev` to your `ddev`:

    ```
    pipx inject ddev -e "/path/to/datadog_checks_dev"
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
