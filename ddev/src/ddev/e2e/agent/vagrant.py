# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import hashlib
import os
import shlex
import shutil
import subprocess
import sys
from contextlib import AbstractContextManager, contextmanager, nullcontext
from functools import cached_property, partial
from typing import TYPE_CHECKING, Any, Callable, Type

from jinja2 import Template

from ddev.e2e.agent.constants import AgentEnvVars
from ddev.e2e.agent.interface import AgentInterface
from ddev.utils.fs import Path
from ddev.utils.structures import EnvVars

if TYPE_CHECKING:
    from ddev.integration.core import Integration
    from ddev.utils.fs import Path
    from ddev.utils.platform import Platform


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
    # Default private network IP for the VM (matches Vagrantfile.template)
    VM_HOST_IP = "172.30.1.5"

    def _substitute_template_variables(self, value: Any) -> Any:
        """Replace template variables like %HOST% in metadata values."""
        if isinstance(value, str):
            return value.replace("%HOST%", self.VM_HOST_IP)
        elif isinstance(value, list):
            return [self._substitute_template_variables(item) for item in value]
        elif isinstance(value, dict):
            return {k: self._substitute_template_variables(v) for k, v in value.items()}
        return value

    def __init__(
        self, platform: Platform, integration: Integration, env: str, metadata: dict[str, Any], config_file: Path
    ) -> None:
        # Apply template substitution to the entire metadata dictionary
        metadata = self._substitute_template_variables(metadata)
        super().__init__(platform, integration, env, metadata, config_file)
        self._initialize_vagrant(overwrite=False)

    def _initialize_vagrant(self, overwrite: bool = False, **kwargs):
        # Initialize and create the directory for Vagrant files specific to this VM
        home_dir = Path.home()
        self._temp_vagrant_dir = home_dir / ".ddev" / "vagrant" / self._vm_name
        self._temp_vagrant_dir.mkdir(parents=True, exist_ok=True)

        # Generate Vagrantfile if it doesn't exist
        vagrantfile_path = self._temp_vagrant_dir / "Vagrantfile"
        if not vagrantfile_path.exists() or overwrite:
            old_file_hash = None
            if overwrite:
                old_file_hash = hashlib.sha256(vagrantfile_path.read_text().encode()).hexdigest()
                print(f"Overwriting Vagrantfile found at '{vagrantfile_path}'.")
                vagrantfile_path.unlink()
                print(f"Vagrantfile deleted at {vagrantfile_path}")
            else:
                print(f"Vagrantfile not found at {vagrantfile_path}, generating new one.")

            vagrantfile_content = self._generate_vagrantfile_content(**kwargs)
            vagrantfile_path.write_text(vagrantfile_content)
            print(f"Vagrantfile generated at {vagrantfile_path}")
            new_file_hash = hashlib.sha256(vagrantfile_content.encode()).hexdigest()
            if old_file_hash and old_file_hash != new_file_hash:
                self.metadata["vagrant_provision"] = True
        else:
            print(f"Using existing Vagrantfile at {vagrantfile_path}")

        # Set VAGRANT_CWD to self.temp_vagrant_dir
        os.environ["VAGRANT_CWD"] = str(self._temp_vagrant_dir)
        print(f"Vagrant working directory set to: {self._temp_vagrant_dir}")

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
            " ".join([f'{key}="{value}"' for key, value in agent_install_env_vars.items()])
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
            path, target = volume.split(":")
            synced_folders_str += f'config.vm.synced_folder "{path}", "{target}"\n'

        template = self._get_vagrantfile_template()

        return template.render(
            dd_api_key=os.environ.get("DD_API_KEY", ""),
            exported_env_vars_str=exported_env_vars_str,
            vagrant_box=vagrant_box,
            synced_folders_str=synced_folders_str,
            vm_hostname=vm_hostname,
            agent_install_env_vars_str=agent_install_env_vars_str,
        )

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
        base_synced_dir = "C:\\vagrant" if self._is_windows_vm else "/home"
        return os.path.join(base_synced_dir, "packages/").replace(
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
        inner_cmd_list.extend(guest_command_parts)

        # Handle sudo for non-Windows guests if metadata suggests it's needed for the command.
        # This is a basic approach. More complex sudo needs might require specific command metadata.
        if not self._is_windows_vm and self.metadata.get("vagrant_command_needs_sudo", False):
            if not inner_cmd_list or inner_cmd_list[0] != "sudo":
                inner_cmd_list.insert(0, "sudo -E")

        inner_cmd_str = " ".join(shlex.quote(part) for part in inner_cmd_list)
        host_command = ["vagrant", "ssh", self._vm_name, "-c", inner_cmd_str.replace("'", "")]
        return host_command

    def _captured_process(self, host_command: list[str], **kwargs) -> subprocess.CompletedProcess:
        kwargs.setdefault("check", False)

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
        # prepare agent install scripts environment variables
        agent_install_env_vars = {}

        if agent_build:
            pipeline_id, major_version, arch = agent_build.split("-")
            agent_install_env_vars["TESTING_APT_URL"] = "s3.amazonaws.com/apttesting.datad0g.com"
            agent_install_env_vars["TESTING_APT_REPO_VERSION"] = (
                f"pipeline-{pipeline_id}-a{major_version}-{arch} {major_version}"
            )
            agent_install_env_vars["TESTING_YUM_URL"] = "s3.amazonaws.com/yumtesting.datad0g.com"
            agent_install_env_vars["TESTING_YUM_VERSION_PATH"] = (
                f"testing/pipeline-{pipeline_id}-a{major_version}/{major_version}"
            )

        # prepare synced_folders
        synced_folders = []
        synced_folders.extend(self.metadata.get('vagrant_synced_folders', []))

        ensure_local_pkg: Type[AbstractContextManager] | Callable[[], AbstractContextManager] = nullcontext
        if self.config_file.is_file():
            synced_folders.append(f'{self.config_file.parent}:{self._config_mount_dir}')
            if local_packages:
                ensure_local_pkg = partial(disable_integration_before_install, self.config_file)

        # It is safe to assume that the directory name is unique across all repos
        for local_package in local_packages:
            synced_folders.append(f'{local_package}:{self._package_mount_dir}{local_package.name}')

        # Host environment variables for `vagrant up` command itself
        host_operation_env_vars = EnvVars(os.environ)
        host_operation_env_vars.update(env_vars)  # User-provided can override system for the vagrant command

        # Prepare environment variables intended for the Agent process inside the VM.
        exported_env_vars = {}
        exported_env_vars.update(self.metadata.get('env', {}))
        if AgentEnvVars.API_KEY not in env_vars:
            exported_env_vars[AgentEnvVars.API_KEY] = "a" * 32

        # By default, the hostname is the VM hostname (set in VagrantFile with DD_HOSTNAME)
        if self.metadata.get("dd_hostname"):
            exported_env_vars[AgentEnvVars.HOSTNAME] = self.metadata.get("dd_hostname")

        exported_env_vars[AgentEnvVars.APM_ENABLED] = self.metadata.get("dd_apm_enabled", "false")
        exported_env_vars[AgentEnvVars.TELEMETRY_ENABLED] = self.metadata.get("dd_telemetry_enabled", "true")
        exported_env_vars[AgentEnvVars.EXPVAR_PORT] = self.metadata.get("dd_expvar_port", "5000")
        if (proxy_data := self.metadata.get("proxy")) is not None:
            if (http_proxy := proxy_data.get("http")) is not None:
                exported_env_vars[AgentEnvVars.PROXY_HTTP] = http_proxy
            if (https_proxy := proxy_data.get("https")) is not None:
                exported_env_vars[AgentEnvVars.PROXY_HTTPS] = https_proxy

        # We can now generate the Vagrantfile content
        self._initialize_vagrant(
            overwrite=True,
            exported_env_vars=exported_env_vars,
            agent_install_env_vars=agent_install_env_vars,
            synced_folders=synced_folders,
        )

        print(f"Starting Vagrant environment for VM: {self._vm_name} with agent build: '{agent_build}'")

        up_command_host = ["vagrant", "up", self._vm_name]
        if self.metadata.get("vagrant_provision", False):
            print(f"VagrantFile changed, provisioning Vagrant VM: {self._vm_name}")
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

        with ensure_local_pkg():
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
            f"Bringing up Vagrant VM: {self._vm_name} from {self._temp_vagrant_dir} "
            f"with command: {' '.join(up_command_host)}"
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

        # Configure sudoers after VM is up but before starting the agent
        if sudoers_content := self.metadata.get("vagrant_sudoers_config"):
            self._configure_sudoers(sudoers_content)

        if start_guest_commands:
            self._run_commands(start_guest_commands, "start")

        # Install local packages
        if local_packages:
            print(f"Installing local packages in VM `{self._vm_name}`...")
            base_pip_command = [
                "sudo",
                "-u",
                "dd-agent",
                self._python_path,
                '-m',
                'pip',
                'install',
                '--disable-pip-version-check',
                '-e',
            ]
            for local_package, features in local_packages.items():
                package_mount = f'{self._package_mount_dir}{local_package.name}{features}'
                formatted_cmd = self._format_command([*base_pip_command, package_mount])
                print(f"Running command: {' '.join(formatted_cmd)}")
                process = self._captured_process(formatted_cmd)
                stdout = process.stdout.decode("utf-8", errors="replace") if process.stdout else ""
                stderr = process.stderr.decode("utf-8", errors="replace") if process.stderr else ""
                if process.returncode:
                    raise RuntimeError(
                        f"Failed to run command `{' '.join(formatted_cmd)}` in VM `{self._vm_name}` "
                        f"(RC: {process.returncode}).\n"
                        f"Stdout:\n{stdout}\nStderr:\n{stderr}"
                    )
                print(
                    f"Successfully installed  local package `{local_package.name}` in Agent Vagrant VM "
                    f"`{self._vm_name}`\n stdout: {stdout}"
                )

        # Execute post_install_commands (guest commands)
        if post_install_guest_commands:
            self._run_commands(post_install_guest_commands, "post-install")

    def _run_commands(self, commands: list[str], command_type: str) -> None:
        print(f"Running {command_type} commands in VM `{self._vm_name}`...")
        for guest_cmd_str in commands:
            cmd_parts_guest = self.platform.modules.shlex.split(guest_cmd_str)
            formatted_host_cmd = self._format_command(cmd_parts_guest)
            process = self._captured_process(formatted_host_cmd)
            stdout = process.stdout.decode("utf-8", errors="replace") if process.stdout else ""
            stderr = process.stderr.decode("utf-8", errors="replace") if process.stderr else ""
            if process.returncode:
                raise RuntimeError(
                    f"Failed to run {command_type} command `{' '.join(cmd_parts_guest)}` in VM "
                    f"`{self._vm_name}` (RC: {process.returncode}).\n"
                    f"Stdout:\n{stdout}\nStderr:\n{stderr}"
                )
            print(f"Successfully ran {command_type} command `{' '.join(cmd_parts_guest)}`.\n{stdout}")

    def stop(self) -> None:
        print(f"Stopping Vagrant VM: {self._vm_name}...")
        stop_guest_commands = self.metadata.get("stop_commands", [])
        if stop_guest_commands:
            self._run_commands(stop_guest_commands, "stop")

        # Halt the VM
        halt_cmd_host = ["vagrant", "halt", self._vm_name]
        print(f"Halting VM: {self._vm_name} with command: {' '.join(halt_cmd_host)}")
        process_halt = self._captured_process(halt_cmd_host)  # cwd is no longer set by _captured_process
        if process_halt.returncode:
            print(
                f"Failed to halt Vagrant VM `{self._vm_name}` (RC: {process_halt.returncode}). "
                f"Stderr: "
                f"{process_halt.stderr.decode('utf-8', errors='replace') if process_halt.stderr else 'N/A'}"
            )
        else:
            print(f"VM {self._vm_name} halted.")

        # Destroy the VM
        destroy_cmd_host = ["vagrant", "destroy", self._vm_name, "--force"]
        print(f"Destroying VM: {self._vm_name} with command: {' '.join(destroy_cmd_host)}")
        process_destroy = self._captured_process(destroy_cmd_host)
        if process_destroy.returncode:
            raise RuntimeError(
                f"Failed to destroy Vagrant VM `{self._vm_name}` (RC: {process_destroy.returncode}).\n"
                f"Stdout: "
                f"{process_destroy.stdout.decode('utf-8', errors='replace') if process_destroy.stdout else 'N/A'}\n"
                f"Stderr: "
                f"{process_destroy.stderr.decode('utf-8', errors='replace') if process_destroy.stderr else 'N/A'}"
            )
        print(f"VM {self._vm_name} destroyed.")

        # delete the temp vagrant dir
        shutil.rmtree(self._temp_vagrant_dir)
        print(f"Vagrant working directory deleted: {self._temp_vagrant_dir}")

    def restart(self) -> None:
        print(f"Restarting (reloading) Vagrant VM: {self._vm_name}...")
        reload_cmd_host = ["vagrant", "reload", self._vm_name]
        if self.metadata.get("vagrant_provision_on_reload", True):  # Default to reprovisioning on reload
            reload_cmd_host.append("--provision")

        process = self._captured_process(reload_cmd_host)
        stdout = process.stdout.decode("utf-8", errors="replace") if process.stdout else ""
        stderr = process.stderr.decode("utf-8", errors="replace") if process.stderr else ""
        if process.returncode:
            raise RuntimeError(
                f"Failed to restart (reload) Vagrant VM `{self._vm_name}` "
                f"(RC: {process.returncode}).\n"
                f"Stdout:\n{stdout}\nStderr:\n{stderr}"
            )
        print(f"Vagrant VM `{self._vm_name}` restarted successfully.\n{stdout}")

    def restart_agent_service(self) -> None:
        # Restarts the Datadog Agent service *inside* the VM
        print(f"Restarting Datadog Agent service in VM: {self._vm_name}...")
        if self._is_windows_vm:
            # Example for Windows: restart using sc. Ensure agent service name is correct.
            agent_service_name = self.metadata.get("vagrant_windows_agent_service_name", "DatadogAgent")
            # Stop and then start, as 'restart' is not always available/reliable with sc for all services
            guest_cmds = [f"sc stop {agent_service_name}", f"sc start {agent_service_name}"]
        else:
            restart_cmd_str = "sudo service datadog-agent restart"
            guest_cmds = [restart_cmd_str]

        self._run_commands(guest_cmds, "restart-agent-service")
        print("Datadog Agent service restart sequence completed.")

    def invoke(self, args: list[str]) -> None:
        # Runs an 'agent <command>' inside the VM
        agent_bin = (
            "/opt/datadog-agent/bin/agent/agent"
            if not self._is_windows_vm
            else "C:\\Program Files\\Datadog\\Datadog Agent\\bin\\agent.exe"
        )

        guest_cmd_parts = ["sudo", agent_bin] + args
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

    def _configure_sudoers(self, sudoers_content: str) -> None:
        """Configure sudoers to allow dd-agent to run sudo commands without password."""
        if self._is_windows_vm:
            print("Skipping sudoers configuration for Windows VM")
            return

        print(f"Configuring sudoers for dd-agent in VM: {self._vm_name}")

        sudoers_file = "/etc/sudoers.d/dd-agent"

        # Create commands to configure sudoers
        # Use a here-document to write the sudoers file content
        # This avoids shell escaping issues with multi-line content
        write_sudoers_cmd = f"""sudo bash -c 'cat > {sudoers_file} << EOF
{sudoers_content}
EOF'"""

        commands = [
            "sudo mkdir -p /etc/sudoers.d",
            write_sudoers_cmd,
            f"sudo chmod 0440 {sudoers_file}",
            f"sudo chown root:root {sudoers_file}",
            f"sudo visudo -c -f {sudoers_file}",
        ]

        # Execute commands using existing vagrant ssh approach
        for cmd in commands:
            # For complex shell commands with pipes, we need to pass them as a single string
            host_cmd = ["vagrant", "ssh", self._vm_name, "-c", cmd]
            process = self._captured_process(host_cmd)

            if process.returncode != 0:
                stdout = process.stdout.decode('utf-8', errors='replace') if process.stdout else ''
                stderr = process.stderr.decode('utf-8', errors='replace') if process.stderr else ''
                # For visudo, the error messages often go to stdout
                error_output = stderr or stdout or 'No error output captured'
                raise RuntimeError(
                    f"Failed to execute command '{cmd}' on VM {self._vm_name}. "
                    f"Exit status: {process.returncode}, Error: {error_output}"
                )

        print(f"Successfully configured sudoers for dd-agent in VM: {self._vm_name}")
