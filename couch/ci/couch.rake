require 'ci/common'

def couch_version
  ENV['FLAVOR_VERSION'] || 'couchdb:1.6.1'
end

def couch_2?
  couch_version.include? '2.0'
end

def couch_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/couch_#{couch_version}"
end

container_name = 'dd-test-couch'
container_port = 5984

namespace :ci do
  namespace :couch do |flavor|
    task before_install: ['ci:common:before_install'] do
      sh %(docker kill #{container_name} 2>/dev/null || true)
      sh %(docker rm #{container_name} 2>/dev/null || true)
    end

    task :install do
      Rake::Task['ci:common:install'].invoke('couch')
      docker_args = if couch_2?
                      %(--with-admin-party-please --with-haproxy -n 1)
                    else
                      %()
                    end
      sh %(docker run -p #{container_port}:#{container_port} --name #{container_name} -d #{couch_version} ) + docker_args
    end

    task before_script: ['ci:common:before_script'] do
      if couch_2?
        ENV['NOSE_FILTER'] = if ENV['NOSE_FILTER']
                               ENV['NOSE_FILTER'] + ' and not couch1_only'
                             else
                               'not couch1_only'
                             end
      end

      Wait.for container_port
      count = 0
      logs = `docker logs dd-test-couch 2>&1`
      puts 'Waiting for couchdb to come up'
      couch_up_msg = couch_2? ? 'cluster is set up' : 'CouchDB has started'
      until count == 20 || logs.include?(couch_up_msg)
        sleep_for 2
        logs = `docker logs dd-test-couch 2>&1`
        count += 1
      end
      puts 'couchdb is up!' if logs.include? couch_up_msg

      if couch_2?
        # couch 2 takes a little longer to be available, but doesn't have more
        # logs we can look for
        sleep_for 10
      end

      # Create a user
      if couch_2?
        sh %(curl -X PUT http://localhost:5984/_node/node1@127.0.0.1/_config/admins/dduser -d '"pawprint"')
      else
        sh %(curl -X PUT http://localhost:5984/_config/admins/dduser -d '"pawprint"')
      end

      # Create a test database
      sh %(curl -X PUT http://dduser:pawprint@localhost:5984/kennel)

      # Restrict test databse to other authenticated user
      sh %(curl -X PUT http://dduser:pawprint@localhost:5984/kennel/_security \
           -d '{"admins":{"names":[],"roles":[]},"members":{"names":["dduser"],"roles":[]}}')
    end

    task script: ['ci:common:script'] do
      this_provides = [
        'couch'
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
