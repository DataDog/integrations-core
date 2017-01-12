#!/usr/bin/env rake

require 'rake'

unless ENV['CI']
  rakefile_dir = File.dirname(__FILE__)
  ENV['TRAVIS_BUILD_DIR'] = rakefile_dir
  ENV['INTEGRATIONS_DIR'] = File.join(rakefile_dir, 'embedded')
  ENV['PIP_CACHE'] = File.join(rakefile_dir, '.cache/pip')
  ENV['VOLATILE_DIR'] = '/tmp/integration-sdk-testing'
  ENV['CONCURRENCY'] = ENV['CONCURRENCY'] || '2'
  ENV['NOSE_FILTER'] = 'not windows'
  ENV['RUN_VENV'] = 'true'
  ENV['SDK_TESTING'] = 'true'
end

ENV['SDK_HOME'] = File.dirname(__FILE__)

spec = Gem::Specification.find_by_name 'datadog-sdk-testing'
load "#{spec.gem_dir}/lib/tasks/sdk.rake"

def find_check_files()
  Dir.glob("#{ENV['SDK_HOME']}/*/check.py").collect do |file_path|
    check_basename = "#{File.basename(File.dirname(file_path))}.py"
    [check_basename, file_path]
  end.entries
end

def find_yaml_confs()
  yaml_confs = Dir.glob("#{ENV['SDK_HOME']}/*/conf.yaml.example").collect do |file_path|
    yaml_basename = "#{File.basename(File.dirname(file_path))}.yaml.example"
    [yaml_basename, file_path]
  end.entries
  yaml_confs += Dir.glob("#{ENV['SDK_HOME']}/*/conf/*.yaml.example").collect do |file_path|
    yaml_basename = File.basename(file_path)
    [yaml_basename, file_path]
  end.entries
  yaml_confs
end

def find_inconsistencies(files, dd_agent_base_dir)
  inconsistencies = []
  files.each do |file_basename, file_path|
    file_content = File.read(file_path)
    dd_agent_file_path = File.join(ENV['SDK_HOME'], 'embedded', 'dd-agent', dd_agent_base_dir, file_basename)
    if not File.exist?(dd_agent_file_path)
      inconsistencies << "#{file_basename} not found in dd-agent/#{dd_agent_base_dir}/"
      next
    end
    dd_agent_file_content = File.read(dd_agent_file_path)
    if file_content != dd_agent_file_content
      inconsistencies << file_basename
    end
  end

  if inconsistencies.empty?
    puts "No #{dd_agent_base_dir} inconsistencies found"
  else
    puts "## #{dd_agent_base_dir} inconsistencies:"
    puts inconsistencies.join("\n")
  end
end

desc 'Outputs the checks/example configs of this repo that do not match the ones in `dd-agent` (temporary task)'
task dd_agent_consistency: [:pull_latest_agent] do
  find_inconsistencies(find_check_files(), 'checks.d')
  find_inconsistencies(find_yaml_confs(), 'conf.d')
end
