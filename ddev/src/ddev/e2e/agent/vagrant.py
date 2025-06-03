# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import os
import shlex
import sys
import socket  # For _get_hostname and _find_free_port
import tempfile
from contextlib import AbstractContextManager, contextmanager, nullcontext, closing
from functools import cache, cached_property, partial
from typing import TYPE_CHECKING, Callable, Type

import stamina
import shutil

from ddev.e2e.agent.interface import AgentInterface
from ddev.utils.structures import EnvVars
from ddev.e2e.agent.constants import AgentEnvVars
from ddev.utils.fs import Path


if TYPE_CHECKING:
    import subprocess
    from ddev.platform import Platform


@contextmanager
def disable_integration_before_install(config_file: Path):
    """
    Disable integration by renaming the config to "conf.yaml.example".

    As we exit the context manager we rename it back to "conf.yaml" to re-enable the integration.
    This assumes the config_file is accessible from the host and is part of a synced folder.
    """
    old_name = config_file.name
    new_config_file = config_file.rename(config_file.parent / (config_file.name + ".example"))
    try:
        yield
    finally:
        # Ensure the file is renamed back even if errors occur within the context
        if new_config_file.is_file():  # Check if it was successfully renamed
            new_config_file.rename(config_file.parent / old_name)
        elif not config_file.exists() and (config_file.parent / old_name).exists():
            # If the original was somehow restored or yield failed before new_config_file was used.
            pass  # Already in desired state or original file does not exist to be renamed.


