require 'ci/common'

def gearmand_version
  ENV['FLAVOR_VERSION'] || 'latest'
end

def gearmand_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/gearmand_#{gearmand_version}"
end

container_name = 'dd-test-gearmand'
container_port = 15_440

namespace :ci do
  namespace :gearmand do |flavor|
    task before_install: ['ci:common:before_install']

    task :install do
      Rake::Task['ci:common:install'].invoke('gearmand')
      sh %(docker run -d -p #{container_port}:4730 --name #{container_name} kendu/gearman)
    end

    task before_script: ['ci:common:before_script']

    task script: ['ci:common:script'] do
      this_provides = [
        'gearmand'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task before_cache: ['ci:common:before_cache']

    task cleanup: ['ci:common:cleanup'] do
      `docker kill $(docker ps -q --filter name=dd-test-gearmand) || true`
      `docker rm $(docker ps -aq --filter name=dd-test-gearmand) || true`
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
