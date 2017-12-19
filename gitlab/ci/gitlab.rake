require 'ci/common'

def gitlab_version
  ENV['FLAVOR_VERSION'] || 'latest'
end

GITLAB_TEST_PASSWORD = 'testroot'.freeze
GITLAB_LOCAL_PORT = 8086
GITLAB_LOCAL_PROMETHEUS_PORT = 8088

GITLAB_COMPOSE_ARGS = "GITLAB_ROOT_PASSWORD=#{GITLAB_TEST_PASSWORD} GITLAB_VERSION=#{gitlab_version} " \
               "LOCAL_PROMETHEUS_PORT=#{GITLAB_LOCAL_PROMETHEUS_PORT} LOCAL_PORT=#{GITLAB_LOCAL_PORT}".freeze

namespace :ci do
  namespace :gitlab do |flavor|
    task before_install: ['ci:common:before_install'] do
      sh %(#{GITLAB_COMPOSE_ARGS} docker-compose -f gitlab/ci/docker-compose.yml down)
    end

    task :install do
      Rake::Task['ci:common:install'].invoke('gitlab')
      sh %(#{GITLAB_COMPOSE_ARGS} docker-compose -f gitlab/ci/docker-compose.yml up -d)
      Wait.for "http://localhost:#{GITLAB_LOCAL_PORT}", 900
      Wait.for "http://localhost:#{GITLAB_LOCAL_PROMETHEUS_PORT}", 900
    end

    task before_script: ['ci:common:before_script'] do
      100.times do
        `curl --silent http://localhost:#{GITLAB_LOCAL_PORT} > /dev/null`
      end
      sleep_for 2
    end

    task script: ['ci:common:script'] do
      this_provides = ['gitlab']
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task before_cache: ['ci:common:before_cache']

    # sample cleanup task
    task cleanup: ['ci:common:cleanup'] do
      sh %(#{GITLAB_COMPOSE_ARGS} docker-compose -f gitlab/ci/docker-compose.yml down)
    end

    task :execute do
      exception = nil
      begin
        %w(before_install install before_script).each do |u|
          Rake::Task["#{flavor.scope.path}:#{u}"].invoke
        end
        if !ENV['SKIP_TEST']
          Rake::Task["#{flavor.scope.path}:script"].invoke
        else
          puts 'Skipping tests'.yellow
        end
        Rake::Task["#{flavor.scope.path}:before_cache"].invoke
      rescue => e
        exception = e
        puts "Failed task: #{e.class} #{e.message}".red
      end
      if ENV['SKIP_CLEANUP']
        puts 'Skipping cleanup, disposable environments are great'.yellow
      else
        puts 'Cleaning up'
        Rake::Task["#{flavor.scope.path}:cleanup"].invoke
      end
      raise exception if exception
    end
  end
end
