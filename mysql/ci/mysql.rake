require 'ci/common'

def mysql_version
  ENV['FLAVOR_VERSION'] || 'latest'
end

def mysql_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/mysql_#{mysql_version}"
end

container_name = 'dd-test-mysql'
container_port = 13_306

namespace :ci do
  namespace :mysql do |flavor|
    task before_install: ['ci:common:before_install'] do
      `docker kill $(docker ps -q --filter name=dd-test-mysql) || true`
      `docker rm $(docker ps -aq --filter name=dd-test-mysql) || true`
    end

    task :install do
      Rake::Task['ci:common:install'].invoke('mysql')
      sh %(docker run -p #{container_port}:3306 --name #{container_name} -e MYSQL_ROOT_PASSWORD=datadog -d mysql:5.7)
    end

    task before_script: ['ci:common:before_script'] do
      Wait.for 13_306
      count = 0
      logs = `docker logs dd-test-mysql 2>&1`
      puts 'Waiting for MySQL to come up'
      until count == 20 || logs.include?('MySQL init process done. Ready for start up')
        sleep_for 2
        logs = `docker logs dd-test-mysql 2>&1`
        count += 1
      end
      if logs.include? 'MySQL init process done. Ready for start up'
        puts 'MySQL is up!'
      end

      sh %(docker run -it --link dd-test-mysql:mysql --rm mysql:5.7 \
           sh -c 'exec mysql -h"$MYSQL_PORT_3306_TCP_ADDR" -P"MYSQL_PORT_3306_TCP_PORT" -uroot -p"$MYSQL_ENV_MYSQL_ROOT_PASSWORD" \
           -e "create user \\"dog\\"@\\"%\\" identified by \\"dog\\"; \
           GRANT PROCESS, REPLICATION CLIENT ON *.* TO \\"dog\\"@\\"%\\" WITH MAX_USER_CONNECTIONS 5; \
           CREATE DATABASE testdb; \
           CREATE TABLE testdb.users (name VARCHAR(20), age INT); \
           GRANT SELECT ON testdb.users TO \\"dog\\"@\\"%\\"; \
           INSERT INTO testdb.users (name,age) VALUES(\\"Alice\\",25); \
           INSERT INTO testdb.users (name,age) VALUES(\\"Bob\\",20); \
           GRANT SELECT ON performance_schema.* TO \\"dog\\"@\\"%\\"; \
           USE testdb; \
           SELECT * FROM users ORDER BY name; "')
    end

    task script: ['ci:common:script'] do
      this_provides = [
        'mysql'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task before_cache: ['ci:common:before_cache']

    task cleanup: ['ci:common:cleanup'] do
      `docker kill $(docker ps -q --filter name=dd-test-mysql) || true`
      `docker rm $(docker ps -aq --filter name=dd-test-mysql) || true`
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
