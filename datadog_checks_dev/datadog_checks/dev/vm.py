# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import platform
import time
from contextlib import contextmanager
from typing import Iterator  # noqa: F401
import subprocess
import re
import sys

from .conditions import CheckVMLogs
from .env import environment_run, get_state, save_state
from .structures import EnvVars, LazyFunction
from .subprocess import run_command
from .utils import find_check_root, running_on_ci

ON_CI = running_on_ci()

try:
    from contextlib import ExitStack
except ImportError:
    from contextlib2 import ExitStack


def get_vm_hostname(vm_name):
    """
    Get a VM's hostname.
    """
    # For arm64 macOS, the VM hostname is typically set in the VM itself
    return vm_name


def get_vm_ip(vm_name):
    """
    Get a VM's IP address from its name.
    """
    # First try using Vagrant to get the IP
    vagrant_dir = _find_vagrant_dir(vm_name)
    if vagrant_dir:
        # Change to the Vagrant directory
        original_dir = os.getcwd()
        try:
            os.chdir(vagrant_dir)

            # Get IP using Vagrant SSH
            cmd = ["vagrant", "ssh", vm_name, "-c", "hostname -I | cut -d' ' -f2"]
            result = run_command(cmd, capture="out", check=False)
            if result.code == 0 and result.stdout.strip():
                ip = result.stdout.strip()
                if ip:
                    return ip
        except Exception as e:
            print(f"Error getting VM IP via Vagrant: {e}")
        finally:
            os.chdir(original_dir)

    # Fall back to trying VMware Fusion if available
    try:
        cmd = ["vmrun", "getGuestIPAddress", vm_name]
        result = run_command(cmd, capture="out", check=False)
        if result.code == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass

    # Fall back to localhost if we can't determine the IP
    return "127.0.0.1"


def _find_vagrant_dir(vm_identifier):
    """Find the directory containing the Vagrantfile for a VM"""
    if os.path.exists(vm_identifier):
        if os.path.isfile(vm_identifier):
            return os.path.dirname(os.path.abspath(vm_identifier))
        return os.path.abspath(vm_identifier)
    return None


def vm_is_running(vm_name):
    """
    Returns a `bool` indicating whether or not a VM is running.
    """
    # Check if it's a Vagrant VM
    vagrant_dir = _find_vagrant_dir(vm_name)
    if vagrant_dir:
        # Change to the Vagrant directory
        original_dir = os.getcwd()
        try:
            os.chdir(vagrant_dir)

            # Check if VM is running using Vagrant
            status_cmd = ["vagrant", "status", vm_name]
            status = run_command(status_cmd, capture="out", check=False).stdout

            return "running" in status
        except Exception:
            pass
        finally:
            os.chdir(original_dir)

    # Also check using VMware if available
    try:
        list_cmd = ["vmrun", "list"]
        running_vms = run_command(list_cmd, capture="out", check=False).stdout

        return vm_name in running_vms
    except Exception:
        pass

    return False


