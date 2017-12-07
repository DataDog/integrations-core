require 'ci/common'

def nginx_version
  ENV['FLAVOR_VERSION'] || '1.7.11'
end

def nginx_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/nginx_#{nginx_version}"
end

container_name = 'dd-test-nginx'
container_port1 = 44_441
container_port2 = 44_442

namespace :ci do
  namespace :nginx do |flavor|
    task before_install: ['ci:common:before_install'] do
      sh %(docker kill #{container_name} 2>&1 >/dev/null || true 2>&1 >/dev/null)
      sh %(docker rm #{container_name} 2>&1 >/dev/null || true 2>&1 >/dev/null)
    end

    task :install do
      Rake::Task['ci:common:install'].invoke('nginx')
      if nginx_version == '1.6.2'
        repo = 'centos/nginx-16-centos7'
        sh %(docker create -p #{container_port1}:#{container_port1} -p #{container_port2}:#{container_port2} --name #{container_name} #{repo})
        sh %(docker cp #{__dir__}/nginx.conf #{container_name}:/opt/rh/nginx16/root/etc/nginx/nginx.conf)
        sh %(docker cp #{__dir__}/testing.key #{container_name}:/opt/rh/nginx16/root/etc/nginx/testing.key)
        sh %(docker cp #{__dir__}/testing.crt #{container_name}:/opt/rh/nginx16/root/etc/nginx/testing.crt)
        sh %(docker start #{container_name})
      else
        repo = "nginx:#{nginx_version}"
        volumes = %( -v #{__dir__}/nginx.conf:/etc/nginx/nginx.conf \
                  -v #{__dir__}/testing.crt:/etc/nginx/testing.crt \
                  -v #{__dir__}/testing.key:/etc/nginx/testing.key )
        sh %(docker run -d -p #{container_port1}:#{container_port1} -p #{container_port2}:#{container_port2} \
             --name #{container_name} #{volumes} #{repo})
      end
    end

    task before_script: ['ci:common:before_script']

    task script: ['ci:common:script'] do
      this_provides = [
        'nginx'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task before_cache: ['ci:common:before_cache']

    task cleanup: ['ci:common:cleanup'] do
      sh %(docker kill #{container_name} 2>&1 >/dev/null || true 2>&1 >/dev/null)
      sh %(docker rm #{container_name} 2>&1 >/dev/null || true 2>&1 >/dev/null)
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
