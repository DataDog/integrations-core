name 'virtualenv'

dependency 'python3'


build do
  if windows?
    python = "#{windows_safe_path(python_3_embedded)}\\python.exe"
  else
    python = "#{install_dir}/embedded/bin/python3"
  end

  # Note: virtualenv v20.22.0 dropped support for creating py2-based virtual environments,
  # that's why we stick for an older version.
  command "#{python} -m pip install virtualenv==20.21.1"
end
