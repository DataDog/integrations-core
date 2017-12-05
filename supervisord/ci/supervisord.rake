require 'ci/common'

def supervisord_version
  ENV['FLAVOR_VERSION'] || '3.3.3'
end

def supervisord_rootdir
  integrations_dir = ENV['INTEGRATIONS_DIR'] || 'embedded'
  "#{integrations_dir}/supervisord"
end

container_name = 'dd-test-supervisord'
container_port = 19_001

namespace :ci do
  namespace :supervisord do |flavor|
    task before_install: ['ci:common:before_install'] do
      sh %(rm -rf #{supervisord_rootdir} || true)
      sh %(mkdir -p #{supervisord_rootdir} || true)
      sh %(docker kill #{container_name} 2>/dev/null || true)
      sh %(docker rm #{container_name} 2>/dev/null || true)
    end

    task :install do
      Rake::Task['ci:common:install'].invoke('supervisord')
      sh %(docker run -d --name #{container_name} -p #{container_port}:#{container_port} \
           -v #{supervisord_rootdir}:/supervisor datadog/docker-library:supervisord_3_3_3)
    end

    task before_script: ['ci:common:before_script'] do
      # we need to make sure that supervisor is running an the rpc port is up
      Wait.for 19_001
    end

    task script: ['ci:common:script'] do
      this_provides = [
        'supervisord'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task before_cache: ['ci:common:before_cache']

    task cleanup: ['ci:common:cleanup'] do
      sh %(docker kill #{container_name} 2>/dev/null || true)
      sh %(docker rm #{container_name} 2>/dev/null || true)
      sh %(rm -rf #{supervisord_rootdir})
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
