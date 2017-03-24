require 'ci/common'

def iis_version
  ENV['FLAVOR_VERSION'] || 'latest'
end

def iis_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/iis_#{iis_version}"
end

def iis_testsite_name
  'Test-Website-1'
end

def iis_testsite_dir
  File.join(ENV['INTEGRATIONS_DIR'], "iis_#{iis_testsite_name}")
end

namespace :ci do
  namespace :iis do |flavor|
    task before_install: ['ci:common:before_install']

    task :install do
      Rake::Task['ci:common:install'].invoke('iis')
    end

    task before_script: ['ci:common:before_script'] do
      # Set up an IIS website
      sh %(powershell New-Item -ItemType Directory -Force #{iis_testsite_dir})
      sh %(powershell Import-Module WebAdministration)
      # Create the new website
      sh %(powershell New-Website -Name #{iis_testsite_name} -Port 8080 -PhysicalPath #{iis_testsite_dir})
    end

    task script: ['ci:common:script'] do
      this_provides = [
        'iis'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task before_cache: ['ci:common:before_cache']

    task cleanup: ['ci:common:cleanup']

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
