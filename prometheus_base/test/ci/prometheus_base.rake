require 'ci/common'

def prometheus_base_version
  ENV['FLAVOR_VERSION'] || 'latest'
end

def prometheus_base_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/prometheus_base_#{prometheus_base_version}"
end

namespace :ci do
  namespace :prometheus_base do |flavor|
    task before_install: ['ci:common:before_install']

    task :install do
      Rake::Task['ci:common:install'].invoke('prometheus_base')
      # sample docker usage
      # sh %(docker create -p XXX:YYY --name prometheus_base source/prometheus_base:prometheus_base_version)
      # sh %(docker start prometheus_base)
    end

    task before_script: ['ci:common:before_script']

    task script: ['ci:common:script'] do
      this_provides = [
        'prometheus_base'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task before_cache: ['ci:common:before_cache']

    task cleanup: ['ci:common:cleanup']
    # sample cleanup task
    # task cleanup: ['ci:common:cleanup'] do
    #   sh %(docker stop prometheus_base)
    #   sh %(docker rm prometheus_base)
    # end

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
