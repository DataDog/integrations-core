require 'ci/common'

def pdh_check_version
  ENV['FLAVOR_VERSION'] || 'latest'
end

def pdh_check_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/exchange_check_#{pdh_check_version}"
end

namespace :ci do
  namespace :pdh_check do |flavor|
    task before_install: ['ci:common:before_install']

    task :install do
      Rake::Task['ci:common:install'].invoke('exchange_check')
      # sample docker usage
      # sh %(docker create -p XXX:YYY --name pdh_check source/pdh_check:pdh_check_version)
      # sh %(docker start pdh_check)
    end

    task before_script: ['ci:common:before_script']

    task script: ['ci:common:script'] do
      this_provides = [
        'exchange_check'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task before_cache: ['ci:common:before_cache']

    task cleanup: ['ci:common:cleanup']
    # sample cleanup task
    # task cleanup: ['ci:common:cleanup'] do
    #   sh %(docker stop pdh_check)
    #   sh %(docker rm pdh_check)
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
