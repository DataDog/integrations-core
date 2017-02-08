require 'ci/common'

def mongo_version
  ENV['FLAVOR_VERSION'] || '3.0.1'
end

def mongo_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/mongo_#{mongo_version}"
end

namespace :ci do
  namespace :mongo do |flavor|
    task before_install: ['ci:common:before_install']

    task install: ['ci:common:install'] do
      use_venv = in_venv
      install_requirements('mongo/requirements.txt',
                           "--cache-dir #{ENV['PIP_CACHE']}",
                           "#{ENV['VOLATILE_DIR']}/ci.log", use_venv)
      sh %(bash mongo/ci/start-docker.sh)
    end

    task before_script: ['ci:common:before_script'] do
      use_venv = in_venv
      install_requirements('mongo/requirements.txt',
                           "--cache-dir #{ENV['PIP_CACHE']}",
                           "#{ENV['VOLATILE_DIR']}/ci.log", use_venv)
    end

    task script: ['ci:common:script'] do
      this_provides = [
        'mongo'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task before_cache: ['ci:common:before_cache']

    # task cleanup: ['ci:common:cleanup']
    # sample cleanup task
    task cleanup: ['ci:common:cleanup'] do
      sh %(bash mongo/ci/stop-docker.sh)
    end

    task :execute do
      if ENV['FLAVOR_VERSION']
        flavor_versions = ENV['FLAVOR_VERSION'].split(',')
      else
        flavor_versions = [nil]
      end

      exception = nil
      begin
        %w(before_install install).each do |u|
          Rake::Task["#{flavor.scope.path}:#{u}"].invoke
        end
        flavor_versions.each do |flavor_version|
          ENV['FLAVOR_VERSION'] = flavor_version
          %w(install_infrastructure before_script).each do |u|
            Rake::Task["#{flavor.scope.path}:#{u}"].invoke
          end
          Rake::Task["#{flavor.scope.path}:script"].invoke
          Rake::Task["#{flavor.scope.path}:before_cache"].invoke
          Rake::Task["#{flavor.scope.path}:cleanup"].invoke
        end
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
