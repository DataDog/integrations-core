require 'ci/common'

def riak_version
  ENV['FLAVOR_VERSION'] || 'latest'
end

def riak_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/riak_#{riak_version}"
end

container_name = 'dd-test-riak'
resources_path = (ENV['SDK_HOME']).to_s + '/riak/test/ci/resources'

namespace :ci do
  namespace :riak do |flavor|
    task before_install: ['ci:common:before_install'] do
      sh %(docker rm -f #{container_name} 2>/dev/null || true)
    end

    task :install do
      Rake::Task['ci:common:install'].invoke('riak')
      sh %(docker run -d --name #{container_name} -p 18098:8098 -v #{resources_path}:/etc/riak/ tutum/riak)
    end

    task before_script: ['ci:common:before_script'] do
      puts 'Waiting for Riak to come up'
      wait_on_docker_logs('dd-test-riak', 60, 'You can now use riak Server')
      sleep_for 20

      10.times do
        sh %(curl -XPUT -H 'Content-Type: text/plain' -d 'herzlich willkommen' http://localhost:18098/riak/bucket/german)
        sh %(curl http://localhost:18098/riak/bucket/german)
      end
    end

    task script: ['ci:common:script'] do
      this_provides = [
        'riak'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task before_cache: ['ci:common:before_cache']

    task cleanup: ['ci:common:cleanup'] do
      sh %(docker rm -f #{container_name} 2>/dev/null || true)
      sh %(find #{resources_path}/ ! -name 'app.config' ! -name 'riak.conf' -type f -exec rm -f {} +)
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
