require 'ci/common'

def pgbouncer_version
  ENV['FLAVOR_VERSION'] || 'latest'
end

def pgbouncer_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/pgbouncer_#{pgbouncer_version}"
end

namespace :ci do
  namespace :pgbouncer do |flavor|
    task before_install: ['ci:common:before_install']

    task install: ['ci:common:install'] do
      use_venv = in_venv
      install_requirements('pgbouncer/requirements.txt',
                           "--cache-dir #{ENV['PIP_CACHE']}",
                           "#{ENV['VOLATILE_DIR']}/ci.log", use_venv)
      sh %(bash pgbouncer/ci/start-docker-pg.sh)
      sh %(docker run -d --name dd-test-pgbouncer --link dd-test-postgres:postgres -v resources:/etc/pgbouncer:ro -p 15433:6432 kotaimen/pgbouncer)
      sleep_for 10
    end

    task before_script: ['ci:common:before_script']

    task script: ['ci:common:script'] do
      this_provides = [
        'pgbouncer'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task before_cache: ['ci:common:before_cache']

    task cleanup: ['ci:common:cleanup'] do
      sh %(docker rm -f dd-test-pgbouncer dd-test-postgres)
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
