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

    task :install do
      Rake::Task['ci:common:install'].invoke('haproxy')

      sh %(mkdir -p $VOLATILE_DIR/haproxy)
      sh %(docker create -v $VOLATILE_DIR/haproxy:/tmp -p 3835:3835 --name dd-haproxy haproxy:#{haproxy_version})
      sh %(docker create -p 3836:3836 --name dd-haproxy-open haproxy:#{haproxy_version})

      sh %(docker cp #{ENV['SDK_HOME']}/haproxy/test/ci/haproxy.cfg dd-haproxy:/usr/local/etc/haproxy/haproxy.cfg)
      sh %(docker cp #{ENV['SDK_HOME']}/haproxy/test/ci/haproxy-open.cfg dd-haproxy-open:/usr/local/etc/haproxy/haproxy.cfg)

      sh %(docker start dd-haproxy)
      sh %(docker start dd-haproxy-open)

      # Allow CI user to access the haproxy unix socket
      sh %(sudo chown $USER $VOLATILE_DIR/haproxy/datadog-haproxy-stats.sock)
    end

    task before_script: ['ci:common:before_script']

    task script: ['ci:common:script'] do |_, _attr|
      this_provides = [
        'haproxy'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task before_cache: ['ci:common:before_cache']

    task cleanup: ['ci:common:cleanup'] do
      sh %(docker kill dd-haproxy)
      sh %(docker kill dd-haproxy-open)
      sh %(docker rm dd-haproxy)
      sh %(docker rm dd-haproxy-open)
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
