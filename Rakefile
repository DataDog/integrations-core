#!/usr/bin/env rake

require 'rake'

unless ENV['CI']
  rakefile_dir = File.dirname(__FILE__)
  ENV['TRAVIS_BUILD_DIR'] = rakefile_dir
  ENV['INTEGRATIONS_DIR'] = File.join(rakefile_dir, 'embedded')
  ENV['PIP_CACHE'] = File.join(rakefile_dir, '.cache/pip')
  ENV['VOLATILE_DIR'] = '/tmp/integration-sdk-testing'
  ENV['CONCURRENCY'] = ENV['CONCURRENCY'] || '2'
  ENV['NOSE_FILTER'] = ENV['NOSE_FILTER'] || 'not windows'
  ENV['RUN_VENV'] = 'true'
  ENV['SDK_TESTING'] = 'true'
end

ENV['SDK_HOME'] = File.dirname(__FILE__)

spec = Gem::Specification.find_by_name 'datadog-sdk-testing'
load "#{spec.gem_dir}/lib/tasks/sdk.rake"

def find_check_files
  Dir.glob("#{ENV['SDK_HOME']}/*/check.py").collect do |file_path|
    check_basename = "#{File.basename(File.dirname(file_path))}.py"
    [check_basename, file_path]
  end.entries
end

def find_yaml_confs
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
    dd_agent_file_path = File.join(
      ENV['SDK_HOME'],
      'embedded',
      'dd-agent',
      dd_agent_base_dir,
      file_basename
    )
    unless File.exist?(dd_agent_file_path)
      inconsistencies << "#{file_basename} not found in dd-agent/#{dd_agent_base_dir}/"
      next
    end
    if file_content != File.read(dd_agent_file_path)
      inconsistencies << file_basename
    end
  end
  inconsistencies
end

def print_inconsistencies(display_name, inconsistencies)
  if inconsistencies.empty?
    puts "No #{display_name} inconsistencies found"
  else
    puts "## #{display_name} inconsistencies:"
    puts inconsistencies.join("\n")
  end
end

def os
  case RUBY_PLATFORM
  when /linux/
    'linux'
  when /darwin/
    'mac_os'
  when /x64-mingw32/
    'windows'
  else
    raise 'Unsupported OS'
  end
end

desc 'Outputs the checks/example configs of this repo that do not match the ones in `dd-agent` (temporary task)'
task dd_agent_consistency: [:pull_latest_agent] do
  print_inconsistencies(
    'check file',
    find_inconsistencies(find_check_files, 'checks.d')
  )
  print_inconsistencies(
    'yaml example file',
    find_inconsistencies(find_yaml_confs, 'conf.d')
  )
end

desc 'Copy checks and configuration files over the given paths, optionally merging requirements files into one'
task :copy_checks do
  conf_dir = ENV['conf_dir']
  raise "please specify 'conf_dir' param" if conf_dir.to_s.empty?
  mkdir_p File.join(conf_dir, 'auto_conf')

  checks_dir = ENV['checks_dir']
  raise "please specify 'checks_dir' param" if checks_dir.to_s.empty?
  mkdir_p checks_dir

  all_reqs_file = nil

  merge_to = ENV['merge_requirements_to']
  unless merge_to.to_s.empty?
    all_reqs_file = File.open(File.join(merge_to, 'check_requirements.txt'), 'w+')
  end

  Dir.glob('*/').each do |check|
    check.slice! '/'

    # Check the manifest to be sure that this check is enabled on this system
    # or skip this iteration
    manifest_file_path = "#{check}/manifest.json"

    # If there is no manifest file, then we should assume the folder does not
    # contain a working check and move onto the next
    File.exist?(manifest_file_path) || next

    manifest = JSON.parse(File.read(manifest_file_path))
    manifest['supported_os'].include?(os) || next

    # Copy the checks over
    if File.exist? "#{check}/check.py"
      copy "#{check}/check.py", "#{checks_dir}/#{check}.py"
    end

    # Copy the check config to the conf directories
    if File.exist? "#{check}/conf.yaml.example"
      copy "#{check}/conf.yaml.example", "#{conf_dir}/#{check}.yaml.example"
    end

    # Copy the default config, if it exists
    if File.exist? "#{check}/conf.yaml.default"
      copy "#{check}/conf.yaml.default", "#{conf_dir}/#{check}.yaml.default"
    end

    # We don't have auto_conf on windows yet
    if os != 'windows'
      if File.exist? "#{check}/auto_conf.yaml"
        copy "#{check}/auto_conf.yaml", "#{conf_dir}/auto_conf/#{check}.yaml"
      end
    end

    next unless all_reqs_file && File.exist?("#{check}/requirements.txt") && !manifest['use_omnibus_reqs']

    reqs = File.open("#{check}/requirements.txt", 'r').read
    reqs.each_line do |line|
      all_reqs_file.puts line if line[0] != '#'
    end
  end

  all_reqs_file.close if all_reqs_file
end
