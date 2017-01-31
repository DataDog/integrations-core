require 'json'
require 'securerandom'
require 'pp'

Dir.glob("./**/manifest.json") do |f|
  manifest = JSON.parse(File.read(f))
  manifest['manifest_version'] = "0.1.0"
  File.open(f, "w") do |manifestFile|
    manifestFile.write(JSON.pretty_generate(manifest))
  end
end
