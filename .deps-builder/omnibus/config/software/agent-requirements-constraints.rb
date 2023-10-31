require './lib/paths.rb'

name 'agent-requirements-constraints'

source file: agent_requirements_path

build do
  # Create a constraints.txt file from the original requirements, for
  # which extras (specified with brackets after the package name) need to stripped first
  # (See https://github.com/pypa/pip/issues/8210)
  constraints_file = File.join(build_dir, "constraints.txt")

  block "Create constraints file" do
    requirements = File.read(File.join(project_dir, agent_requirements_in))
    File.open(constraints_file, 'w') { |f| f << requirements.gsub(/\[.*?\]/, "") }
  end

  python_build_env.constrain constraints_file
end
