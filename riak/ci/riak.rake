require 'ci/common'

def riak_version
  ENV['FLAVOR_VERSION'] || 'latest'
end

def riak_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/riak_#{riak_version}"
end

container_name = 'dd-test-riak'
resources_path = (ENV['TRAVIS_BUILD_DIR']).to_s + '/riak/ci/resources'

namespace :ci do
  namespace :riak do |flavor|
    task before_install: ['ci:common:before_install'] do
      sh %(docker rm -f #{container_name} 2>/dev/null || true)
    end

    task install: ['ci:common:install'] do
      use_venv = in_venv
      install_requirements('riak/requirements.txt',
                           "--cache-dir #{ENV['PIP_CACHE']}",
                           "#{ENV['VOLATILE_DIR']}/ci.log", use_venv)
      sh %(docker run -d --name #{container_name} -p 18098:8098 -v #{resources_path}:/etc/riak/ tutum/riak)
    end

    task before_script: ['ci:common:before_script'] do
      count = 0
      logs = `docker logs #{container_name} 2>&1`
      puts 'Waiting for Riak to come up'
      until count == 20 || logs.include?('INFO success: riak entered RUNNING state')
        sleep_for 2
        logs = `docker logs #{container_name} 2>&1`
        count += 1
      end
      if logs.include? 'INFO success: riak entered RUNNING state'
        puts 'Riak is up!'
      else
        sh %(docker logs #{container_name} 2>&1)
        raise
      end
      sleep_for 10
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
