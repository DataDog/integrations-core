# (Computed) constants for use across definitions

def integrations_core_root
  default_root = windows? ? 'C:\integrations-core' : '/integrations-core'
  root = ENV.fetch('INTEGRATIONS_CORE_PATH', default_root)
end

def agent_requirements_in
  'agent_requirements.in'
end

def agent_requirements_path
  File.join(integrations_core_root, 'datadog_checks_base/datadog_checks/base/data', agent_requirements_in)
end
