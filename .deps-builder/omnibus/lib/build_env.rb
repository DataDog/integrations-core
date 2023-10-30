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
  # use for Agent integration dependencies.
  # Note that the Python build environment itself is assumed to be a global (per-project) entity,
  # and instances of the class are expected to use the same data for the most part,
  # they exist as instances mostly to hold a reference to the current builder.

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
    @@constraint_file = val
  end

  def constraint_file
    @@constraint_file
  end

  # Run pip wheel with PYTHONPATH set to this build environment and store the produced wheels
  # inside the project's `installdir`. Apply constraint file if set.
  # `options` are passed to the `shellout!` function used to run commands
  def wheel(arg, **options)
    # Builder#block uses `instance_eval`, therefore the scope inside the block is as if it were running
    # within the builder instance; that's why we need to access methods via `python_build_env`.
    @builder.block "Build wheels for #{arg}" do
      constraint_arg = python_build_env.constraint_file && "-c #{python_build_env.constraint_file}" || ""

      shellout! "#{python_build_env.python} -m pip wheel --no-build-isolation #{constraint_arg} -w #{python_build_env.wheels_dir} #{arg}", **options
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
