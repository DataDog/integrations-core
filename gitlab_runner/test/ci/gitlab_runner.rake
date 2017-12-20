require 'ci/common'

def gitlab_master_version
  ENV['MASTER_FLAVOR_VERSION'] || 'latest'
end

def gitlab_runner_version
  ENV['RUNNER_FLAVOR_VERSION'] || 'latest'
end

# Test token shared between Gitlab and Runner for automatic registration
TEST_TOKEN = 'ddtesttoken'.freeze
LOCAL_MASTER_PORT = 8085
LOCAL_RUNNER_PORT = 8087

COMPOSE_ARGS = "GITLAB_VERSION=#{gitlab_master_version} GITLAB_RUNNER_VERSION=#{gitlab_runner_version} " \
               "TEST_TOKEN=#{TEST_TOKEN} LOCAL_RUNNER_PORT=#{LOCAL_RUNNER_PORT} LOCAL_MASTER_PORT=#{LOCAL_MASTER_PORT}".freeze

namespace :ci do
  namespace :gitlab_runner do |flavor|
    task before_install: ['ci:common:before_install'] do
      sh %(#{COMPOSE_ARGS} docker-compose -f #{ENV['TRAVIS_BUILD_DIR']}/gitlab_runner/test/ci/resources/docker-compose.yml down)
    end

    task :install do
      Rake::Task['ci:common:install'].invoke('gitlab_runner')
      # Gitlab master, to have a proper runner registration
      sh %(#{COMPOSE_ARGS} docker-compose -f #{ENV['TRAVIS_BUILD_DIR']}/gitlab_runner/test/ci/resources/docker-compose.yml up -d)

      # The runner already waits for the master to be up before registering
      # Here we make sure that the runner itself is actually up and running
      Wait.for "http://localhost:#{LOCAL_RUNNER_PORT}/metrics", 900
    end

    task before_script: ['ci:common:before_script'] do
      100.times do
        `curl --silent http://localhost:#{LOCAL_RUNNER_PORT} > /dev/null`
      end
      sleep_for 2
    end

    task script: ['ci:common:script'] do
      this_provides = [
        'gitlab_runner'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task before_cache: ['ci:common:before_cache']

    # sample cleanup task
    task cleanup: ['ci:common:cleanup'] do
      sh %(#{COMPOSE_ARGS} docker-compose -f #{ENV['TRAVIS_BUILD_DIR']}/gitlab_runner/test/ci/resources/docker-compose.yml down)
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
