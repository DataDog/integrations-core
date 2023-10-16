module Omnibus
  class Builder
    def python_build_env
      @python_build_env ||= PythonBuildEnvironment.new(self)
      end
    expose :python_build_env
  end
end

class PythonBuildEnvironment
  def initialize(builder)
    @builder = builder
  end

  def create(python, build_dependencies_file)
    # TODO: venv is probably not an option for py2
    @builder.command "#{python} -m venv #{build_root} #{runtime_root}"
    @builder.command "#{build_env_python} -m pip install -r #{build_dependencies_file}"
  end

  def build_env_python
    File.join(build_root, "bin", "python")
  end

  def runtime_python
    File.join(runtime_root, "bin", "python")
  end

  # Run pip install on a requirements file with PYTHONPATH set to this build environment
  # `options` are passed to the `shellout!` function used to run commands
  def install_requirements(requirements_file, **options)
    # Builder#block uses `instance_eval`, therefore the scope inside the block is as if it were running
    # within the builder instance; that's why we need to access methods via `python_build_env`.
    @builder.block "Install Python requirements from #{requirements_file}" do
      # TODO: This current approach is py3 only, find some reasonable alternative for py2.
      get_site_script = 'import site; import os; print(os.pathsep.join(site .getsitepackages()))'

      # Set PYTHONPATH to the `site_path` of the build environment
      site_path = shellout!("#{python_build_env.build_env_python} -c '#{get_site_script}'").stdout.strip
      env = {"PYTHONPATH" => site_path}.merge(options[:env])
      options = options.merge({env: env})

      shellout! "#{python_build_env.runtime_python} -m pip install --no-build-isolation -r #{requirements_file}", **options
    end
  end

  # Run pip wheel on a requirements file with PYTHONPATH set to this build environment
  # `options` are passed to the `shellout!` function used to run commands
  def wheels_for_requirements(requirements_file, output_dir, **options)
    # Builder#block uses `instance_eval`, therefore the scope inside the block is as if it were running
    # within the builder instance; that's why we need to access methods via `python_build_env`.
    @builder.block "Install Python requirements from #{requirements_file}" do
      # TODO: This current approach is py3 only, find some reasonable alternative for py2.
      get_site_script = 'import site; import os; print(os.pathsep.join(site.getsitepackages()))'

      # Set PYTHONPATH to the `site_path` of the build environment
      site_path = shellout!("#{python_build_env.build_env_python} -c '#{get_site_script}'").stdout.strip
      env = {"PYTHONPATH" => site_path}.merge(options[:env])
      options = options.merge({env: env})

      shellout! "#{python_build_env.runtime_python} -m pip wheel --no-build-isolation -w #{output_dir} -r #{requirements_file}", **options
    end
  end

  private

  def build_root
    File.join(@builder.build_dir, "build_env")
  end

  def runtime_root
    File.join(@builder.build_dir, "runtime_env")
  end
end
