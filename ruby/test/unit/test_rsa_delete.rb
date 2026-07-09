# frozen_string_literal: true

require_relative '../test_helper'
require_relative '../helpers'
require 'robocap/sdk/config'
require 'robocap/sdk/errors'
require 'robocap/sdk/rsa_key_meta'
require 'robocap/sdk/rsa_oaep'
require 'robocap/sdk/vault_layout'
require 'robocap/sdk/key_vault'
require 'robocap/sdk/rsa_delete'

class TestRsaDelete < Minitest::Test
  include TestHelpers

  def setup
    @tmp = Pathname(Dir.mktmpdir('robocap-del-'))
    @pub, @priv = generate_rsa_keypair(bits: 2048)
    import_rsa_v1(@tmp, 'CUST_DEL', @pub, @priv)
  end

  def teardown
    FileUtils.remove_entry(@tmp) if @tmp&.directory?
  end

  def test_delete_removes_version_and_returns_result
    result = RobocapCenc::SDK::RsaDelete.call(
      customer_id: 'CUST_DEL', rsa_key_version: 1, sdk_root: @tmp,
    )
    assert_equal 'CUST_DEL', result.customer_id
    assert_equal 'v1', result.folder_name
    refute result.key_dir.directory?
    assert_equal [], RobocapCenc::SDK::KeyVault.new(@tmp).list_rsa_versions('CUST_DEL')
  end

  def test_delete_unknown_customer
    err = assert_raises(RobocapCenc::SDK::Error) do
      RobocapCenc::SDK::RsaDelete.call(
        customer_id: 'NOPE', rsa_key_version: 1, sdk_root: @tmp,
      )
    end
    assert_equal RobocapCenc::SDK::ErrorCode::ERR_CUSTOMER_NOT_FOUND, err.code
  end

  def test_delete_unknown_version
    err = assert_raises(RobocapCenc::SDK::Error) do
      RobocapCenc::SDK::RsaDelete.call(
        customer_id: 'CUST_DEL', rsa_key_version: 99, sdk_root: @tmp,
      )
    end
    assert_equal RobocapCenc::SDK::ErrorCode::ERR_RSA_VERSION_MISSING, err.code
  end

  def test_delete_keeps_other_versions
    pub2, priv2 = generate_rsa_keypair(bits: 2048)
    import_rsa_vN(@tmp, 'CUST_DEL', pub2, priv2, 2)
    RobocapCenc::SDK::RsaDelete.call(
      customer_id: 'CUST_DEL', rsa_key_version: 1, sdk_root: @tmp,
    )
    assert_equal [2], RobocapCenc::SDK::KeyVault.new(@tmp).list_rsa_versions('CUST_DEL')
  end

  def test_call_with_dir_removes_dir_and_returns_result
    vault = RobocapCenc::SDK::KeyVault.new(@tmp)
    target = vault.rsa_version_dir('CUST_DEL', 1)
    expected_resolved = target.realpath
    result = RobocapCenc::SDK::RsaDelete.call_with_dir(
      customer_id: 'CUST_DEL', key_dir: target, sdk_root: @tmp,
    )
    assert_equal 'CUST_DEL', result.customer_id
    assert_equal 'v1', result.folder_name
    assert_equal expected_resolved.to_s, result.key_dir.to_s
    refute target.exist?
    assert_equal [], vault.list_rsa_versions('CUST_DEL')
  end
end
