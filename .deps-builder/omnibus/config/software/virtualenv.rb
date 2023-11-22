name 'virtualenv'

dependency 'python3'


build do
  # Note: virtualenv v20.22.0 dropped support for creating py2-based virtual environments,
  # that's why we stick for an older version.
  command "#{python_build_env.system_python} -m pip install virtualenv==20.21.1"
end
