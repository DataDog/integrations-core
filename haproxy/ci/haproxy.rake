require 'ci/common'

def haproxy_version
  ENV['FLAVOR_VERSION'] || '1.5.11'
end

def haproxy_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/haproxy_#{haproxy_version}"
end

namespace :ci do
  namespace :haproxy do |flavor|
    task before_install: ['ci:common:before_install']

    task install: ['ci:common:install'] do |t|
      use_venv = in_venv
      install_requirements('haproxy/requirements.txt',
                           "--cache-dir #{ENV['PIP_CACHE']}",
                           "#{ENV['VOLATILE_DIR']}/ci.log", use_venv)
      t.reenable
    end

    task :install_infrastructure do |t|
      sh %(mkdir -p $VOLATILE_DIR/haproxy)
      sh %(docker create -v $VOLATILE_DIR/haproxy:/tmp -p 3835:3835 --name dd-haproxy haproxy:#{haproxy_version})
      sh %(docker create -p 3836:3836 --name dd-haproxy-open haproxy:#{haproxy_version})

      sh %(docker cp `pwd`/haproxy/ci/haproxy.cfg dd-haproxy:/usr/local/etc/haproxy/haproxy.cfg)
      sh %(docker cp `pwd`/haproxy/ci/haproxy-open.cfg dd-haproxy-open:/usr/local/etc/haproxy/haproxy.cfg)

      sh %(docker start dd-haproxy)
      sh %(docker start dd-haproxy-open)

      # Allow CI user to access the haproxy unix socket
      sh %(sudo chown $USER $VOLATILE_DIR/haproxy/datadog-haproxy-stats.sock)
      t.reenable
    end

    task before_script: ['ci:common:before_script']

    task script: ['ci:common:script'] do |t, _attr|
      this_provides = [
        'haproxy'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
      t.reenable
    end

    task before_cache: ['ci:common:before_cache']

    task cleanup: ['ci:common:cleanup'] do |t|
      sh %(docker kill dd-haproxy)
      sh %(docker kill dd-haproxy-open)
      sh %(docker rm dd-haproxy)
      sh %(docker rm dd-haproxy-open)
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
