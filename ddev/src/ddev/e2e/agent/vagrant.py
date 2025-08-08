# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import os
import re
import shlex
import shutil
import sys
from contextlib import AbstractContextManager, contextmanager, nullcontext
from functools import cached_property, partial
from typing import TYPE_CHECKING, Any, Callable, Type

from jinja2 import Template

from ddev.e2e.agent.constants import (
    LINUX_AGENT_BIN_PATH,
    LINUX_AGENT_CONF_DIR,
    LINUX_AGENT_PYTHON_PREFIX,
    LINUX_SUDOERS_FILE_PATH,
    WINDOWS_AGENT_BIN_PATH,
    WINDOWS_AGENT_CONF_DIR,
    WINDOWS_AGENT_PYTHON_PREFIX,
    AgentEnvVars,
)
from ddev.e2e.agent.interface import AgentInterface
from ddev.e2e.config import EnvDataStorage
from ddev.utils.fs import Path
from ddev.utils.structures import EnvVars

if TYPE_CHECKING:
    from ddev.cli.application import Application
    from ddev.integration.core import Integration
    from ddev.utils.fs import Path


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
    VM_HOST_IP = "172.30.1.5"

    def __init__(
        self, app: Application, integration: Integration, env: str, metadata: dict[str, Any], config_file: Path
    ) -> None:
        metadata = self._substitute_template_variables(metadata)
        super().__init__(app, integration, env, metadata, config_file)
        self.env_data = EnvDataStorage(app.data_dir).get(integration.name, env)
        self._initialize_vagrant(write=False)

    def start(self, *, agent_build: str, local_packages: dict[Path, str], env_vars: dict[str, str]) -> None:
        # Generate the Vagrantfile content
        self._initialize_vagrant(
            write=True,
            exported_env_vars=self._prepare_exported_env_vars(env_vars),
            agent_install_env_vars=self._prepare_agent_install_env_vars(agent_build),
            synced_folders=self._prepare_synced_folders(local_packages),
        )

        # Initialize the VM, run custom commands, and handle restart if necessary
        self._initialize_vm_with_commands(agent_build, local_packages, self._prepare_host_env_vars(env_vars))

    def stop(self) -> None:
        self.app.display_info(f"Stopping Vagrant VM `{self._vm_name}`")
        stop_guest_commands = self.metadata.get("stop_commands", [])
        if stop_guest_commands:
            self._run_commands(stop_guest_commands, "stop")

        # Halt the VM
        self.app.display_info(f"Halting VM `{self._vm_name}`")
        self._run_command(f"vagrant halt {self._vm_name}", "halt_command", host=True)
        self.app.display_info(f"VM `{self._vm_name}` halted")

        # Destroy the VM
        self.app.display_info(f"Destroying VM `{self._vm_name}`")
        self._run_command(f"vagrant destroy {self._vm_name} --force", "destroy_command", host=True)
        self.app.display_info(f"VM `{self._vm_name}` destroyed.")

        # delete the vagrant dir
        shutil.rmtree(self._vagrant_dir)
        self.app.display_info(f"Vagrant working directory deleted: {self._vagrant_dir}")

    def enter_shell(self) -> None:
        self.app.display_info(f"Entering interactive shell for VM `{self._vm_name}`")
        host_cmd = ["vagrant", "ssh", self._vm_name]
        self.app.display_debug(f"Interactive shell command: `{' '.join(host_cmd)}`")
        self.platform.modules.subprocess.run(host_cmd, check=True)

    def restart(self) -> None:
        self.app.display_info(f"Restarting Datadog Agent service in VM `{self._vm_name}`")
        if self._is_windows_vm:
            agent_service_name = self.metadata.get("vagrant_windows_agent_service_name", "DatadogAgent")
            guest_cmds = [f"sc stop {agent_service_name}", f"sc start {agent_service_name}"]
        else:
            guest_cmds = ["sudo service datadog-agent restart"]

        self._run_commands(guest_cmds, "restart_agent_service")
        self.app.display_info("Datadog Agent service restart sequence completed.")

    def invoke(self, args: list[str]) -> None:
        agent_bin = LINUX_AGENT_BIN_PATH if not self._is_windows_vm else WINDOWS_AGENT_BIN_PATH
        guest_cmd_parts = ["sudo", agent_bin] + args if not self._is_windows_vm else [agent_bin] + args
        host_cmd = self._format_command(guest_cmd_parts)

        self.app.display_info(f"Invoking agent command in VM `{self._vm_name}`: {' '.join(host_cmd)}")
        process = self.platform.run_command(
            host_cmd,
        )
        stdout = process.stdout.decode("utf-8", errors="replace") if process.stdout else ""
        stderr = process.stderr.decode("utf-8", errors="replace") if process.stderr else ""
        if stdout:
            self.app.display_info(stdout)
        if stderr:
            self.app.display_error(stderr)

    def _initialize_vagrant(self, write: bool = False, **kwargs):
        self._vagrant_dir = self.env_data.storage_dir / "vagrant" / self._vm_name
        self._vagrant_dir.mkdir(parents=True, exist_ok=True)

        vagrantfile_path = self._vagrant_dir / "Vagrantfile"

        os.environ["VAGRANT_CWD"] = str(self._vagrant_dir)
        self.app.display_debug(f"Vagrant working directory set to: {self._vagrant_dir}")

        if write:
            vagrantfile_content = self._generate_vagrantfile_content(**kwargs)
            vagrantfile_path.write_text(vagrantfile_content)
            self.app.display_info(f"Vagrantfile generated at {vagrantfile_path}")
        else:
            if vagrantfile_path.exists():
                self.app.display_info(f"Using existing Vagrantfile at {vagrantfile_path}")

    def _get_vagrantfile_template(self) -> Template:
        template_path = Path(__file__).parent / "Vagrantfile.template"
        if not template_path.is_file():
            raise FileNotFoundError(f"Vagrantfile template not found at {template_path}")
        return Template(template_path.read_text())

    def _generate_vagrantfile_content(self, **kwargs) -> str:
        agent_install_env_vars = kwargs.get("agent_install_env_vars", {})
        synced_folders = kwargs.get("synced_folders", [])
        exported_env_vars = kwargs.get("exported_env_vars", {})

        agent_install_env_vars_str = (
            " ".join(f'{key}="{value}"' for key, value in agent_install_env_vars.items())
            if agent_install_env_vars
            else ""
        )
        exported_env_vars_str = (
            "\n".join([f'export {key}="{value}"' for key, value in exported_env_vars.items()])
            if exported_env_vars
            else ""
        )

        vm_hostname = self._vm_name  # Already sanitized and unique
        vagrant_box = self.metadata.get("vagrant_box", "net9/ubuntu-24.04-arm64")  # Default box

        synced_folders_str = ""
        for volume in synced_folders:
            # Handle Windows paths that contain drive letters (e.g., C:\path)
            # Look for pattern like ":C:\" or ":D:\" etc.
            windows_path_match = re.search(r':([A-Za-z]:\\.*)', volume)
            if windows_path_match:
                # Split at the position before the drive letter
                split_pos = windows_path_match.start()
                path = volume[:split_pos]
                target = volume[split_pos + 1 :]  # Skip the colon
            else:
                # For non-Windows paths, use simple split
                path, target = volume.split(":", 1)
            synced_folders_str += f'config.vm.synced_folder "{path}", "{target}"\n'

        template = self._get_vagrantfile_template()

        return template.render(
            exported_env_vars_str=exported_env_vars_str,
            vagrant_box=vagrant_box,
            synced_folders_str=synced_folders_str,
            vm_hostname=vm_hostname,
            agent_install_env_vars_str=agent_install_env_vars_str,
        )

    def _run_commands(self, commands: list[str], command_type: str, host=False, shell=False, **kwargs):
        self.app.display_info(f"Running commands of type `{command_type}` in VM `{self._vm_name}`")
        for cmd in commands:
            self._run_command(cmd, command_type, host, shell, **kwargs)

    def _run_command(self, command: str, command_type: str, host=False, shell=False, **kwargs):
        self.app.display_debug(f"[{self._vm_name}] Running command_type: `{command_type}` command: `{command}`")

        command_formatted: str | list[str]
        if host:
            command_formatted = command
        else:
            command_formatted = self._format_command([command])

        self.app.display_debug(f"Running formatted command '{command_formatted}'")

        process = self.platform.run_command(command_formatted, shell=shell, **kwargs)
        stdout = process.stdout.decode("utf-8", errors="replace") if process.stdout else ""
        stderr = process.stderr.decode("utf-8", errors="replace") if process.stderr else ""
        if process.returncode:
            cmd_str = ' '.join(command_formatted) if isinstance(command_formatted, list) else str(command_formatted)
            raise RuntimeError(
                f"Command failed: {cmd_str} (RC: {process.returncode})\nStdout:\n{stdout}\nStderr:\n{stderr}"
            )
        return process, stdout, stderr

    def _initialize(
        self,
        up_command_host: str,
        local_packages: dict[Path, str],
        start_commands: list[str],
        post_install_commands: list[str],
    ):
        self.app.display_info(
            f"Starting up Vagrant VM `{self._vm_name}`",
        )
        self._run_command(
            up_command_host,
            "up_command",
            host=True,
        )

        self.app.display_info(f"Vagrant VM `{self._vm_name}` started successfully.")

        # Configure sudoers after VM is up but before starting the agent
        if sudoers_content := self.metadata.get("vagrant_sudoers_config"):
            self._configure_sudoers(sudoers_content)

        if start_commands:
            self._run_commands(start_commands, "start")

        # Install local packages
        if local_packages:
            self.app.display_info(f"Installing local packages in VM `{self._vm_name}`")

            for local_package, features in local_packages.items():
                package_mount = f'{self._package_mount_dir}{local_package.name}{features}'
                pip_install_cmd = self._build_pip_install_command(package_mount)
                self._run_command(pip_install_cmd, f"installing_local_package_{local_package.name}{features}")

                self.app.display_info(
                    f"Successfully installed local package `{local_package.name}` in Agent Vagrant VM `{self._vm_name}`",  # noqa: E501
                )

        # Execute post_install_commands (guest commands)
        if post_install_commands:
            self._run_commands(post_install_commands, "post-install")

    def _build_pip_install_command(self, package_path: str) -> str:
        """Build the pip install command for the current OS.

        Args:
            package_path: The path to the package to install (including any feature flags)

        Returns:
            The complete pip install command string
        """
        if self._is_windows_vm:
            # Windows: Direct execution without sudo
            return f'{self._python_path} -m pip install --disable-pip-version-check -e {package_path}'
        else:
            # Linux/Unix: Use sudo to run as dd-agent user
            return f'sudo -u dd-agent {self._python_path} -m pip install --disable-pip-version-check -e {package_path}'

    def _format_command(self, guest_command_parts: list[str]) -> list[str]:
        # Returns the host-side command to execute something in the guest.
        # Prepare the command string to be executed inside the VM via ssh -c "..."
        inner_cmd_list = []
        inner_cmd_list.extend(guest_command_parts)

        # Handle sudo for non-Windows guests if metadata suggests it's needed for the command.
        # This is a basic approach. More complex sudo needs might require specific command metadata.
        if not self._is_windows_vm and self.metadata.get("vagrant_command_needs_sudo", False):
            if not inner_cmd_list or inner_cmd_list[0] != "sudo":
                inner_cmd_list.insert(0, "sudo -E")

        inner_cmd_str = " ".join(shlex.quote(part) for part in inner_cmd_list)
        host_command = ["vagrant", "ssh", self._vm_name, "-c", inner_cmd_str.replace("'", "")]
        return host_command

    def _prepare_agent_install_env_vars(self, agent_build: str) -> dict[str, str]:
        """Prepare environment variables for agent installation based on the build."""
        if not agent_build:
            return {}

        agent_install_env_vars = {}
        # format: <pipeline_id>-<major_version>-<arch>"
        # example: "12345-7-x86_64"
        parts = agent_build.split("-")
        if len(parts) != 3 or not all(parts):
            self.app.abort(
                text=f"Invalid `agent_build` format: '{agent_build}'. "
                f"Expected format: '<pipeline_id>-<major_version>-<arch>'"
            )
        pipeline_id, major_version, arch = agent_build.split("-")
        agent_install_env_vars["TESTING_APT_URL"] = "s3.amazonaws.com/apttesting.datad0g.com"
        agent_install_env_vars["TESTING_APT_REPO_VERSION"] = (
            f"pipeline-{pipeline_id}-a{major_version}-{arch} {major_version}"
        )
        agent_install_env_vars["TESTING_YUM_URL"] = "s3.amazonaws.com/yumtesting.datad0g.com"
        agent_install_env_vars["TESTING_YUM_VERSION_PATH"] = (
            f"testing/pipeline-{pipeline_id}-a{major_version}/{major_version}"
        )

        return agent_install_env_vars

    def _prepare_synced_folders(self, local_packages: dict[Path, str]) -> list[str]:
        """Prepare the list of folders to sync between host and VM."""
        synced_folders = []
        synced_folders.extend(self.metadata.get('vagrant_synced_folders', []))

        if self.config_file.is_file():
            synced_folders.append(f'{self.config_file.parent}:{self._config_mount_dir}')

        # It is safe to assume that the directory name is unique across all repos
        for local_package in local_packages:
            synced_folders.append(f'{local_package}:{self._package_mount_dir}{local_package.name}')

        return synced_folders

    def _prepare_host_env_vars(self, env_vars: dict[str, str]) -> EnvVars:
        """Prepare host environment variables for vagrant commands."""
        host_operation_env_vars = EnvVars(os.environ)
        host_operation_env_vars.update(env_vars)  # User-provided can override system for the vagrant command
        return host_operation_env_vars

    def _prepare_exported_env_vars(self, env_vars: dict[str, str]) -> dict[str, str]:
        """Prepare environment variables to export inside the VM for the Agent process."""
        exported_env_vars = env_vars
        exported_env_vars.update(self.metadata.get('env', {}))

        if AgentEnvVars.API_KEY not in env_vars:
            exported_env_vars[AgentEnvVars.API_KEY] = "a" * 32

        # By default, the hostname is the VM hostname (set in VagrantFile with DD_HOSTNAME)
        if self.metadata.get("dd_hostname"):
            exported_env_vars[AgentEnvVars.HOSTNAME] = str(self.metadata.get("dd_hostname", ""))

        exported_env_vars[AgentEnvVars.APM_ENABLED] = self.metadata.get("dd_apm_enabled", "false")
        exported_env_vars[AgentEnvVars.TELEMETRY_ENABLED] = self.metadata.get("dd_telemetry_enabled", "true")
        exported_env_vars[AgentEnvVars.EXPVAR_PORT] = self.metadata.get("dd_expvar_port", "5000")

        if (proxy_data := self.metadata.get("proxy")) is not None:
            if (http_proxy := proxy_data.get("http")) is not None:
                exported_env_vars[AgentEnvVars.PROXY_HTTP] = http_proxy
            if (https_proxy := proxy_data.get("https")) is not None:
                exported_env_vars[AgentEnvVars.PROXY_HTTPS] = https_proxy

        return exported_env_vars

    def _initialize_vm_with_commands(
        self, agent_build: str, local_packages: dict[Path, str], host_operation_env_vars: EnvVars
    ) -> None:
        """Initialize the VM, execute custom commands, and handle agent restart if necessary."""
        # Prepare the vagrant up command
        up_command_host = f"vagrant up {self._vm_name}"

        # Get custom commands from metadata
        start_commands = self.metadata.get("start_commands", [])
        post_install_commands = self.metadata.get("post_install_commands", [])

        # Set up context manager for local package installation
        ensure_local_pkg: Type[AbstractContextManager] | Callable[[], AbstractContextManager] = nullcontext
        if self.config_file.is_file() and local_packages:
            ensure_local_pkg = partial(disable_integration_before_install, self.config_file)

        # Initialize the VM with all configurations
        with ensure_local_pkg():
            self._initialize(
                up_command_host,
                local_packages,
                start_commands,
                post_install_commands,
            )

        # Handle agent restart after initialization if any custom operations were performed
        operations_performed = bool(local_packages or start_commands or post_install_commands)

        if operations_performed:
            self.app.display_info("Custom operations performed. Restarting agent service...")
            self.restart()

    def _configure_sudoers(self, sudoers_content: str) -> None:
        """Configure sudoers to allow dd-agent to run sudo commands without password."""
        if self._is_windows_vm:
            self.app.display_info("Skipping sudoers configuration for Windows VM")
            return

        self.app.display_info(f"Configuring sudoers for dd-agent in VM `{self._vm_name}`")

        # Create commands to configure sudoers
        # Use a here-document to write the sudoers file content
        # This avoids shell escaping issues with multi-line content
        write_sudoers_cmd = f"""sudo bash -c 'cat > {LINUX_SUDOERS_FILE_PATH} << EOF
{sudoers_content}
EOF'"""

        commands = [
            "sudo mkdir -p /etc/sudoers.d",
            write_sudoers_cmd,
            f"sudo chmod 0440 {LINUX_SUDOERS_FILE_PATH}",
            f"sudo chown root:root {LINUX_SUDOERS_FILE_PATH}",
            f"sudo visudo -c -f {LINUX_SUDOERS_FILE_PATH}",
        ]

        # Execute commands using existing vagrant ssh approach
        for cmd in commands:
            # For complex shell commands with pipes, we need to pass them as a single string
            host_cmd = f"vagrant ssh {self._vm_name} -c \"{cmd}\""
            self.app.display_debug(f"Configuring sudoers with command: {host_cmd}")
            self._run_command(host_cmd, "suoders_config_command", host=True)

        self.app.display_info(f"Successfully configured sudoers for dd-agent in VM: {self._vm_name}")

    def _substitute_template_variables(self, value: Any) -> Any:
        """Replace template variables like %HOST% in metadata values."""
        if isinstance(value, str):
            return value.replace("%HOST%", self.VM_HOST_IP)
        elif isinstance(value, list):
            return [self._substitute_template_variables(item) for item in value]
        elif isinstance(value, dict):
            return {k: self._substitute_template_variables(v) for k, v in value.items()}
        return value

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
        # Assumes a synced folder like `/home` or `C:\vagrant` on the guest.
        if self._is_windows_vm:
            return "C:\\vagrant\\packages\\"
        else:
            return "/home/packages/"

    @cached_property
    def _config_mount_dir(self) -> str:
        # Path INSIDE the VM where agent configs are expected.
        name = self.integration.name
        if self._is_windows_vm:
            return f"{WINDOWS_AGENT_CONF_DIR}\\{name}.d"
        else:
            return f"{LINUX_AGENT_CONF_DIR}/{name}.d"

    @cached_property
    def _python_path(self) -> str:
        # Path to python executable INSIDE the VM.
        py_major = self.python_version[0]
        if self._is_windows_vm:
            return f"{WINDOWS_AGENT_PYTHON_PREFIX}{py_major}\\python.exe"
        else:
            return f"{LINUX_AGENT_PYTHON_PREFIX}{py_major}"
