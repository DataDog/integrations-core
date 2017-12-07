require 'ci/common'

def varnish_version
  ENV['FLAVOR_VERSION'] || '4.1.7'
end

namespace :ci do
  namespace :varnish do |flavor|
    task before_install: ['ci:common:before_install']

    task :install do
      target = varnish_version.split('.')[0]
      sh %(docker-compose -f varnish/ci/docker-compose.yml up -d varnish#{target})
    end

    task before_script: ['ci:common:before_script']

    task script: ['ci:common:script'] do |_, _attr|
      Rake::Task['ci:common:run_tests'].invoke(['varnish'])
    end

    task before_cache: ['ci:common:before_cache']

    task cleanup: ['ci:common:cleanup'] do
      sh %(docker-compose -f varnish/ci/docker-compose.yml down)
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
