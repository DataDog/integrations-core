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
