# frozen_string_literal: true

require_relative '../test_helper'
require_relative '../helpers'
require 'robocap/sdk'

class TestPublicApi < Minitest::Test
  include TestHelpers

  def setup
    @tmp = Pathname(Dir.mktmpdir('robocap-pub-'))
  end

  def teardown
    FileUtils.remove_entry(@tmp) if @tmp&.directory?
  end

  def test_module_responds_to_documented_methods
    %i[import_rsa_key_version delete_rsa_key_version delete_rsa_key_dir decrypt_cenc_mp4 verify_customer_private_key].each do |sym|
      assert_respond_to Robocap::SDK, sym, "Robocap::SDK should expose .#{sym}"
    end
  end

  def test_constants_are_exposed
    assert defined?(Robocap::SDK::Error)
    assert defined?(Robocap::SDK::ErrorCode)
    assert defined?(Robocap::SDK::RsaKeyMeta)
    assert defined?(Robocap::SDK::ImportRsaResult)
    assert defined?(Robocap::SDK::DeleteRsaResult)
    assert defined?(Robocap::SDK::DecryptCencResult)
    assert defined?(Robocap::SDK::VerifiedKeyVersion)
  end

  def test_import_rsa_key_version_returns_result
    pub, priv = generate_rsa_keypair(bits: 2048)
    meta = Robocap::SDK::RsaKeyMeta.new(
      rsa_key_version: 1, effective_at: Time.utc(2026, 1, 1),
      device_id: 'D', rsa_bits: 2048,
    )
    result = Robocap::SDK.import_rsa_key_version(
      customer_id: 'C1', public_pem: pub, private_pem: priv,
      meta: meta, sdk_root: @tmp,
    )
    assert_kind_of Robocap::SDK::ImportRsaResult, result
    assert_equal 1, result.rsa_key_version
  end

  def test_delete_rsa_key_version_returns_result
    pub, priv = generate_rsa_keypair(bits: 2048)
    import_rsa_v1(@tmp, 'C1', pub, priv)
    result = Robocap::SDK.delete_rsa_key_version(
      customer_id: 'C1', rsa_key_version: 1, sdk_root: @tmp,
    )
    assert_kind_of Robocap::SDK::DeleteRsaResult, result
    assert_equal 'v1', result.folder_name
  end

  def test_delete_rsa_key_dir_returns_result
    pub, priv = generate_rsa_keypair(bits: 2048)
    import_rsa_v1(@tmp, 'C1', pub, priv)
    vault = Robocap::SDK::KeyVault.new(@tmp)
    target = vault.rsa_version_dir('C1', 1)
    result = Robocap::SDK.delete_rsa_key_dir(
      customer_id: 'C1', key_dir: target, sdk_root: @tmp,
    )
    assert_kind_of Robocap::SDK::DeleteRsaResult, result
    assert_equal 'C1', result.customer_id
    assert_equal 'v1', result.folder_name
    refute target.exist?
  end

  def test_verify_customer_private_key_returns_result
    pub, priv = generate_rsa_keypair(bits: 2048)
    import_rsa_v1(@tmp, 'C1', pub, priv)
    result = Robocap::SDK.verify_customer_private_key(
      customer_id: 'C1', user_private_pem: priv, sdk_root: @tmp,
    )
    assert_kind_of Robocap::SDK::VerifiedKeyVersion, result
    assert_equal 1, result.matched_rsa_key_version
  end
end
