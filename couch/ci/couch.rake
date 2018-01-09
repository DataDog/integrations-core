require 'ci/common'
require 'net/http'

def couch_version
  ENV['FLAVOR_VERSION'] || '1.6.1'
end

def couch_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/couch_#{couch_version}"
end

class ArgsProvider
  attr_reader :version

  def initialize(couch_version)
    @version = couch_version.split('.').first
    @couch_version = couch_version
  end

  def docker_image
    case @version
    when '1'
      "couchdb:#{@couch_version}"
    when '2'
      "klaemo/couchdb:#{@couch_version}"
    end
  end

  def docker_args
    case @version
    when '2'
      '--admin=dduser:pawprint --with-haproxy'
    else
      ''
    end
  end

  def nose_filter
    case @version
    when '1'
      'couch_version==\'1.x\''
    when '2'
      'couch_version==\'2.x\''
    end
  end
end

container_name = 'dd-test-couch'
container_port = 5984
provider = ArgsProvider.new(couch_version)

namespace :ci do
  namespace :couch do |flavor|
    task before_install: ['ci:common:before_install'] do
      sh %(docker kill #{container_name} 2>/dev/null || true)
      sh %(docker rm #{container_name} 2>/dev/null || true)
    end

    task :install do
      Rake::Task['ci:common:install'].invoke('couch')
      sh %(docker run -p #{container_port}:#{container_port}\
        --name #{container_name} -d #{provider.docker_image} #{provider.docker_args})
    end

    task before_script: ['ci:common:before_script'] do
      Wait.for 'http://localhost:5984', 30

      # Create a test database
      if provider.version == '2'
        sh %(curl -X PUT http://dduser:pawprint@localhost:5984/kennel)
        sh "curl -X PUT http://dduser:pawprint@localhost:5984/kennel/_design/dummy -d \
          '{\"language\":\"javascript\",\
            \"views\":{\
              \"all\":{\"map\":\"function(doc) { emit(doc._id, doc); }\"},\
              \"by_data\":{ \"map\": \"function(doc) { emit(doc.data, doc); }\"}}}'"

        times = 0
        data = []
        uri = URI('http://localhost:5984/_node/node1@127.0.0.1/_stats')
        req = Net::HTTP::Get.new(uri)
        req.basic_auth('dduser', 'pawprint')

        puts 'Waiting for stats to be generated on the nodes...'
        while times < 20 || data.empty?
          res = Net::HTTP.start(uri.hostname, uri.port) do |http|
            http.request(req)
          end
          data = JSON.parse(res.body)
          times += 1
          sleep 0.5
        end

      else
        sh %(curl -X PUT http://localhost:5984/kennel)
      end
    end

    task script: ['ci:common:script'] do
      ENV['NOSE_FILTER'] = provider.nose_filter
      Rake::Task['ci:common:run_tests'].invoke(['couch'])
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
