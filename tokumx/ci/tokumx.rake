require 'ci/common'

def tokumx_version
  ENV['FLAVOR_VERSION'] || '2.0.1'
end

def tokumx_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/tokumx_#{tokumx_version}"
end

namespace :ci do
  namespace :tokumx do |flavor|
    task before_install: ['ci:common:before_install']

    task install: ['ci:common:install'] do |t|
      use_venv = in_venv
      install_requirements('tokumx/requirements.txt',
                           "--cache-dir #{ENV['PIP_CACHE']}",
                           "#{ENV['VOLATILE_DIR']}/ci.log", use_venv)
      t.reenable
    end

    task :install_infrastructure do |t|
      sh %(bash tokumx/ci/start-docker.sh)
      t.reenable
    end

    task before_script: ['ci:common:before_script']

    task script: ['ci:common:script'] do |t, _attr|
      this_provides = [
        'tokumx'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
      t.reenable
    end

    task before_cache: ['ci:common:before_cache']

    task cleanup: ['ci:common:cleanup'] do |t|
      sh %(bash tokumx/ci/stop-docker.sh)
      t.reenable
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
          section("TESTING VERSION #{flavor_version}")
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
