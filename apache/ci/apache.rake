require 'ci/common'

def apache_version
  ENV['FLAVOR_VERSION'] || 'latest'
end

def apache_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/apache_#{apache_version}"
end

namespace :ci do
  namespace :apache do |flavor|
    task before_install: ['ci:common:before_install']

    task install: ['ci:common:install'] do
      use_venv = in_venv
      install_requirements('apache/requirements.txt',
                           "--cache-dir #{ENV['PIP_CACHE']}",
                           "#{ENV['VOLATILE_DIR']}/ci.log", use_venv)
      sh %(bash apache/ci/start-docker.sh)
      Wait.for 'http://localhost:8080', 15
    end

    task before_script: ['ci:common:before_script'] do
      100.times do
        sh %(curl --silent http://localhost:8080 > /dev/null)
      end
      sleep_for 2
    end

    task script: ['ci:common:script'] do
      this_provides = [
        'apache'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task before_cache: ['ci:common:before_cache']

    # sample cleanup task
    task cleanup: ['ci:common:cleanup'] do
      sh %(bash apache/ci/stop-docker.sh)
    end

    task :execute do
      exception = nil
      begin
        %w(before_install install before_script).each do |u|
          Rake::Task["#{flavor.scope.path}:#{u}"].invoke
        end
        Rake::Task["#{flavor.scope.path}:script"].invoke
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
