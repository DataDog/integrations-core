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
    task before_install: ['ci:common:before_install'] do |t|
      sh %(docker kill #{container_name} 2>/dev/null || true)
      sh %(docker rm #{container_name} 2>/dev/null || true)
      t.reenable
    end

    task install: ['ci:common:install'] do |t|
      use_venv = in_venv
      install_requirements('powerdns_recursor/requirements.txt',
                           "--cache-dir #{ENV['PIP_CACHE']}",
                           "#{ENV['VOLATILE_DIR']}/ci.log", use_venv)
      t.reenable
    end

    task :install_infrastructure do |t|
      pdns_tag = 'powerdns_recursor_' + powerdns_recursor_version.tr('.', '_')
      sh %(docker run -d --expose #{container_port2} --expose #{container_port1}/udp \
           -p #{container_port1}:#{container_port1} -p #{container_port2}:#{container_port2}/udp \
           --name #{container_name} datadog/docker-library:#{pdns_tag})
      Wait.for 8082, 5
      t.reenable
    end

    task before_script: ['ci:common:before_script']

    task script: ['ci:common:script'] do |t|
      this_provides = [
        'powerdns_recursor'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
      t.reenable
    end

    task before_cache: ['ci:common:before_cache']

    # sample cleanup task
    task cleanup: ['ci:common:cleanup'] do |t|
      sh %(docker kill #{container_name} 2>/dev/null || true)
      sh %(docker rm #{container_name} 2>/dev/null || true)
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
