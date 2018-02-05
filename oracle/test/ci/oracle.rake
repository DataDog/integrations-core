require 'ci/common'

def oracle_version
  ENV['FLAVOR_VERSION'] || 'latest'
end

def oracle_repo
  'sath89/oracle-12c'
end

def oracle_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/oracle_#{oracle_version}"
end

def oracle_volume
  "#{ENV['ORACLE_DIR']}/data"
end

container_name = 'dd-test-oracle'
container_port = 1_521
container_port_8080 = 80_80

namespace :ci do
  namespace :oracle do |flavor|
    task before_install: ['ci:common:before_install'] do
      sh %(mkdir -p #{ENV['ORACLE_DIR']})
      sh %(#{ENV['SDK_HOME']}/oracle/test/ci/resources/get_instantclient.py --agree=yes)
      sh %(echo #{ENV['ORACLE_HOME']} | sudo tee /etc/ld.so.conf.d/oracle_instantclient.conf)
      sh %(sudo ldconfig)
      unless File.exist?("#{ENV['ORACLE_HOME']}/libclntsh.so")
        sh %(ln -s #{ENV['ORACLE_HOME']}/libclntsh.so.12.1 #{ENV['ORACLE_HOME']}/libclntsh.so)
      end
      `docker kill $(docker ps -q --filter name=#{container_name}) || true`
      `docker rm $(docker ps -aq --filter name=#{container_name}) || true`
    end

    task install: ['ci:common:install'] do
      use_venv = in_venv
      install_requirements('oracle/requirements.txt',
                           "--cache-dir #{ENV['PIP_CACHE']}",
                           "#{ENV['VOLATILE_DIR']}/ci.log", use_venv)
      sh %(mkdir -p #{oracle_volume})
      sh %(docker run  --shm-size=1024MB -p #{container_port}:1521 -p #{container_port_8080}:8080 \
           --name #{container_name} -v #{__dir__}/resources:/docker-entrypoint-initdb.d -v #{oracle_volume}:/u01/app/oracle \
           -e WEB_CONSOLE=false -d #{oracle_repo}:#{oracle_version})
    end

    task before_script: ['ci:common:before_script'] do
      Wait.for container_port
      Wait.for container_port_8080
      # it can be a loooong wait (600s TO)...
      wait_on_docker_logs(container_name, 600, 'Database ready to use')
    end

    task script: ['ci:common:script'] do
      this_provides = [
        'oracle'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task before_cache: ['ci:common:before_cache']

    task cleanup: ['ci:common:cleanup'] do
      `docker kill $(docker ps -q --filter name=#{container_name}) || true`
      `docker rm $(docker ps -aq --filter name=#{container_name}) || true`
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
