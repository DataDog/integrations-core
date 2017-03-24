require 'ci/common'

def etcd_version
  ENV['FLAVOR_VERSION'] || 'latest'
end

def etcd_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/etcd_#{etcd_version}"
end

namespace :ci do
  namespace :etcd do |flavor|
    task before_install: ['ci:common:before_install'] do
      sh %(docker stop dd-test-etcd || true)
      sh %(docker rm dd-test-etcd || true)
    end

    task :install do
      Rake::Task['ci:common:install'].invoke('etcd')
      sh %(docker create --expose 2379 -p 2379:2379 --name dd-test-etcd quay.io/coreos/etcd:v2.0.5 -listen-client-urls http://0.0.0.0:2379)
      sh %(docker start dd-test-etcd)
    end

    task before_script: ['ci:common:before_script'] do
      Wait.for 'http://localhost:2379/v2/stats/self'
      Wait.for 'http://localhost:2379/v2/stats/store'
      10.times do
        sh %(curl -s http://127.0.0.1:2379/v2/keys/message\
             -XPUT -d value="Hello world" >/dev/null)
        sh %(curl -s http://127.0.0.1:2379/v2/keys/message > /dev/null)
      end
    end

    task script: ['ci:common:script'] do
      this_provides = [
        'etcd'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task before_cache: ['ci:common:before_cache']

    # sample cleanup task
    task cleanup: ['ci:common:cleanup'] do
      sh %(docker stop dd-test-etcd)
      sh %(docker rm dd-test-etcd)
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
