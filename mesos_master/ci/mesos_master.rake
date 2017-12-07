require 'ci/common'

def mesos_master_version
  ENV['FLAVOR_VERSION'] || '1.0.1'
end

def mesos_master_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/mesos_master_#{mesos_master_version}"
end

namespace :ci do
  namespace :mesos_master do |flavor|
    task before_install: ['ci:common:before_install'] do
    end

    task :install do
      Rake::Task['ci:common:install'].invoke('mesos_master')
    end

    task before_script: ['ci:common:before_script'] do
    end

    task script: ['ci:common:script'] do
      this_provides = [
        'mesos_master'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task before_cache: ['ci:common:before_cache']

    task cleanup: ['ci:common:cleanup'] do
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
