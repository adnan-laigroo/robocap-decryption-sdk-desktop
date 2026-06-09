# frozen_string_literal: true

$LOAD_PATH.unshift File.expand_path('../lib', __dir__)

require 'minitest/autorun'
require 'fileutils'
require 'tmpdir'
require 'pathname'
require 'time'
require 'json'
require 'base64'
require 'openssl'
require 'open3'

require 'robocap/sdk'

TEST_VECTORS_DIR = Pathname(
  ENV.fetch('ROBOCAP_TEST_VECTORS_DIR') do
    File.expand_path('../../test-vectors', __dir__)
  end
).freeze
