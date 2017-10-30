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

    task :install do
      Rake::Task['ci:common:install'].invoke('tokumx')
      sh %(bash #{'SDK_HOME'}/tokumx/ci/start-docker.sh)
    end

    task before_script: ['ci:common:before_script']

    task script: ['ci:common:script'] do |_, _attr|
      this_provides = [
        'tokumx'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task before_cache: ['ci:common:before_cache']

    task cleanup: ['ci:common:cleanup'] do
      sh %(bash #{'SDK_HOME'}/tokumx/ci/stop-docker.sh)
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