class VagrantAgent(AgentInterface):
    def __init__(
        self,
        platform: Platform,
        integration: Path,
        env: str,
        metadata: dict,
        config_file: Path,
    ):
        super().__init__(platform, integration, env, metadata, config_file)
        # self.platform = platform
        # self.integration = integration
        # self.config_file = config_file
        # self.metadata = metadata

        # Initialize and create the directory for Vagrant files specific to this VM
        home_dir = Path.home()
        self._temp_vagrant_dir = home_dir / ".ddev" / "vagrant" / self._vm_name
        self._temp_vagrant_dir.mkdir(parents=True, exist_ok=True)

        # Generate Vagrantfile if it doesn't exist
        vagrantfile_path = self._temp_vagrant_dir / "Vagrantfile"
        if not vagrantfile_path.exists():
            print(f"Vagrantfile not found at {vagrantfile_path}, generating new one.")
            vagrantfile_content = self._generate_vagrantfile_content()
            vagrantfile_path.write_text(vagrantfile_content)
            print(f"Vagrantfile generated at {vagrantfile_path}")
        else:
            print(f"Using existing Vagrantfile at {vagrantfile_path}")

        # Set VAGRANT_CWD to self.temp_vagrant_dir
        os.environ["VAGRANT_CWD"] = str(self._temp_vagrant_dir)
        print(f"Vagrant working directory set to: {self._temp_vagrant_dir}")

    def _generate_vagrantfile_content(self) -> str:
        vm_hostname = self._vm_name  # Already sanitized and unique
        vagrant_box = self.metadata.get("vagrant_box", "net9/ubuntu-24.04-arm64")  # Default box
        vagrant_sync_type = self.metadata.get("vagrant_sync_type")
        # vb_memory = self.metadata.get("vagrant_vm_memory", "1024")
        # vb_cpus = self.metadata.get("vagrant_vm_cpus", "1")

        # sync_type_option = f', type: "{vagrant_sync_type}"' if vagrant_sync_type else ""  # For synced_folder

        # Config file sync setup
        # self.config_file is the host path to the integration's specific config file, e.g., .../data/conf.yaml
        # self._config_mount_dir is the target directory on the guest, e.g., /etc/datadog-agent/conf.d/my_integration.d
        # host_config_file_abs = str(self.config_file.resolve())
        # host_config_dir_abs = str(self.config_file.parent.resolve())
        # guest_config_target_dir = self._config_mount_dir  # This is already OS-specific via its own definition

        return f"""\
# -*- mode: ruby -*-
# vi: set ft=ruby :

$set_environment_variables = <<SCRIPT
tee "/etc/profile.d/myvars.sh" > "/dev/null" <<EOF

export DD_API_KEY="{os.environ.get("DD_API_KEY")}"
EOF
SCRIPT


Vagrant.configure("2") do |config|
  config.vm.box = "{vagrant_box}"
  config.vm.box_version = "1.1"

  # Default synced folder: the directory containing this Vagrantfile (self._temp_vagrant_dir on host)
  # is synced to /vagrant on Linux guest or C:\\vagrant on Windows guest.
  # This is used for staging local packages for installation.
  # config.vm.synced_folder ".", "/vagrant" # Ensure the temp dir itself is synced to /vagrant

  config.vm.network "private_network", type: "dhcp"

  config.vm.define "{vm_hostname}" do |node|
    node.vm.hostname = "{vm_hostname}"

    node.vm.provision "shell", inline: $set_environment_variables, run: "always"

    node.vm.provision "shell", inline: <<-SHELL, run: "always"
      apt update
      DD_SITE="datadoghq.com" bash -c "$(curl -L https://install.datadoghq.com/scripts/install_script_agent7.sh)"
      service datadog-agent start && echo "Agent started successfully"
      echo "VM #{vm_hostname} is ready"
    SHELL
  end

end
"""

    @cached_property
    def _isatty(self) -> bool:
        isatty: Callable[[], bool] | None = getattr(sys.stdout, "isatty", None)
        if isatty is not None:
            try:
                return isatty()
            except ValueError:  # Raised if sys.stdout is not a tty (e.g. in a pipe)
                pass
        return False

    @cached_property
    def _vm_name(self) -> str:
        # vm name can only conntain letters, numbers, hyphens and dots.
        return f"dd_vagrant_{super().get_id()}".replace("_", "-")

    @cached_property
    def _is_windows_vm(self) -> bool:
        return self.metadata.get("vagrant_guest_os", "linux").lower() == "windows"

    @cached_property
    def _package_mount_dir(self) -> str:
        # Default path INSIDE the VM where host packages are synced/mounted.
        # Assumes a synced folder like `/vagrant` or `C:\vagrant` on the guest.
        base_synced_dir = "C:\\vagrant" if self._is_windows_vm else "/vagrant"
        return os.path.join(base_synced_dir, "packages").replace(
            "\\", "\\\\"
        )  # Ensure correct path sep for os.join and escape for f-strings

    @cached_property
    def _config_mount_dir(self) -> str:
        # Path INSIDE the VM where agent configs are expected.
        name = self.integration.name
        if self._is_windows_vm:
            return f"C:\\ProgramData\\Datadog\\conf.d\\{name}.d"
        else:
            return f"/etc/datadog-agent/conf.d/{name}.d"

    @cached_property
    def _python_path(self) -> str:
        # Path to python executable INSIDE the VM.
        py_major = self.python_version[0]
        if self._is_windows_vm:
            return f"C:\\Program Files\\Datadog\\Datadog Agent\\embedded{py_major}\\python.exe"
        else:
            return f"/opt/datadog-agent/embedded/bin/python{py_major}"

    def _format_command(self, guest_command_parts: list[str], interactive: bool = False) -> list[str]:
        # Returns the host-side command to execute something in the guest.
        if interactive:
            return ["vagrant", "ssh", self._vm_name]

        # Prepare the command string to be executed inside the VM via ssh -c "..."
        inner_cmd_list = []
        if guest_command_parts[0].lower() == "pip":  # Check for pip command
            inner_cmd_list.extend([self._python_path, "-m", "pip"])
            inner_cmd_list.extend(guest_command_parts[1:])
        else:
            inner_cmd_list.extend(guest_command_parts)

        # Handle sudo for non-Windows guests if metadata suggests it's needed for the command.
        # This is a basic approach. More complex sudo needs might require specific command metadata.
        if not self._is_windows_vm and self.metadata.get("vagrant_command_needs_sudo", True):
            if not inner_cmd_list or inner_cmd_list[0] != "sudo":
                inner_cmd_list.insert(0, "sudo")

        inner_cmd_str = " ".join(shlex.quote(part) for part in inner_cmd_list)
        host_command = ["vagrant", "ssh", self._vm_name, "-c", inner_cmd_str]
        return host_command

    def _captured_process(self, host_command: list[str], **kwargs) -> subprocess.CompletedProcess:
        kwargs.setdefault("check", False)  # Caller should handle errors based on returncode

        return self.platform.run_command(
            host_command,
            stdout=self.platform.modules.subprocess.PIPE,
            stderr=self.platform.modules.subprocess.PIPE,
            **kwargs,
        )

    def _run_command(self, host_command: list[str], **kwargs) -> subprocess.CompletedProcess:
        # `check=True` by default if not specified by caller.
        kwargs.setdefault("check", True)
        kwargs.setdefault("env", os.environ)

        return self.platform.run_command(host_command, **kwargs)

    def _show_logs(self) -> None:
        print(f"Attempting to fetch agent logs from VM: {self._vm_name}...")
        log_file_path_guest = (
            "C:\\ProgramData\\Datadog\\logs\\agent.log" if self._is_windows_vm else "/var/log/datadog/agent.log"
        )

        guest_cmd_parts = ["type" if self._is_windows_vm else "cat", log_file_path_guest]

        # Reading agent logs on Linux might require sudo.
        if not self._is_windows_vm and self.metadata.get("vagrant_logs_require_sudo", True):
            if guest_cmd_parts[0] != "sudo":  # Avoid double sudo if 'cat' was replaced by 'sudo cat'
                guest_cmd_parts.insert(0, "sudo")

        host_cmd_to_fetch_logs = self._format_command(guest_cmd_parts)

        process = self._captured_process(host_cmd_to_fetch_logs)
        stdout = process.stdout.decode("utf-8", errors="replace").strip() if process.stdout else ""
        stderr = process.stderr.decode("utf-8", errors="replace").strip() if process.stderr else ""

        if process.returncode == 0 and stdout:
            print(f"Agent logs from VM ({self._vm_name}):\n{stdout}")
        elif process.returncode == 0 and not stdout:
            print(f"Successfully fetched agent logs from VM ({self._vm_name}), but logs are empty.")
        else:
            raise Exception(
                f"Failed to fetch agent logs from VM ({self._vm_name}). RC: {process.returncode}\n"
                f"Stdout:\n{stdout}\n"
                f"Stderr:\n{stderr}"
            )

    def get_id(self) -> str:
        return self._vm_name

    def start(self, *, agent_build: str, local_packages: dict[Path, str], env_vars: dict[str, str]) -> None:
        # `agent_build` is part of the interface but less directly used for Vagrant
        # as the VM's "build" (box image) is typically defined in the Vagrantfile.
        # It could be used to select a Vagrant box if multiple are defined and match a pattern.
        print(f"Starting Vagrant environment for VM: {self._vm_name}.")

        # Stage local packages into a `packages` directory in the Current Working Directory.
        # Assumes the Vagrantfile being used will sync this directory.
        if local_packages:
            packages_dir_host = Path.cwd() / "packages"
            packages_dir_host.mkdir(parents=True, exist_ok=True)
            print(f"Staging local packages into: {packages_dir_host}")
            for package_path_on_host, _features in local_packages.items():
                target_on_host = packages_dir_host / package_path_on_host.name
                if package_path_on_host.is_dir():
                    if target_on_host.exists():
                        shutil.rmtree(target_on_host)  # shutil imported at top level by user
                    shutil.copytree(package_path_on_host, target_on_host, dirs_exist_ok=True)
                elif package_path_on_host.is_file():  # e.g., a wheel file
                    shutil.copy2(package_path_on_host, target_on_host)
                print(f"Staged local package {package_path_on_host.name} to {target_on_host}")

        # Host environment variables for `vagrant up` command itself
        host_operation_env_vars = EnvVars(os.environ)
        host_operation_env_vars.update(env_vars)  # User-provided can override system for the vagrant command

        # Prepare environment variables intended for the Agent process inside the VM.
        # These are primarily for reference or if custom start_commands need them.
        # Agent installation & primary config are now assumed to be in the Vagrantfile.
        agent_process_env = {}
        if AgentEnvVars.API_KEY not in env_vars:
            agent_process_env[AgentEnvVars.API_KEY] = "a" * 32
        agent_process_env[AgentEnvVars.HOSTNAME] = self.metadata.get("dd_hostname", _get_hostname())
        agent_process_env[AgentEnvVars.CMD_PORT] = str(self.metadata.get("dd_cmd_port", _find_free_port()))
        agent_process_env[AgentEnvVars.APM_ENABLED] = self.metadata.get("dd_apm_enabled", "false")
        agent_process_env[AgentEnvVars.TELEMETRY_ENABLED] = self.metadata.get("dd_telemetry_enabled", "true")
        agent_process_env[AgentEnvVars.EXPVAR_PORT] = self.metadata.get("dd_expvar_port", "5000")
        if (proxy_data := self.metadata.get("proxy")) is not None:
            if (http_proxy := proxy_data.get("http")) is not None:
                agent_process_env[AgentEnvVars.PROXY_HTTP] = http_proxy
            if (https_proxy := proxy_data.get("https")) is not None:
                agent_process_env[AgentEnvVars.PROXY_HTTPS] = https_proxy
        self.metadata["resolved_agent_process_env"] = agent_process_env  # Keep for reference

        config_management_context: Type[AbstractContextManager] | Callable[[], AbstractContextManager] = nullcontext
        if self.config_file.is_file() and local_packages:
            print(f"Local packages to install; temporarily disabling integration config: {self.config_file}")
            config_management_context = partial(disable_integration_before_install, self.config_file)

        up_command_host = ["vagrant", "up", self._vm_name]
        if self.metadata.get("vagrant_provision", True):
            up_command_host.append("--provision")

        # Agent installation script via Python is removed. Assumed to be in Vagrantfile provisioning.
        # Custom start_commands from metadata are still run.
        start_commands = []
        if custom_start_cmds := self.metadata.get("start_commands"):
            if isinstance(custom_start_cmds, list):
                start_commands.extend(custom_start_cmds)
            else:
                start_commands.append(str(custom_start_cmds))

        post_install_guest_commands = self.metadata.get("post_install_commands", [])

        with config_management_context():
            self._initialize(
                up_command_host,
                local_packages,
                start_commands,
                post_install_guest_commands,
                host_operation_env_vars,
            )

        if local_packages or start_commands or post_install_guest_commands:
            print("Local packages installed or custom start/post-install commands run. Restarting agent service.")
            self.restart_agent_service()
        else:
            print("No local packages or custom start/post-install commands. Agent service restart skipped.")

    def _initialize(
        self,
        up_command_host: list[str],
        local_packages: dict[Path, str],
        start_guest_commands: list[str],  # Renamed from start_commands for clarity here
        post_install_guest_commands: list[str],
        host_operation_env_vars: EnvVars,
    ):
        print(
            f"Bringing up Vagrant VM: {self._vm_name} from {self._temp_vagrant_dir} with command: {' '.join(up_command_host)}"
        )
        # _captured_process will now automatically use self._temp_vagrant_dir as cwd for vagrant commands
        process = self._captured_process(up_command_host, env=host_operation_env_vars)
        stdout = process.stdout.decode("utf-8", errors="replace") if process.stdout else ""
        stderr = process.stderr.decode("utf-8", errors="replace") if process.stderr else ""
        if process.returncode:
            raise RuntimeError(
                f"Failed to start Vagrant VM `{self._vm_name}` (RC: {process.returncode}).\n"
                f"Stdout:\n{stdout}\nStderr:\n{stderr}"
            )
        print(f"Vagrant VM `{self._vm_name}` started successfully.\n{stdout}")

        # Execute start_commands (guest commands)
        if start_guest_commands:
            print(f"Running start-up commands in VM `{self._vm_name}`...")
            for guest_cmd_str in start_guest_commands:
                cmd_parts_guest = self.platform.modules.shlex.split(guest_cmd_str)
                formatted_host_cmd = self._format_command(cmd_parts_guest)
                process = self._captured_process(formatted_host_cmd)
                stdout = process.stdout.decode("utf-8", errors="replace") if process.stdout else ""
                stderr = process.stderr.decode("utf-8", errors="replace") if process.stderr else ""
                if process.returncode:
                    self._show_logs()
                    raise RuntimeError(
                        f"Failed to run start-up command `{' '.join(cmd_parts_guest)}` in VM `{self._vm_name}` (RC: {process.returncode}).\n"
                        f"Stdout:\n{stdout}\nStderr:\n{stderr}"
                    )
                print(f"Successfully ran start-up command `{' '.join(cmd_parts_guest)}`.\n{stdout}")

        # Install local packages
        if local_packages:
            print(f"Installing local packages in VM `{self._vm_name}`...")
            pip_base_cmd_guest = ["pip", "install", "--disable-pip-version-check", "-e"]
            for host_package_path, features in local_packages.items():
                package_name_on_host = host_package_path.name
                # Assumes the package dir itself is synced under self._package_mount_dir
                package_path_in_guest = (
                    f"{self._package_mount_dir.rstrip('/')}/{package_name_on_host}"  # Construct path carefully
                )
                package_spec_in_guest = (
                    f"{package_path_in_guest}{features}"  # e.g., /vagrant/packages/my_check[feature]
                )

                full_pip_cmd_guest = pip_base_cmd_guest + [package_spec_in_guest]
                formatted_host_cmd = self._format_command(full_pip_cmd_guest)

                print(f"Installing {package_spec_in_guest} using: {' '.join(formatted_host_cmd)}")
                process = self._captured_process(formatted_host_cmd)
                stdout = process.stdout.decode("utf-8", errors="replace") if process.stdout else ""
                stderr = process.stderr.decode("utf-8", errors="replace") if process.stderr else ""
                if process.returncode:
                    self._show_logs()
                    raise RuntimeError(
                        f"Unable to install package `{package_spec_in_guest}` in VM `{self._vm_name}` (RC: {process.returncode}).\n"
                        f"Stdout:\n{stdout}\nStderr:\n{stderr}"
                    )
                print(f"Successfully installed {package_spec_in_guest}.\n{stdout}")

        # Execute post_install_commands (guest commands)
        if post_install_guest_commands:
            print(f"Running post-install commands in VM `{self._vm_name}`...")
            for guest_cmd_str in post_install_guest_commands:
                cmd_parts_guest = self.platform.modules.shlex.split(guest_cmd_str)
                formatted_host_cmd = self._format_command(cmd_parts_guest)
                process = self._captured_process(formatted_host_cmd)
                stdout = process.stdout.decode("utf-8", errors="replace") if process.stdout else ""
                stderr = process.stderr.decode("utf-8", errors="replace") if process.stderr else ""
                if process.returncode:
                    self._show_logs()
                    raise RuntimeError(
                        f"Failed to run post-install command `{' '.join(cmd_parts_guest)}` in VM `{self._vm_name}` (RC: {process.returncode}).\n"
                        f"Stdout:\n{stdout}\nStderr:\n{stderr}"
                    )
                print(f"Successfully ran post-install command `{' '.join(cmd_parts_guest)}`.\n{stdout}")

    def stop(self) -> None:
        print(f"Stopping Vagrant VM: {self._vm_name}...")
        stop_guest_commands = self.metadata.get("stop_commands", [])
        if stop_guest_commands:
            print(f"Running stop commands in VM `{self._vm_name}`...")
            for guest_cmd_str in stop_guest_commands:
                cmd_parts_guest = self.platform.modules.shlex.split(guest_cmd_str)
                formatted_host_cmd = self._format_command(cmd_parts_guest)
                process = self._captured_process(formatted_host_cmd)  # Don't check=True, try to proceed
                if process.returncode:
                    print(
                        f"A stop command `{' '.join(cmd_parts_guest)}` failed (RC: {process.returncode}) "
                        f"but attempting to continue stopping VM."
                    )

        # Halt the VM
        halt_cmd_host = ["vagrant", "halt", self._vm_name]
        print(f"Halting VM: {self._vm_name} with command: {' '.join(halt_cmd_host)}")
        process_halt = self._captured_process(halt_cmd_host)  # cwd is no longer set by _captured_process
        if process_halt.returncode:
            print(  # Don't raise, still attempt destroy
                f"Failed to halt Vagrant VM `{self._vm_name}` (RC: {process_halt.returncode}). "
                f"Stderr: {process_halt.stderr.decode('utf-8', errors='replace') if process_halt.stderr else 'N/A'}"
            )
        else:
            print(f"VM {self._vm_name} halted.")

        # Destroy the VM
        destroy_cmd_host = ["vagrant", "destroy", self._vm_name, "--force"]
        print(f"Destroying VM: {self._vm_name} with command: {' '.join(destroy_cmd_host)}")
        process_destroy = self._captured_process(destroy_cmd_host)  # cwd is no longer set by _captured_process
        if process_destroy.returncode:
            # This is more critical
            raise RuntimeError(
                f"Failed to destroy Vagrant VM `{self._vm_name}` (RC: {process_destroy.returncode}).\n"
                f"Stdout: {process_destroy.stdout.decode('utf-8', errors='replace') if process_destroy.stdout else 'N/A'}\n"
                f"Stderr: {process_destroy.stderr.decode('utf-8', errors='replace') if process_destroy.stderr else 'N/A'}"
            )
        print(f"VM {self._vm_name} destroyed.")

    def restart(self) -> None:
        # Restarts the entire VM
        print(f"Restarting (reloading) Vagrant VM: {self._vm_name}...")
        reload_cmd_host = ["vagrant", "reload", self._vm_name]
        if self.metadata.get("vagrant_provision_on_reload", True):  # Default to reprovisioning on reload
            reload_cmd_host.append("--provision")

        process = self._captured_process(reload_cmd_host)
        stdout = process.stdout.decode("utf-8", errors="replace") if process.stdout else ""
        stderr = process.stderr.decode("utf-8", errors="replace") if process.stderr else ""
        if process.returncode:
            raise RuntimeError(
                f"Failed to restart (reload) Vagrant VM `{self._vm_name}` (RC: {process.returncode}).\n"
                f"Stdout:\n{stdout}\nStderr:\n{stderr}"
            )
        print(f"Vagrant VM `{self._vm_name}` restarted successfully.\n{stdout}")
        # After a full VM reload, agent service should be managed by guest OS init system.
        # If specific post-reload steps are needed, they might go here or be part of provisioning.

    def restart_agent_service(self) -> None:
        # Restarts the Datadog Agent service *inside* the VM
        print(f"Restarting Datadog Agent service in VM: {self._vm_name}...")
        if self._is_windows_vm:
            # Example for Windows: restart using sc. Ensure agent service name is correct.
            agent_service_name = self.metadata.get("vagrant_windows_agent_service_name", "DatadogAgent")
            # Stop and then start, as 'restart' is not always available/reliable with sc for all services
            guest_cmds = [["sc", "stop", agent_service_name], ["sc", "start", agent_service_name]]
        else:
            # Example for Linux: systemd. Allow override via metadata.
            restart_cmd_str = self.metadata.get(
                "vagrant_linux_agent_restart_command", "sudo systemctl restart datadog-agent.service"
            )
            guest_cmds = [self.platform.modules.shlex.split(restart_cmd_str)]

        for guest_cmd_parts in guest_cmds:
            host_cmd = self._format_command(guest_cmd_parts)
            print(f"Executing agent service command in guest: {' '.join(guest_cmd_parts)}")
            process = self._captured_process(host_cmd)
            stdout = process.stdout.decode("utf-8", errors="replace") if process.stdout else ""
            stderr = process.stderr.decode("utf-8", errors="replace") if process.stderr else ""
            if process.returncode:
                self._show_logs()  # Show agent logs for diagnostics
                raise RuntimeError(
                    f"Failed to run agent service command `{' '.join(guest_cmd_parts)}` in VM `{self._vm_name}` (RC: {process.returncode}).\n"
                    f"Stdout:\n{stdout}\nStderr:\n{stderr}"
                )
            print(f"Agent service command `{' '.join(guest_cmd_parts)}` executed successfully.\n{stdout}")
        print("Datadog Agent service restart sequence completed.")

    def invoke(self, args: list[str]) -> None:
        # Runs an 'agent <command>' inside the VM
        agent_bin = self.metadata.get("vagrant_agent_binary_path", "/opt/datadog-agent/bin/agent/agent")
        if self._is_windows_vm:
            agent_bin = self.metadata.get(
                "vagrant_windows_agent_binary_path", "C:\\Program Files\\Datadog\\Datadog Agent\\bin\\agent.exe"
            )

        guest_cmd_parts = [agent_bin] + args
        host_cmd = self._format_command(guest_cmd_parts)

        print(f"Invoking agent command in VM `{self._vm_name}`: {' '.join(host_cmd)}")
        # Using _run_command directly to stream output and check=True by default
        self._run_command(host_cmd)

    def enter_shell(self) -> None:
        print(f"Entering interactive shell for VM: {self._vm_name}...")
        # _format_command with interactive=True gives ['vagrant', 'ssh', self._vm_name]
        host_cmd = self._format_command([], interactive=True)
        # For interactive shells, check=True might exit if shell exits non-zero,
        # but usually, it's what's desired.
        self._run_command(host_cmd, check=True)


@cache
def _get_hostname():
    try:
        return socket.gethostname().lower()
    except Exception:
        return "unknown-vagrant-host"


@cache
def _find_free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("", 0))  # Bind to an ephemeral port on all interfaces
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]  # Return the port number assigned
