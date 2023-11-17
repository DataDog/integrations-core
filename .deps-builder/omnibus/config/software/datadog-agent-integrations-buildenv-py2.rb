require './lib/paths.rb'

name 'datadog-agent-integrations-buildenv-py2'

source file: File.join(integrations_core_root, '.deps/build_dependencies.txt')

dependency "datadog-agent-prepare"
dependency "python2"

build do
  if windows?
    python = "#{windows_safe_path(python_2_embedded)}\\python.exe"
  else
    python = "#{install_dir}/embedded/bin/python2"
  end

  # Install build dependencies in a virtual environment
  python_build_env_py2.create python, "build_dependencies.txt"
end
