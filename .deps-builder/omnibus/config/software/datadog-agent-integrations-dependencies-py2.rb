require './lib/paths.rb'

name 'datadog-agent-integrations-dependencies-py2'

source file: agent_requirements_path

dependency "datadog-agent-integrations-buildenv-py2"
dependency "agent-requirements-constraints"

if arm?
  # same with libffi to build the cffi wheel
  dependency 'libffi'
  # same with libxml2 and libxslt to build the lxml wheel
  dependency 'libxml2'
  dependency 'libxslt'
end

if osx?
  dependency 'postgresql'
  dependency 'unixodbc'
end

if linux?
  # * Psycopg2 doesn't come with pre-built wheel on the arm architecture.
  #   to compile from source, it requires the `pg_config` executable present on the $PATH
  # * We also need it to build psycopg[c] Python dependency
  # * Note: because having unixodbc already built breaks postgresql build,
  #   we made unixodbc depend on postgresql to ensure proper build order.
  #   If we're ever removing/changing one of these dependencies, we need to
  #   take this into account.
  dependency 'postgresql'
  # add nfsiostat script
  dependency 'unixodbc'
  dependency 'freetds'  # needed for SQL Server integration
  dependency 'nfsiostat'
  # add libkrb5 for all integrations supporting kerberos auth with `requests-kerberos`
  dependency 'libkrb5'
  # needed for glusterfs
  dependency 'gstatus'
end


# package names of dependencies that won't be added to the Agent Python environment
excluded_packages = Array.new

if osx?
  # exclude aerospike, new version 3.10 is not supported on MacOS yet
  excluded_packages.push(/^aerospike==/)
end

if arm?
  # This doesn't build on ARM
  excluded_packages.push(/^pymqi==/)
end

if arm? || !_64_bit?
  excluded_packages.push(/^orjson==/)
end

