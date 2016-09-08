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

    task install: ['ci:common:install'] do
      use_venv = in_venv
      install_requirements('haproxy/requirements.txt',
                           "--cache-dir #{ENV['PIP_CACHE']}",
                           "#{ENV['VOLATILE_DIR']}/ci.log", use_venv)

      sh %(docker create -p 3835:3835 --name haproxy haproxy:#{haproxy_version})
      sh %(docker create -p 3836:3836 --name haproxy-open haproxy:#{haproxy_version})

      sh %(docker cp haproxy/ci/haproxy.cfg haproxy:/usr/local/etc/haproxy/haproxy.cfg)
      sh %(docker cp haproxy/ci/haproxy-open.cfg haproxy-open:/usr/local/etc/haproxy/haproxy.cfg)

      sh %(docker start haproxy)
      sh %(docker start haproxy-open)
    end

    task before_script: ['ci:common:before_script']

    task script: ['ci:common:script'] do |_, attr|
      this_provides = [
        'haproxy'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task before_cache: ['ci:common:before_cache']

    task cleanup: ['ci:common:cleanup'] do
      sh %(docker stop haproxy)
      sh %(docker stop haproxy-open)
      sh %(docker rm haproxy)
      sh %(docker rm haproxy-open)
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
