require 'ci/common'

def mysql_version
  ENV['FLAVOR_VERSION'] || 'latest'
end

def mysql_flavor
  ENV['MYSQL_FLAVOR'] || 'mysql'
end

def mysql_repo
  if mysql_flavor == 'mysql'
    if mysql_version == '5.5'
      'jfullaondo/mysql-replication'
    else
      'bergerx/mysql-replication'
    end
  elsif mysql_flavor == 'mariadb'
    'bitnami/mariadb'
  end
end

def mysql_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/mysql_#{mysql_version}"
end

container_name = 'dd-test-mysql'
container_port = 13_306
slave_container_port = 13_307

namespace :ci do
  namespace :mysql do |flavor|
    task before_install: ['ci:common:before_install'] do
      `docker kill $(docker ps -q --filter name=#{container_name}_slave) || true`
      `docker rm $(docker ps -aq --filter name=#{container_name}_slave) || true`
      `docker kill $(docker ps -q --filter name=#{container_name}_master) || true`
      `docker rm $(docker ps -aq --filter name=#{container_name}_master) || true`
    end

    task :install do
      Rake::Task['ci:common:install'].invoke('mysql')
      if mysql_flavor == 'mariadb'
        sh %(docker run -p #{container_port}:3306 --name #{container_name}_master \
	     -e MARIADB_ROOT_PASSWORD=master_root_password \
             -e MARIADB_REPLICATION_MODE=master \
             -e MARIADB_REPLICATION_USER=my_repl_user \
             -e MARIADB_REPLICATION_PASSWORD=my_repl_password \
             -e MARIADB_USER=my_user \
             -e MARIADB_PASSWORD=my_password \
             -e MARIADB_DATABASE=my_database -d #{mysql_repo}:#{mysql_version})
      else
        sh %(docker run -p #{container_port}:3306 --name #{container_name}_master \
             -e MYSQL_ALLOW_EMPTY_PASSWORD=1 -d #{mysql_repo}:#{mysql_version})
      end
    end

    task before_script: ['ci:common:before_script'] do
      Wait.for container_port
      count = 0
      logs = `docker logs #{container_name}_master 2>&1`
      puts 'Waiting for MySQL to come up'
      if mysql_flavor == 'mariadb'
        expect_log = 'mariadb successfully initialized'
        expect_log_up = 'Starting mysqld daemon with databases'
      else
        expect_log = 'MySQL init process done. Ready for start up'
        expect_log_up = 'MySQL init process done. Ready for start up'
      end

      until count == 20 || logs.include?(expect_log)
        sleep_for 2
        logs = `docker logs #{container_name}_master 2>&1`
        count += 1
      end
      raise 'Master not up in time. Failing...' unless logs.include? expect_log_up
      puts 'MySQL is up!'

      if mysql_flavor == 'mariadb'
        sh %(docker run -p #{slave_container_port}:3306 --name #{container_name}_slave \
             -e MYSQL_ALLOW_EMPTY_PASSWORD=1 --link #{container_name}_master:master \
	     -e MARIADB_REPLICATION_MODE=slave \
             -e MARIADB_REPLICATION_USER=my_repl_user \
             -e MARIADB_REPLICATION_PASSWORD=my_repl_password \
             -e MARIADB_MASTER_HOST=master \
             -e MARIADB_MASTER_ROOT_PASSWORD=master_root_password -d #{mysql_repo}:#{mysql_version})
      else
        sh %(docker run -p #{slave_container_port}:3306 --name #{container_name}_slave \
             -e MYSQL_ALLOW_EMPTY_PASSWORD=1 --link #{container_name}_master:master \
             -d #{mysql_repo}:#{mysql_version})
      end
      Wait.for slave_container_port
      count = 0
      logs = `docker logs #{container_name}_slave 2>&1`
      puts 'Waiting for MySQL to come up'

      until count == 20 || logs.include?(expect_log)
        sleep_for 2
        logs = `docker logs #{container_name}_slave 2>&1`
        count += 1
      end
      raise 'Slave not up in time. Failing...' unless logs.include? expect_log_up
      puts 'MySQL is up!'

      opts = ''
      cli_version = mysql_version
      if mysql_flavor == 'mariadb'
        opts = '--password=master_root_password'
        cli_version = 'latest'
      end
      sh %(docker run -it --link #{container_name}_master:mysql --rm mysql:#{cli_version} \
           sh -c 'exec mysql -h\"$MYSQL_PORT_3306_TCP_ADDR\" -P\"MYSQL_PORT_3306_TCP_PORT\" -uroot \
           #{opts} -e \"create user \\"dog\\"@\\"%\\" identified by \\"dog\\"; \
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
      `docker kill $(docker ps -q --filter name=#{container_name}_slave) || true`
      `docker rm $(docker ps -aq --filter name=#{container_name}_slave) || true`
      `docker kill $(docker ps -q --filter name=#{container_name}_master) || true`
      `docker rm $(docker ps -aq --filter name=#{container_name}_master) || true`
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
