require 'ci/common'

def linkerd_version
  ENV['FLAVOR_VERSION'] || '1.3.5'
end

def linkerd_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/linkerd_#{linkerd_version}"
end

container_name = 'dd-test-linkerd'
container_port = 9990

namespace :ci do
  namespace :linkerd do |flavor|
    task before_install: ['ci:common:before_install'] do
      sh %(rm -rf #{linkerd_rootdir} || true)
      sh %(mkdir -p #{linkerd_rootdir} || true)
      sh %(docker kill #{container_name} 2>/dev/null || true)
      sh %(docker rm #{container_name} 2>/dev/null || true)
    end

    task :install do
      Rake::Task['ci:common:install'].invoke('linkerd')
      sh %(docker run -d --name #{container_name} -p #{container_port}:#{container_port} \
           -v #{__dir__}/config.yaml:/config.yaml buoyantio/linkerd:#{linkerd_version} /config.yaml)
    end

    task before_script: ['ci:common:before_script'] do
      Wait.for 'http://localhost:9990/admin/metrics/prometheus'
    end

    task script: ['ci:common:script'] do
      this_provides = [
        'linkerd'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task before_cache: ['ci:common:before_cache']

    task cleanup: ['ci:common:cleanup'] do
      sh %(docker kill #{container_name} 2>/dev/null || true)
      sh %(docker rm #{container_name} 2>/dev/null || true)
      sh %(rm -rf #{supervisord_rootdir})
    end

    task :execute do
      exception = nil
      begin
        %w[before_install install before_script].each do |u|
          Rake::Task["#{flavor.scope.path}:#{u}"].invoke
        end
        if !ENV['SKIP_TEST']
          Rake::Task["#{flavor.scope.path}:script"].invoke
        else
          puts 'Skipping tests'.yellow
        end
        Rake::Task["#{flavor.scope.path}:before_cache"].invoke
      rescue StandardError => e
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
