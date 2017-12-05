require 'ci/common'

container_name = 'dd-test-snmp'
resources_path = (ENV['TRAVIS_BUILD_DIR']).to_s + '/snmp/ci/resources'

namespace :ci do
  namespace :snmp do |flavor|
    task before_install: ['ci:common:before_install'] do
      sh %(docker rm -f #{container_name} 2>/dev/null || true)
    end

    task :install do
      Rake::Task['ci:common:install'].invoke('snmp')
      sh %(docker run -d -v #{resources_path}:/etc/snmp/ --name #{container_name} -p 11111:161/udp polinux/snmpd -c /etc/snmp/snmpd.conf)
      sleep_for 5
    end

    task before_script: ['ci:common:before_script']

    task script: ['ci:common:script'] do
      this_provides = [
        'snmp'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task before_cache: ['ci:common:before_cache']

    task cleanup: ['ci:common:cleanup'] do
      sh %(docker rm -f #{container_name})
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
