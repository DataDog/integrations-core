require 'ci/common'

def cassandra_check_version
  ENV['FLAVOR_VERSION'] || '2.1.14' # '2.0.17'
end

def cassandra_check_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/cassandra_check_#{cassandra_check_version}"
end

container_name = 'dd-test-cassandra'
container_name2 = 'dd-test-cassandra2'

namespace :ci do
  namespace :cassandra_check do |flavor|
    task before_install: ['ci:common:before_install'] do
      sh %(docker kill #{container_name} 2>/dev/null || true)
      sh %(docker rm #{container_name} 2>/dev/null || true)
      sh %(docker kill #{container_name2} 2>/dev/null || true)
      sh %(docker rm #{container_name2} 2>/dev/null || true)
    end

    task :install do
      Rake::Task['ci:common:install'].invoke('cassandra_check')
      sh %(docker create --expose 9042 --expose 7000 --expose 7001 --expose 9160 \
            -p 9042:9042 -p 7000:7000 -p 7001:7001 -p 9160:9160 --name #{container_name} cassandra:#{cassandra_check_version})
      sh %(docker start #{container_name})
      sh %(docker create --name #{container_name2} \
            -e CASSANDRA_SEEDS="$(docker inspect --format='{{ .NetworkSettings.IPAddress }}' #{container_name})" cassandra:#{cassandra_check_version})
      sh %(docker start #{container_name2})
    end

    task before_script: ['ci:common:before_script'] do
      # Wait.for container_port
      count = 0
      logs = `docker logs #{container_name} 2>&1`
      logs2 = `docker logs #{container_name2} 2>&1`
      puts 'Waiting for Cassandra to come up'
      until count == 20 || ((logs.include?('Listening for thrift clients') || logs.include?("Created default superuser role 'cassandra'")) && \
             (logs2.include?('Listening for thrift clients') || logs2.include?('Not starting RPC server as requested')))
        sleep_for 4
        logs = `docker logs #{container_name} 2>&1`
        logs2 = `docker logs #{container_name2} 2>&1`
        count += 1
      end
      if (logs.include?('Listening for thrift clients') || logs.include?("Created default superuser role 'cassandra'")) && \
         (logs2.include?('Listening for thrift clients') || logs2.include?('Not starting RPC server as requested'))
        puts 'Cassandra is up!'
      else
        puts 'Logs of container 1'
        sh %(docker logs #{container_name} 2>&1)
        puts 'Logs of container 2'
        sh %(docker logs #{container_name2} 2>&1)
        raise
      end
    end

    task script: ['ci:common:script'] do
      this_provides = [
        'cassandra_check'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task before_cache: ['ci:common:before_cache']

    task cleanup: ['ci:common:cleanup'] do
      sh %(docker kill #{container_name} 2>/dev/null || true)
      sh %(docker rm #{container_name} 2>/dev/null || true)
      sh %(docker kill #{container_name2} 2>/dev/null || true)
      sh %(docker rm #{container_name2} 2>/dev/null || true)
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
