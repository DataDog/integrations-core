# (Computed) constants for use across definitions

def integrations_core_root
  root = ENV.fetch('INTEGRATIONS_CORE_PATH', '/integrations-core')
end

def agent_requirements_in
  'agent_requirements.in'
end

def agent_requirements_path
  File.join(integrations_core_root, 'datadog_checks_base/datadog_checks/base/data', agent_requirements_in)
end
