require 'ci/common'

def lighttpd_version
  ENV['FLAVOR_VERSION'] || '1.4.35'
end

def lighttpd_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/lighttpd_#{lighttpd_version}"
end

container_name = 'dd-test-lighttpd'
container_port = 9449
lighttpd_image = 'arulrajnet/lighttpd'

namespace :ci do
  namespace :lighttpd do |flavor|
    task before_install: ['ci:common:before_install'] do
      sh %(docker kill #{container_name} 2>/dev/null || true)
      sh %(docker rm #{container_name} 2>/dev/null || true)
    end

    task :install do
      Rake::Task['ci:common:install'].invoke('lighttpd')
      sh %(docker run -d --name #{container_name} -v #{__dir__}/lighttpd.conf:/etc/lighttpd/lighttpd.conf \
           -p #{container_port}:#{container_port} #{lighttpd_image})
    end

    task before_script: ['ci:common:before_script']

    task script: ['ci:common:script'] do
      this_provides = [
        'lighttpd'
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
