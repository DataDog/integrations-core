module Omnibus
  class Builder
    def python_build_env
      @python_build_env ||= PythonBuildEnvironment.new(self)
      end
    expose :python_build_env
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
  @@constraints_file = nil

  def initialize(builder)
    @builder = builder
  end

  def create(python, build_dependencies_file)
    # TODO: venv is probably not an option for py2
    @builder.command "#{python} -m venv #{build_root}"
    @builder.command "#{self.python} -m pip install -r #{build_dependencies_file}"
  end

  def python
    File.join(build_root, "bin", "python")
  end

  # Set a constraint file (for all instances)
  def constrain(val)
    # Actually set the value at build time, not load time
    @builder.block "Set constraint file to #{val}" do
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
    # We need to use a block here to ensure an order of execution that is consistent wrt how we set the `constraints_file`.
    # Builder#block uses `instance_eval`, therefore the scope inside the block is as if it were running
    # within the builder instance; that's why we need to access methods via `python_build_env`.
    @builder.block "Build wheels for #{arg}" do
      constraints_arg = python_build_env.constraints_file && "-c #{python_build_env.constraints_file}" || ""

      shellout! "#{python_build_env.python} -m pip wheel --no-build-isolation #{constraints_arg} -w #{python_build_env.wheels_dir} #{arg}", **options
    end
  end

  def wheels_dir
    File.join(@builder.install_dir, "wheels")
  end

  private

  def build_root
    File.join(@builder.build_dir, "build_env")
  end
end
