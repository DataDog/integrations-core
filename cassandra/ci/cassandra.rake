require 'ci/common'

def cassandra_version
  ENV['FLAVOR_VERSION'] || '2.1.14' # '2.0.17'
end

def cassandra_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/cassandra_#{cassandra_version}"
end

container_name = 'dd-test-cassandra'
container_port = 7199
cassandra_jmx_options = "-Dcom.sun.management.jmxremote.port=#{container_port}
  -Dcom.sun.management.jmxremote.rmi.port=#{container_port}
  -Dcom.sun.management.jmxremote.ssl=false
  -Dcom.sun.management.jmxremote.authenticate=true
  -Dcom.sun.management.jmxremote.password.file=/etc/cassandra/jmxremote.password
  -Djava.rmi.server.hostname=localhost"

namespace :ci do
  namespace :cassandra do |flavor|
    task before_install: ['ci:common:before_install'] do
      sh %(docker kill #{container_name} 2>/dev/null || true)
      sh %(docker rm #{container_name} 2>/dev/null || true)
      sh %(rm -f #{__dir__}/jmxremote.password.tmp)
    end

    task install: ['ci:common:install'] do
      use_venv = in_venv
      install_requirements('cassandra/requirements.txt',
                           "--cache-dir #{ENV['PIP_CACHE']}",
                           "#{ENV['VOLATILE_DIR']}/ci.log", use_venv)
      sh %(docker create --expose #{container_port} --expose 9042 --expose 7000 --expose 7001 --expose 9160 -p #{container_port}:#{container_port} -p 9042:9042 -p 7000:7000 -p 7001:7001 -p 9160:9160 -e JMX_PORT=#{container_port} -e LOCAL_JMX='no' -e JVM_EXTRA_OPTS="#{cassandra_jmx_options}" --name #{container_name} cassandra:#{cassandra_version})

      sh %(cp #{__dir__}/jmxremote.password #{__dir__}/jmxremote.password.tmp)
      sh %(chmod 400 #{__dir__}/jmxremote.password.tmp)
      sh %(docker cp #{__dir__}/jmxremote.password.tmp #{container_name}:/etc/cassandra/jmxremote.password)
      sh %(rm -f #{__dir__}/jmxremote.password.tmp)
      sh %(docker start #{container_name})
      # sh %(bash #{__dir__}/start-docker.sh)
    end

    task before_script: ['ci:common:before_script'] do
      # Wait.for container_port
      count = 0
      logs = `docker logs #{container_name} 2>&1`
      puts "Waiting for Cassandra to come up"
      until count == 20 or logs.include? "Listening for thrift clients" or logs.include? "Created default superuser role 'cassandra'"
        sleep_for 2
        logs = `docker logs #{container_name} 2>&1`
        count += 1
      end
      if logs.include? "Listening for thrift clients" or logs.include? "Created default superuser role 'cassandra'"
        puts "Cassandra is up!"
      else
        sh %(docker logs #{container_name} 2>&1)
        raise
      end
    end

    task script: ['ci:common:script'] do
      this_provides = [
        'cassandra'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task before_cache: ['ci:common:before_cache']

    task cleanup: ['ci:common:cleanup'] do
      sh %(docker kill #{container_name} 2>/dev/null || true)
      sh %(docker rm #{container_name} 2>/dev/null || true)
      sh %(rm -f #{__dir__}/jmxremote.password.tmp)
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
