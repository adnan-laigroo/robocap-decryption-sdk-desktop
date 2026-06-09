# frozen_string_literal: true

require_relative '../test_helper'

class TestCli < Minitest::Test
  RUBY_DIR  = Pathname(File.expand_path('../..', __dir__))
  EXE       = RUBY_DIR.join('exe/robocap-sdk')
  FIXTURES  = TEST_VECTORS_DIR.join('keys')

  def setup
    @sdk_root = Pathname(Dir.mktmpdir('robocap-cli-'))
  end

  def teardown
    FileUtils.remove_entry(@sdk_root) if @sdk_root&.directory?
  end

  def run_cli(*args)
    stdout, stderr, status = Open3.capture3(
      RbConfig.ruby, EXE.to_s, *args.map(&:to_s),
      chdir: RUBY_DIR.to_s,
    )
    [stdout, stderr, status.exitstatus]
  end

  def test_help_exits_zero
    _stdout, _stderr, code = run_cli('--help')
    assert_equal 0, code
  end

  def test_import_then_delete_round_trip
    stdout, _stderr, code = run_cli(
      'import-rsa',
      '--customer-id', 'CLI_TEST',
      '--public-key',  FIXTURES.join('rsa_public_spki.pem').to_s,
      '--private-key', FIXTURES.join('rsa_private_pkcs8.pem').to_s,
      '--rsa-key-version', '1',
      '--rsa-bits', '2048',
      '--sdk-root', @sdk_root.to_s,
    )
    assert_equal 0, code
    payload = JSON.parse(stdout)
    assert_equal 'ok', payload['status']
    assert_equal 'CLI_TEST', payload['customer_id']
    assert_equal 1, payload['rsa_key_version']

    stdout2, _stderr2, code2 = run_cli(
      'delete-rsa',
      '--customer-id', 'CLI_TEST',
      '--rsa-key-version', '1',
      '--sdk-root', @sdk_root.to_s,
    )
    assert_equal 0, code2
    delete_payload = JSON.parse(stdout2)
    assert_equal 'ok', delete_payload['status']
    assert_equal 1, delete_payload['rsa_key_version']
    assert_equal 'v1', delete_payload['folder_name']
  end

  def test_import_error_emits_json_on_stderr
    _stdout, stderr, code = run_cli(
      'import-rsa',
      '--customer-id', 'CLI_BAD',
      '--public-key',  FIXTURES.join('rsa_public_spki.pem').to_s,
      '--private-key', FIXTURES.join('rsa_private_pkcs8.pem').to_s,
      '--rsa-key-version', '1',
      '--rsa-bits', '4096', # mismatched bits vs the 2048 fixture
      '--sdk-root', @sdk_root.to_s,
    )
    assert_equal 1, code
    payload = JSON.parse(stderr)
    assert_equal 6004, payload['code']  # ERR_INVALID_RSA_BITS
    assert_equal 'ERR_INVALID_RSA_BITS', payload['error']
  end

  def test_missing_required_option
    _stdout, _stderr, code = run_cli('import-rsa', '--customer-id', 'X')
    assert_equal 2, code
  end
end