@contextmanager
def vm_run(
    vm_name=None,
    vm_definition=None,
    up=None,
    down=None,
    on_error=None,
    sleep=None,
    endpoints=None,
    log_patterns=None,
    conditions=None,
    env_vars=None,
    wrappers=None,
    attempts=None,
    attempts_wait=5,
    capture=None,
    primary_vm=None,
):
    """
    A convenient context manager for safely setting up and tearing down VM environments.

    Parameters:
        vm_name (str):
            The name of the VM to run
        vm_definition (str):
            A path to a VM definition file (e.g., Vagrantfile)
        up (callable):
            A custom setup callable
        down (callable):
            A custom tear down callable. This is required when using a custom setup.
        on_error (callable):
            A callable called in case of an unhandled exception
        sleep (float):
            Number of seconds to wait before yielding. This occurs after all conditions are successful.
        endpoints (list[str]):
            Endpoints to verify access for before yielding
        log_patterns (list[str | re.Pattern]):
            Regular expression patterns to find in VM logs before yielding
        conditions (callable):
            A list of callable objects that will be executed before yielding to check for errors
        env_vars (dict[str, str]):
            A dictionary to update `os.environ` with during execution
        wrappers (list[callable]):
            A list of context managers to use during execution
        attempts (int):
            Number of attempts to run `up` and the `conditions` successfully. Defaults to 2 in CI
        attempts_wait (int):
            Time to wait between attempts
        primary_vm (str):
            For multi-VM Vagrant environments, specify the primary VM name to use for operations
    """
    if vm_name and up:
        raise TypeError("You must select either a VM name or a custom setup callable, not both.")

    if vm_name is not None:
        set_up = VMUp(vm_name=vm_name)
        if down is not None:
            tear_down = down
        else:
            tear_down = VMDown(vm_name=vm_name)
        if on_error is None:
            on_error = VMLogs(vm_name=vm_name)
    elif vm_definition is not None:
        set_up = VagrantUp(vm_definition=vm_definition, vm_name=primary_vm)
        if down is not None:
            tear_down = down
        else:
            tear_down = VagrantDown(vm_definition=vm_definition)
        if on_error is None:
            # Use the primary_vm if provided for log access
            on_error = VagrantLogs(vm_definition=vm_definition, vm_name=primary_vm or "gluster-node-1")
    else:
        set_up = up
        tear_down = down

    vm_conditions = []

    if log_patterns is not None:
        if vm_name is None and vm_definition is None:
            raise ValueError(
                "The `log_patterns` convenience is unavailable when using "
                "a custom setup. Please use a custom condition instead."
            )
        # Pass the primary_vm for Vagrant environments
        if vm_definition is not None:
            vm_conditions.append(CheckVMLogs(vm_definition, log_patterns, vm_name=primary_vm or "gluster-node-1"))
        else:
            vm_conditions.append(CheckVMLogs(vm_name, log_patterns))

    if conditions is not None:
        vm_conditions.extend(conditions)

    wrappers = list(wrappers) if wrappers is not None else []

    with environment_run(
        up=set_up,
        down=tear_down,
        on_error=on_error,
        sleep=sleep,
        endpoints=endpoints,
        conditions=vm_conditions,
        env_vars=env_vars,
        wrappers=wrappers,
        attempts=attempts,
        attempts_wait=attempts_wait,
    ) as result:
        yield result


class VMUp(LazyFunction):
    def __init__(self, vm_name, snapshot=None, capture=None):
        self.vm_name = vm_name
        self.snapshot = snapshot
        self.capture = capture

        # Command to start VM using VMware Fusion (common on Apple Silicon)
        self.command = ["vmrun", "start", self.vm_name]

        # If headless mode is needed
        if ON_CI:
            self.command.extend(["nogui"])

    def __call__(self):
        args = {"check": False}
        if self.capture is not None:
            args["capture"] = self.capture

        # Try to start the VM
        print(f"Starting VM: {self.vm_name}")
        result = run_command(self.command, **args)

        # VMware vmrun command failed, try using VirtualBox or UTM command line
        if result.code != 0:
            # Try using UTM command line if available
            try:
                utm_cmd = ["open", "-a", "UTM", "--args", "start", self.vm_name]
                print(f"Trying to start with UTM: {utm_cmd}")
                result = run_command(utm_cmd, check=False)
            except Exception as e:
                print(f"Error starting VM with UTM: {e}")

        # Wait for VM to fully boot
        print(f"Waiting for VM to boot...")
        time.sleep(15)

        return result


class VMLogs(LazyFunction):
    def __init__(self, vm_name, check=True):
        self.vm_name = vm_name
        self.check = check

        # On arm64 macOS, just attempt to get basic VM info
        self.command = ["vmrun", "getGuestIPAddress", self.vm_name]

    def __call__(self, exception):
        try:
            result = run_command(self.command, capture=True, check=False)
            print(f"VM diagnostics for {self.vm_name}:")
            print(f"IP Address: {result.stdout if result.code == 0 else 'Unknown'}")
            print(f"Exception: {exception}")
            return result
        except Exception as e:
            print(f"Error getting VM logs: {e}")
            return None


class VMDown(LazyFunction):
    def __init__(self, vm_name, check=True):
        self.vm_name = vm_name
        self.check = check

        # Use VMware vmrun command to gracefully power off VM
        self.command = ["vmrun", "stop", self.vm_name]

    def __call__(self):
        print(f"Stopping VM: {self.vm_name}")
        result = run_command(self.command, check=False)

        # If VMware vmrun command failed, try using VirtualBox or UTM
        if result.code != 0:
            try:
                # Try using UTM command line if available
                utm_cmd = ["open", "-a", "UTM", "--args", "stop", self.vm_name]
                run_command(utm_cmd, check=False)
            except Exception:
                pass

        # Wait for VM to fully shut down
        time.sleep(5)

        return result


