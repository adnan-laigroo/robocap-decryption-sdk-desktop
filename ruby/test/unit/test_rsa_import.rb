# frozen_string_literal: true

require_relative '../test_helper'
require_relative '../helpers'
require 'robocap/sdk/config'
require 'robocap/sdk/errors'
require 'robocap/sdk/rsa_key_meta'
require 'robocap/sdk/rsa_oaep'
require 'robocap/sdk/vault_layout'
require 'robocap/sdk/key_vault'
require 'robocap/sdk/rsa_import'

class TestRsaImport < Minitest::Test
  include TestHelpers

  def setup
    @tmp = Pathname(Dir.mktmpdir('robocap-imp-'))
  end

  def teardown
    FileUtils.remove_entry(@tmp) if @tmp&.directory?
  end

  def test_import_2048_returns_result
    pub, priv = generate_rsa_keypair(bits: 2048)
    meta = RobocapCenc::SDK::RsaKeyMeta.new(
      rsa_key_version: 1, effective_at: Time.utc(2026, 1, 1),
      device_id: 'DEV_2048', rsa_bits: 2048,
    )
    result = RobocapCenc::SDK::RsaImport.call(
      customer_id: 'CUST_2048', public_pem: pub, private_pem: priv,
      meta: meta, sdk_root: @tmp,
    )
    assert_equal 'CUST_2048', result.customer_id
    assert_equal 1, result.rsa_key_version
    assert result.vault_rsa_dir.directory?
  end

  def test_import_rejects_invalid_bits
    pub, priv = generate_rsa_keypair(bits: 2048)
    meta = RobocapCenc::SDK::RsaKeyMeta.new(
      rsa_key_version: 1, effective_at: Time.utc(2026, 1, 1),
      device_id: 'X', rsa_bits: 1024,
    )
    err = assert_raises(RobocapCenc::SDK::Error) do
      RobocapCenc::SDK::RsaImport.call(
        customer_id: 'CUST_BAD', public_pem: pub, private_pem: priv,
        meta: meta, sdk_root: @tmp,
      )
    end
    assert_equal RobocapCenc::SDK::ErrorCode::ERR_INVALID_RSA_BITS, err.code
  end

  def test_import_persists_meta
    pub, priv = generate_rsa_keypair(bits: 2048)
    meta = RobocapCenc::SDK::RsaKeyMeta.new(
      rsa_key_version: 1, effective_at: Time.utc(2026, 1, 1),
      device_id: 'D', rsa_bits: 2048,
    )
    RobocapCenc::SDK::RsaImport.call(
      customer_id: 'C1', public_pem: pub, private_pem: priv,
      meta: meta, sdk_root: @tmp,
    )
    loaded = RobocapCenc::SDK::KeyVault.new(@tmp).load_rsa_meta('C1', 1)
    assert_equal meta, loaded
  end
end
