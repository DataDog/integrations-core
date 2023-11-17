require './lib/ostools.rb'


module Omnibus
  class Builder
    def python_build_env
      @python_build_env ||= PythonBuildEnvironment.new(self)
    end
    expose :python_build_env

    def python_build_env_py2
      @python_build_env_py2 ||= Python2BuildEnvironment.new(self)
    end
    expose :python_build_env_py2
  end
end

class PythonBuildEnvironment
  # Class to interact with the Python build environment in a way that is convenient
  # for implementing the Python dependency resolution and building model that we
  # use for Agent integration dependencies. It's designed to add build commands in `build` blocks
  # inside software definitions.
  # Note that the Python build environment itself is assumed to be a global (per-project) entity,
  # and instances of the class are expected to use the same data for the most part,
  # they exist as instances mostly to hold a reference to the current builder.
  include Omnibus::Util

  @@constraints_file = nil

  def initialize(builder)
    @builder = builder
  end

  def create(python, build_dependencies_file)
    @builder.command "#{system_python} -m virtualenv --python #{python} #{build_root}"
    @builder.command "#{self.python} -m pip install -r #{build_dependencies_file}"
  end

  def python
    windows_safe_path(build_root, os == 'windows' ? "Scripts" : "bin", "python")
  end

  # Set a constraint file (for all instances)
  def constrain(val)
    # Actually set the value at build time, not load time, hence the use of a `block`
    @builder.block "Set constraints file to #{val}" do
      python_build_env.constraints_file = val
    end
  end

  def constraints_file
    @@constraints_file
  end

  def constraints_file=(val)
    @@constraints_file = val
  end

  # Run `pip wheel` with this build environment store the produced wheels
  # inside the project's `installdir`. Apply constraints file if set.
  # `options` are passed to the `shellout!` function used to run commands
  def wheel(arg, **options)
    root = build_root
    build_env = self
    # We need to use a block here to ensure an order of execution that is consistent wrt how we set the `constraints_file`.
    # Builder#block uses `instance_eval`, therefore the scope inside the block is as if it were running
    # within the builder instance; that's why we need to access methods via `python_build_env`.
    @builder.block "Build wheels for #{arg}" do
      # Add the virtual environment's binary path to PATH
      bin_path = File.join(root, windows? ? 'Scripts' : 'bin')
      paths = (options.dig(:env, "PATH") || ENV["PATH"])&.split(File::PATH_SEPARATOR) || []
      paths.prepend(bin_path)
      options[:env] = options.fetch(:env, {}).merge({"PATH" => paths.join(File::PATH_SEPARATOR)})

      # This forces the dependency resolution to ensure that the global constraints are respected
      constraints_arg = build_env.constraints_file && "-c #{build_env.constraints_file}" || ""

      # We pass the `wheels_dir` to `--find-links` to avoid rebuilding wheels that we already have
      shellout! "#{build_env.python} -m pip wheel --no-build-isolation " \
                "--find-links #{build_env.wheels_dir} " \
                "#{constraints_arg} -w #{build_env.wheels_dir} #{arg}",
                **options
    end
  end

  def wheels_dir
    windows_safe_path(@builder.install_dir, "wheels")
  end

  protected

  def build_root
    windows_safe_path(@builder.build_dir, "build_env")
  end

  # The path to the base python used to install virtualenv
  def system_python
    if os == 'windows'
      python = "#{windows_safe_path(@builder.python_3_embedded)}\\python.exe"
    else
      python = "#{@builder.install_dir}/embedded/bin/python3"
    end
  end
end


class Python2BuildEnvironment < PythonBuildEnvironment
  def wheels_dir
    windows_safe_path(@builder.install_dir, "wheels_py2")
  end

  protected

  def build_root
    windows_safe_path(@builder.build_dir, "build_env_py2")
  end
end