class VagrantUp(LazyFunction):
    def __init__(self, vm_definition, capture=None, vm_name=None):
        self.vm_definition = vm_definition
        self.capture = capture
        self.vm_name = vm_name or "default"  # Default for single VM setups
        self.command = ["vagrant", "up"]

        # For multi-VM setups, specify which VM to start if provided
        if vm_name:
            self.command.append(vm_name)

        # Change to directory containing Vagrantfile
        self.cwd = os.path.dirname(os.path.abspath(self.vm_definition))

    def __call__(self):
        args = {"check": False}
        if self.capture is not None:
            args["capture"] = self.capture

        # Need to change directory before running command
        original_dir = os.getcwd()
        os.chdir(self.cwd)

        try:
            # Get the status of any existing VMs
            status_cmd = ["vagrant", "status"]
            status_result = run_command(status_cmd, capture="out", check=False)

            # If there's an issue with the status, try to fix common problems
            if "You no longer have the software required to run this VM" in status_result.stdout:
                print("Detected VMware plugin issue. Attempting to re-install plugin...")
                run_command(["vagrant", "plugin", "install", "vagrant-vmware-desktop"], check=False)

            # Try to start the VMs with retries
            max_retries = 2
            retry_count = 0

            while retry_count <= max_retries:
                print(f"Starting Vagrant VM (attempt {retry_count+1}/{max_retries+1})...")

                result = run_command(self.command, **args)

                # Check if the command succeeded
                if result.code == 0:
                    # Verify VMs are actually running
                    status_result = run_command(status_cmd, capture="out", check=False)

                    # Check if the VM is actually running
                    if "running" in status_result.stdout:
                        break
                else:
                    # Check for specific error messages and provide guidance
                    if "The box 'bento/ubuntu-20.04-arm64' could not be found" in result.stderr:
                        print("Box not found. Attempting to add box...")
                        run_command(["vagrant", "box", "add", "bento/ubuntu-20.04-arm64"], check=False)

                    if "Timed out while waiting for the machine to boot" in result.stderr:
                        print("VM boot timeout. This is common on first boot. Retrying...")

                retry_count += 1
                if retry_count <= max_retries:
                    time.sleep(10)  # Longer wait between retries for arm64

            # Wait extra time for VMs to be fully booted
            if result.code == 0:
                print("Waiting for VMs to fully boot...")
                time.sleep(20)  # Longer wait for arm64 VMs

            return result
        finally:
            os.chdir(original_dir)


class VagrantLogs(LazyFunction):
    def __init__(self, vm_definition, check=True, vm_name=None):
        self.vm_definition = vm_definition
        self.check = check
        self.vm_name = vm_name or "default"  # Default to "default" or first VM if not specified

        # Change to directory containing Vagrantfile
        self.cwd = os.path.dirname(os.path.abspath(self.vm_definition))

        # Specify the VM name when multiple VMs are configured
        self.command = ["vagrant", "ssh", self.vm_name, "-c", "cat /var/log/syslog | tail -n 100"]

    def __call__(self, exception):
        # Need to change directory before running command
        original_dir = os.getcwd()
        os.chdir(self.cwd)
        try:
            print(f"Getting logs for VM {self.vm_name}...")

            # Also display Vagrant status for debugging
            status_cmd = ["vagrant", "status"]
            run_command(status_cmd, capture=False, check=False)

            return run_command(self.command, capture=False, check=self.check)
        except Exception as e:
            print(f"Error getting Vagrant logs: {e}")
            return None
        finally:
            os.chdir(original_dir)


class VagrantDown(LazyFunction):
    def __init__(self, vm_definition, check=True):
        self.vm_definition = vm_definition
        self.check = check
        self.command = ["vagrant", "destroy", "-f"]

        # Change to directory containing Vagrantfile
        self.cwd = os.path.dirname(os.path.abspath(self.vm_definition))

    def __call__(self):
        # Need to change directory before running command
        original_dir = os.getcwd()
        os.chdir(self.cwd)
        try:
            print("Destroying Vagrant VMs...")
            return run_command(self.command, check=self.check)
        finally:
            os.chdir(original_dir)


@contextmanager
def temporarily_pause_vm(vm_name, check=True):
    # type: (str, bool) -> Iterator[None]
    """
    Temporarily pause a VM and resume it afterward.
    """
    # For arm64 macOS, try VMware Fusion first
    pause_command = ["vmrun", "pause", vm_name]
    resume_command = ["vmrun", "unpause", vm_name]

    run_command(pause_command, capture=False, check=False)
    yield
    run_command(resume_command, capture=False, check=False)