build do
  # aliases for pip
  if windows?
    python = "#{windows_safe_path(python_2_embedded)}\\python.exe"
  else
    python = "#{install_dir}/embedded/bin/python2"
  end

  # If a python_mirror is set, it is set in a pip config file so that we do not leak the token in the CI output
  pip_config_file = ENV['PIP_CONFIG_FILE']
  pre_build_env = {
    "PIP_CONFIG_FILE" => "#{pip_config_file}"
  }

  nix_build_env = {
    "PIP_CONFIG_FILE" => "#{pip_config_file}",
    "CFLAGS" => "-I#{install_dir}/embedded/include -I/opt/mqm/inc",
    "CXXFLAGS" => "-I#{install_dir}/embedded/include -I/opt/mqm/inc",
    "LDFLAGS" => "-L#{install_dir}/embedded/lib -L/opt/mqm/lib64 -L/opt/mqm/lib",
    "LD_RUN_PATH" => "#{install_dir}/embedded/lib -L/opt/mqm/lib64 -L/opt/mqm/lib",
    "PATH" => "#{install_dir}/embedded/bin:#{ENV['PATH']}",
  }

  win_build_env = {
    "PIP_CONFIG_FILE" => "#{pip_config_file}",
    "CFLAGS" => ""
  }

  # On Linux & Windows, specify the C99 standard explicitly to avoid issues while building some
  # wheels (eg. ddtrace).
  # Not explicitly setting that option has caused us problems in the past on SUSE, where the ddtrace
  # wheel has to be manually built, as the C code in ddtrace doesn't follow the C89 standard (the default value of std).
  # Note: We don't set this on MacOS, as on MacOS we need to build a bunch of packages & C extensions that
  # don't have precompiled MacOS wheels. When building C extensions, the CFLAGS variable is added to
  # the command-line parameters, even when compiling C++ code, where -std=c99 is invalid.
  # See: https://github.com/python/cpython/blob/v2.7.18/Lib/distutils/sysconfig.py#L222
  if linux? || windows?
    nix_build_env["CFLAGS"] += " -std=c99"
    win_build_env["CFLAGS"] += " -std=c99"
  end

  # Some libraries (looking at you, aerospike-client-python) need EXT_CFLAGS instead of CFLAGS.
  nix_specific_build_env = {
    "aerospike" => nix_build_env.merge({"EXT_CFLAGS" => nix_build_env["CFLAGS"] + " -std=gnu99"}),
    # Always build pyodbc from source to link to the embedded version of libodbc
    "pyodbc" => nix_build_env.merge({"PIP_NO_BINARY" => "pyodbc"}),
  }

  win_specific_build_env = {}

  #
  # Prepare the requirements file containing ALL the dependencies needed by
  # any integration. This will provide the "static Python environment" of the Agent.
  # We don't use the .in file provided by the base check directly because we
  # want to filter out things before installing.
  #
  filtered_agent_requirements_in = 'agent_requirements-py2.in'
  if windows?
    static_reqs_in_file = "#{windows_safe_path(project_dir)}\\#{agent_requirements_in}"
    static_reqs_out_folder = "#{windows_safe_path(project_dir)}\\"
    static_reqs_out_file = static_reqs_out_folder + filtered_agent_requirements_in
  else
    static_reqs_in_file = "#{project_dir}/#{agent_requirements_in}"
    static_reqs_out_folder = "#{project_dir}/"
    static_reqs_out_file = static_reqs_out_folder + filtered_agent_requirements_in
  end

  specific_build_env = windows? ? win_specific_build_env : nix_specific_build_env
  build_env = windows? ? win_build_env : nix_build_env

  # Creating a hash containing the requirements and requirements file path associated to every lib
  requirements_custom = Hash.new()
  specific_build_env.each do |lib, env|
    requirements_custom[lib] = {
      "req_lines" => Array.new,
      "req_file_path" => static_reqs_out_folder + lib + "-py2.in",
    }
  end

  # Remove any excluded requirements from the static-environment req file
  requirements = Array.new

  block "Create filtered requirements" do
    File.open("#{static_reqs_in_file}", 'r+').readlines().each do |line|
      next if excluded_packages.any? { |package_regex| line.match(package_regex) }

      if line.start_with?('psycopg[binary]') && !windows?
        line.sub! 'psycopg[binary]', 'psycopg[c]'
      end
      # Keeping the custom env requirements lines apart to install them with a specific env
      requirements_custom.each do |lib, lib_req|
        if Regexp.new('^' + lib + '==').freeze.match line
          lib_req["req_lines"].push(line)
        end
      end
      # In any case we add the lib to the requirements files to avoid inconsistency in the installed versions
      # For example if aerospike has dependency A>1.2.3 and a package in the big requirements file has A<1.2.3, the install process would succeed but the integration wouldn't work.
      requirements.push(line)
    end

    # Adding pympler for memory debug purposes
    requirements.push("pympler==0.7")
  end

  # Render the filtered requirements file
  erb source: "static_requirements.txt.erb",
      dest: "#{static_reqs_out_file}",
      mode: 0640,
      vars: { requirements: requirements }

  # Render the filtered libraries that are to be built with different env var
  requirements_custom.each do |lib, lib_req|
    erb source: "static_requirements.txt.erb",
        dest: "#{lib_req["req_file_path"]}",
        mode: 0640,
        vars: { requirements: lib_req["req_lines"] }
  end

  # Build dependencies
  # First we install the dependencies that need specific flags
  specific_build_env.each do |lib, env|
    python_build_env_py2.wheel "-r #{requirements_custom[lib]['req_file_path']}", env: env
  end

  # Then the ones requiring their own environment variables
  python_build_env_py2.wheel "-r #{static_reqs_out_file}", env: build_env

  # Produce a lockfile
  # TODO Move this to some constant so that we can reference the same name when "packaging"
  lockfile_path = File.join(install_dir, "frozen-py2.txt")
  command "#{python_build_env_py2.python} -m piptools compile --generate-hashes " \
          "--no-header --no-index --no-emit-find-links --generate-hashes " \
          "-f #{python_build_env_py2.wheels_dir} -o #{lockfile_path} #{agent_requirements_in}"
end
