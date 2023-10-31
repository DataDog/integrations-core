require './lib/paths.rb'

name 'datadog-agent-integrations-buildenv-py3'

source file: File.join(integrations_core_root, '.deps/build_dependencies.txt')

dependency "datadog-agent-prepare"
dependency "python3"

build do
  if windows?
    python = "#{windows_safe_path(python_3_embedded)}\\python.exe"
  else
    python = "#{install_dir}/embedded/bin/python3"
  end

  # Install build dependencies in a virtual environment
  python_build_env.create python, "build_dependencies.txt"
end
