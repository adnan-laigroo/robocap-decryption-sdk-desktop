# frozen_string_literal: true

require_relative 'lib/robocap/sdk/version'

Gem::Specification.new do |s|
  s.name        = 'robocap-decryption-sdk'
  s.version     = RobocapCenc::SDK::VERSION
  s.summary     = 'Offline import of RSA keys and decrypt of CENC-encrypted MP4 files.'
  s.description = 'Ruby port of the Robocap CENC decryption SDK. Reads the same on-disk vault and MP4 format as the Python SDK.'
  s.authors     = ['Frodobots']
  s.license     = 'Nonstandard'
  s.homepage    = 'https://github.com/frodobots-org/robocap-decryption-sdk'

  s.required_ruby_version = '>= 3.2'

  s.files = Dir['lib/**/*.rb'] + ['README.md']
  s.bindir      = 'exe'
  s.executables = ['robocap-decryption-sdk']
  s.require_paths = ['lib']

  s.add_development_dependency 'base64', '~> 0.2'
  s.add_development_dependency 'minitest', '~> 5.20'
  s.add_development_dependency 'rake', '~> 13.0'
end
