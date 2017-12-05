require 'ci/common'

def kong_version
  ENV['FLAVOR_VERSION'] || '0.9.0'
end

def kong_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/kong_#{kong_version}"
end

container_name = 'dd-test-kong'
container_name_db = "#{container_name}-database"
container_port1 = 8000
container_port2 = 8443
container_port3 = 8001
container_port4 = 7946

namespace :ci do
  namespace :kong do |flavor|
    task before_install: ['ci:common:before_install'] do
      sh %(docker kill #{container_name} #{container_name_db} 2>/dev/null || true)
      sh %(docker rm #{container_name} #{container_name_db} 2>/dev/null || true)
    end

    task :install do
      Rake::Task['ci:common:install'].invoke('kong')
      sh %(docker run -d --name #{container_name_db} -p 9042:9042 cassandra:2.2)

      wait_on_docker_logs(container_name_db, 40, 'Listening for thrift clients', "Created default superuser role 'cassandra'")

      sh %(docker run -d --name #{container_name} --link #{container_name_db}:kong-database \
        -e "KONG_DATABASE=cassandra" -e "KONG_CASSANDRA_CONTACT_POINTS=#{container_name_db}" -e "KONG_PG_HOST=#{container_name_db}" \
        -p #{container_port1}:#{container_port1} -p #{container_port2}:#{container_port2}  -p #{container_port3}:#{container_port3} \
        -p #{container_port4}:#{container_port4}  -p 7946:7946/udp kong:#{kong_version})
      Wait.for 'http://localhost:8001/status', 100
    end

    task before_script: ['ci:common:before_script']

    task script: ['ci:common:script'] do
      this_provides = [
        'kong'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task before_cache: ['ci:common:before_cache']

    task cleanup: ['ci:common:cleanup'] do
      sh %(docker kill #{container_name} #{container_name_db} 2>/dev/null || true)
      sh %(docker rm #{container_name} #{container_name_db} 2>/dev/null || true)
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
