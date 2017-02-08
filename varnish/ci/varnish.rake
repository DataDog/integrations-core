require 'ci/common'

def varnish_version
  ENV['FLAVOR_VERSION'] || '4.1.4'
end

namespace :ci do
  namespace :varnish do |flavor|
    task before_install: ['ci:common:before_install']

    task install: ['ci:common:install'] do |t|
      use_venv = in_venv
      install_requirements('varnish/requirements.txt',
                           "--cache-dir #{ENV['PIP_CACHE']}",
                           "#{ENV['VOLATILE_DIR']}/ci.log", use_venv)
      t.reenable
    end

    task :install_infrastructure do |t|
      target = varnish_version.split('.')[0]
      sh %(docker-compose -f varnish/ci/docker-compose.yml up -d varnish#{target})
      t.reenable
    end

    task before_script: ['ci:common:before_script']

    task script: ['ci:common:script'] do |t, _attr|
      Rake::Task['ci:common:run_tests'].invoke(['varnish'])
      t.reenable
    end

    task before_cache: ['ci:common:before_cache']

    task cleanup: ['ci:common:cleanup'] do |t|
      sh %(docker-compose -f varnish/ci/docker-compose.yml down)
      t.reenable
    end

    task :execute do
      if ENV['FLAVOR_VERSION']
        flavor_versions = ENV['FLAVOR_VERSION'].split(',')
      else
        flavor_versions = [nil]
      end

      exception = nil
      begin
        %w(before_install install).each do |u|
          Rake::Task["#{flavor.scope.path}:#{u}"].invoke
        end
        flavor_versions.each do |flavor_version|
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
