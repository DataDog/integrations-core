require 'ci/common'

def activemq_xml_version
  ENV['FLAVOR_VERSION'] || 'latest'
end

def activemq_xml_rootdir
  if ENV['TRAVIS']
    return "#{ENV['INTEGRATIONS_DIR']}/activemq_xml_#{activemq_xml_version}"
  end
  if ENV['VOLATILE_DIR']
    "#{ENV['VOLATILE_DIR']}/activemq_xml"
  else
    '/tmp/integration-sdk-testing/activemq_xml'
  end
end

container_name = 'dd-test-activemq-xml'
admin_port = 8161
listen_port = 61_616

namespace :ci do
  namespace :activemq_xml do |flavor|
    task before_install: ['ci:common:before_install'] do
      sh %(docker stop #{container_name} || true)
      sh %(docker rm #{container_name} || true)
      sh %(mkdir -p #{activemq_xml_rootdir}/data)

      sh %(curl -s -L\
       -o #{activemq_xml_rootdir}/kahadb.tar.gz\
       https://s3.amazonaws.com/dd-agent-tarball-mirror/apache-activemq-kahadb.tar.gz)
      sh %(tar zxf #{activemq_xml_rootdir}/kahadb.tar.gz\
       -C #{activemq_xml_rootdir}/data)
      sh %(rm -rf #{activemq_xml_rootdir}/data/kahadb/lock)
      # I don't like this but it encounters a permissions error if I don't put the chmod here.
      sh %(chmod -R a+rwxX #{activemq_xml_rootdir})
    end

    task :install do
      Rake::Task['ci:common:install'].invoke('activemq_xml')

      sh %(docker run -d \
       -p #{admin_port}:#{admin_port} \
       -p #{listen_port}:#{listen_port} \
       --name #{container_name} \
       -v #{activemq_xml_rootdir}/data:/var/activemq/data \
       -e ACTIVEMQ_DATA=/var/activemq/data \
       rmohr/activemq:#{activemq_xml_version})

      Wait.for 'http://localhost:8161'
    end

    task before_script: ['ci:common:before_script']

    task script: ['ci:common:script'] do
      this_provides = [
        'activemq_xml'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task before_cache: ['ci:common:before_cache']

    task cleanup: ['ci:common:cleanup'] do
      sh %(rm -rf #{activemq_xml_rootdir})
      sh %(docker stop #{container_name} || true)
      sh %(docker rm #{container_name} || true)
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
