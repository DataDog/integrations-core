require 'ci/common'

def cassandra_nodetool_version
  ENV['FLAVOR_VERSION'] || '2.1.14' # '2.0.17'
end

container_name = 'dd-test-cassandra'
container_name2 = 'dd-test-cassandra2'

container_port = 7199
cassandra_jmx_options = "-Dcom.sun.management.jmxremote.port=#{container_port}
  -Dcom.sun.management.jmxremote.rmi.port=#{container_port}
  -Dcom.sun.management.jmxremote.ssl=false
  -Dcom.sun.management.jmxremote.authenticate=true
  -Dcom.sun.management.jmxremote.password.file=/etc/cassandra/jmxremote.password
  -Djava.rmi.server.hostname=localhost"

namespace :ci do
  namespace :cassandra_nodetool do |flavor|
    task before_install: ['ci:common:before_install'] do
      sh %(docker kill #{container_name} 2>/dev/null || true)
      sh %(docker rm #{container_name} 2>/dev/null || true)
      sh %(docker kill #{container_name2} 2>/dev/null || true)
      sh %(docker rm #{container_name2} 2>/dev/null || true)
      sh %(rm -f #{__dir__}/jmxremote.password.tmp)
    end

    task :install do
      Rake::Task['ci:common:install'].invoke('cassandra_nodetool')
      sh %(docker create --expose #{container_port} \
            -p #{container_port}:#{container_port} -e JMX_PORT=#{container_port} \
            -e LOCAL_JMX=no -e JVM_EXTRA_OPTS="#{cassandra_jmx_options}" --name #{container_name} cassandra:#{cassandra_nodetool_version})
      sh %(cp #{__dir__}/jmxremote.password #{__dir__}/jmxremote.password.tmp)
      sh %(chmod 400 #{__dir__}/jmxremote.password.tmp)
      sh %(docker cp #{__dir__}/jmxremote.password.tmp #{container_name}:/etc/cassandra/jmxremote.password)
      sh %(rm -f #{__dir__}/jmxremote.password.tmp)
      sh %(docker start #{container_name})

      sh %(docker create --name #{container_name2} \
            -e CASSANDRA_SEEDS="$(docker inspect --format='{{ .NetworkSettings.IPAddress }}' #{container_name})" \
            cassandra:#{cassandra_nodetool_version})
      sh %(docker start #{container_name2})
    end

    task before_script: ['ci:common:before_script'] do
      # Wait.for container_port
      wait_on_docker_logs(container_name, 20, 'Listening for thrift clients', "Created default superuser role 'cassandra'")
      wait_on_docker_logs(container_name2, 40, 'Listening for thrift clients', 'Not starting RPC server as requested')
      sh %(docker exec #{container_name} cqlsh -e "CREATE KEYSPACE test WITH REPLICATION={'class':'SimpleStrategy', 'replication_factor':2}")
    end

    task script: ['ci:common:script'] do
      this_provides = [
        'cassandra_nodetool'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task before_cache: ['ci:common:before_cache']

    task cleanup: ['ci:common:cleanup'] do
      sh %(docker kill #{container_name} 2>/dev/null || true)
      sh %(docker rm #{container_name} 2>/dev/null || true)
      sh %(docker kill #{container_name2} 2>/dev/null || true)
      sh %(docker rm #{container_name2} 2>/dev/null || true)
      sh %(rm -f #{__dir__}/jmxremote.password.tmp)
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
