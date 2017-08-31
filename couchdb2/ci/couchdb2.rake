require 'ci/common'

def couchdb2_version
  ENV['FLAVOR_VERSION'] || '2.0-dev'
end

def couchdb2_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/couchdb2_#{couchdb2_version}"
end

container_name = 'dd-test-couchdb-2'
container_port = 5984

namespace :ci do
  namespace :couchdb2 do |flavor|
    task before_install: ['ci:common:before_install'] do
      sh %(docker kill #{container_name} 2>/dev/null || true)
      sh %(docker rm #{container_name} 2>/dev/null || true)
    end

    task :install do
      Rake::Task['ci:common:install'].invoke('couchdb2')
      sh %(docker run -p #{container_port}:#{container_port} \
        --name #{container_name} -d klaemo/couchdb:#{couchdb2_version} --admin=dduser:pawprint --with-haproxy)
    end

    task before_script: ['ci:common:before_script'] do
      logs = `docker logs #{container_name} 2>&1`
      count = 0
      until count == 20 || logs.include?('Password:')
        sleep_for 2
        logs = `docker logs #{container_name} 2>&1`
        count += 1
      end
      sleep_for 10
      # Create a test database
      sh %(curl -X PUT http://dduser:pawprint@localhost:5984/kennel)
    end

    task script: ['ci:common:script'] do
      this_provides = [
        'couchdb2'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task before_cache: ['ci:common:before_cache']

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
