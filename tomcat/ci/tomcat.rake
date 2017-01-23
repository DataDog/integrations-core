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

    task install: ['ci:common:install'] do
      use_venv = in_venv
      install_requirements('tomcat/requirements.txt',
                           "--cache-dir #{ENV['PIP_CACHE']}",
                           "#{ENV['VOLATILE_DIR']}/ci.log", use_venv)
      sh %(docker run -d -p #{container_port}:8090 --name #{container_name} -e JAVA_OPTS='#{java_opts}' tomcat:6.0.43)
    end

    task before_script: ['ci:common:before_script'] do
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
    end

    task script: ['ci:common:script'] do
      this_provides = [
        'tomcat'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task before_cache: ['ci:common:before_cache']

    task cleanup: ['ci:common:cleanup'] do
      `docker rm -f #{container_name}`
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
