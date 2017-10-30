require 'ci/common'

def pgbouncer_version
  ENV['FLAVOR_VERSION'] || 'latest'
end

def pgbouncer_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/pgbouncer_#{pgbouncer_version}"
end

pgname = 'dd-test-postgres'
pgbname = 'dd-test-pgbouncer'
pg_resources_path = (ENV['TRAVIS_BUILD_DIR']).to_s + '/pgbouncer/ci/resources/pg'
pgb_resources_path = (ENV['TRAVIS_BUILD_DIR']).to_s + '/pgbouncer/ci/resources/pgb'

namespace :ci do
  namespace :pgbouncer do |flavor|
    task before_install: ['ci:common:before_install'] do
      sh %(docker rm -f #{pgname} #{pgbname} 2>/dev/null || true)
    end

    task :install do
      Rake::Task['ci:common:install'].invoke('pgbouncer')
      puts 'Installing Postgres'
      sh %(docker run --name #{pgname} -v #{pg_resources_path}:/docker-entrypoint-initdb.d -e POSTGRES_PASSWORD=datadog -d postgres:latest)
      count = 0
      logs = `docker logs #{pgname} 2>&1`
      until count == 20 || logs.include?('PostgreSQL init process complete')
        sleep_for 2
        logs = `docker logs #{pgname} 2>&1`
        count += 1
      end
      puts 'Postgres is running, installing PgBouncer'
      sh %(docker run -d --name #{pgbname} --link #{pgname}:postgres -v #{pgb_resources_path}:/etc/pgbouncer:ro -p \
        16432:6432 kotaimen/pgbouncer:#{pgbouncer_version})
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
