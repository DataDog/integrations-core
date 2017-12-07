require 'ci/common'

def powerdns_recursor_version
  ENV['FLAVOR_VERSION'] || '3.7.3'
end

def powerdns_recursor_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/powerdns_recursor_#{powerdns_recursor_version}"
end

container_name = 'dd-test-powerdns-recursor'
container_port1 = 8082
container_port2 = 5353

namespace :ci do
  namespace :powerdns_recursor do |flavor|
    task before_install: ['ci:common:before_install'] do
      sh %(docker kill #{container_name} 2>/dev/null || true)
      sh %(docker rm #{container_name} 2>/dev/null || true)
    end

    task :install do
      Rake::Task['ci:common:install'].invoke('powerdns_recursor')
      pdns_tag = 'powerdns_recursor_' + powerdns_recursor_version.tr('.', '_')
      sh %(docker run -d --expose #{container_port2} --expose #{container_port1}/udp \
           -p #{container_port1}:#{container_port1} -p #{container_port2}:#{container_port2}/udp \
           --name #{container_name} datadog/docker-library:#{pdns_tag})
      Wait.for 8082, 5
    end

    task before_script: ['ci:common:before_script']

    task script: ['ci:common:script'] do
      this_provides = [
        'powerdns_recursor'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task before_cache: ['ci:common:before_cache']

    # sample cleanup task
    task cleanup: ['ci:common:cleanup'] do
      sh %(docker kill #{container_name} 2>/dev/null || true)
      sh %(docker rm #{container_name} 2>/dev/null || true)
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
