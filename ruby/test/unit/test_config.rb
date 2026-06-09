# frozen_string_literal: true

require_relative '../test_helper'
require 'robocap/sdk/config'

class TestConfig < Minitest::Test
  def test_constants_match_python
    assert_equal 4096, Robocap::SDK::Config::RSA_BITS
    assert_equal [2048, 4096], Robocap::SDK::Config::RSA_BITS_ALLOWED
    assert_equal 65_537, Robocap::SDK::Config::RSA_PUBLIC_EXPONENT
    assert_equal 512, Robocap::SDK::Config::RSA_CIPHERTEXT_BYTES
    assert_equal 256, Robocap::SDK::Config::RSA_2048_CIPHERTEXT_BYTES
    assert_equal 16, Robocap::SDK::Config::CEK_BYTES
    assert_equal 32, Robocap::SDK::Config::AES_KEY_BYTES
    assert_equal 'vault/keys', Robocap::SDK::Config::VAULT_KEYS_DIR
    assert_equal 'vault/files', Robocap::SDK::Config::VAULT_FILES_DIR
  end

  def test_default_sdk_root_uses_env_var
    ENV['ROBOCAP_SDK_ROOT'] = '/tmp/custom-vault'
    assert_equal Pathname('/tmp/custom-vault'), Robocap::SDK::Config.default_sdk_root
  ensure
    ENV.delete('ROBOCAP_SDK_ROOT')
  end

  def test_default_sdk_root_falls_back_to_home
    ENV.delete('ROBOCAP_SDK_ROOT')
    assert_equal Pathname(Dir.home).join('.robocap-sdk'),
                 Robocap::SDK::Config.default_sdk_root
  end

  def test_validate_customer_id_accepts_alphanumeric_underscore_hyphen
    Robocap::SDK::Config.validate_customer_id!('frodobot_123')
    Robocap::SDK::Config.validate_customer_id!('CUST-A1')
    Robocap::SDK::Config.validate_customer_id!('a')
  end

  def test_validate_customer_id_rejects_space
    err = assert_raises(ArgumentError) do
      Robocap::SDK::Config.validate_customer_id!('bad id')
    end
    assert_match(/customer_id/, err.message)
  end

  def test_validate_customer_id_rejects_empty
    assert_raises(ArgumentError) { Robocap::SDK::Config.validate_customer_id!('') }
  end

  def test_keys_vault_root_joins_correctly
    assert_equal Pathname('/srv/sdk/vault/keys'),
                 Robocap::SDK::Config.keys_vault_root(Pathname('/srv/sdk'))
  end

  def test_validate_customer_id_rejects_nil
    err = assert_raises(ArgumentError) { Robocap::SDK::Config.validate_customer_id!(nil) }
    assert_match(/customer_id/, err.message)
  end

  def test_files_vault_root_joins_correctly
    assert_equal Pathname('/srv/sdk/vault/files'),
                 Robocap::SDK::Config.files_vault_root(Pathname('/srv/sdk'))
  end
end
