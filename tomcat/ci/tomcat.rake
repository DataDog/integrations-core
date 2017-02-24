require 'ci/common'

def tomcat_version
  ENV['FLAVOR_VERSION'] || 'latest'
end

def tomcat_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/tomcat_#{tomcat_version}"
end

container_name = 'dd-test-tomcat'
container_port = 8090
java_opts = "-Dcom.sun.management.jmxremote
  -Dcom.sun.management.jmxremote.port=#{container_port}
  -Dcom.sun.management.jmxremote.rmi.port=#{container_port}
  -Dcom.sun.management.jmxremote.authenticate=false
  -Dcom.sun.management.jmxremote.ssl=false"

namespace :ci do
  namespace :tomcat do |flavor|
    task before_install: ['ci:common:before_install']

    task install: ['ci:common:install'] do |t|
      use_venv = in_venv
      install_requirements('tomcat/requirements.txt',
                           "--cache-dir #{ENV['PIP_CACHE']}",
                           "#{ENV['VOLATILE_DIR']}/ci.log", use_venv)
      t.reenable
    end

    task :install_infrastructure do |t|
      sh %(docker run -d -p #{container_port}:8090 --name #{container_name} -e JAVA_OPTS='#{java_opts}' tomcat:6.0.43)
      t.reenable
    end

    task before_script: ['ci:common:before_script'] do |t|
      count = 0
      logs = `docker logs #{container_name} 2>&1`
      puts 'Waiting for Tomcat to come up'
      until count == 20 || logs.include?('INFO: Server startup')
        sleep_for 2
        logs = `docker logs #{container_name} 2>&1`
        count += 1
      end
      if logs.include? 'INFO: Server startup'
        puts 'Tomcat is up!'
      else
        sh %(docker logs #{container_name} 2>&1)
        raise
      end
      t.reenable
    end

    task script: ['ci:common:script'] do |t|
      this_provides = [
        'tomcat'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
      t.reenable
    end

    task before_cache: ['ci:common:before_cache']

    task cleanup: ['ci:common:cleanup'] do |t|
      `docker rm -f #{container_name}`
      t.reenable
    end

    task :execute do
      flavor_versions = if ENV['FLAVOR_VERSION']
                          ENV['FLAVOR_VERSION'].split(',')
                        else
                          [nil]
                        end

      exception = nil
      begin
        %w(before_install install).each do |u|
          Rake::Task["#{flavor.scope.path}:#{u}"].invoke
        end
        flavor_versions.each do |flavor_version|
          section("TESTING VERSION #{flavor_version}")
          ENV['FLAVOR_VERSION'] = flavor_version
          %w(install_infrastructure before_script).each do |u|
            Rake::Task["#{flavor.scope.path}:#{u}"].invoke
          end
          Rake::Task["#{flavor.scope.path}:script"].invoke
          Rake::Task["#{flavor.scope.path}:before_cache"].invoke
          Rake::Task["#{flavor.scope.path}:cleanup"].invoke
        end
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
