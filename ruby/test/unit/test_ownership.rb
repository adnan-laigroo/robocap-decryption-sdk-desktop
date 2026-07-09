# frozen_string_literal: true

require_relative '../test_helper'
require_relative '../helpers'
require 'robocap/sdk/config'
require 'robocap/sdk/errors'
require 'robocap/sdk/rsa_key_meta'
require 'robocap/sdk/rsa_oaep'
require 'robocap/sdk/vault_layout'
require 'robocap/sdk/key_vault'
require 'robocap/sdk/ownership'

class TestOwnership < Minitest::Test
  include TestHelpers

  def setup
    @tmp = Pathname(Dir.mktmpdir('robocap-own-'))
    @pub, @priv = generate_rsa_keypair(bits: 2048)
    import_rsa_v1(@tmp, 'CUST_TEST', @pub, @priv)
  end

  def teardown
    FileUtils.remove_entry(@tmp) if @tmp&.directory?
  end

  def test_match_returns_verified_key_version
    result = RobocapCenc::SDK::Ownership.verify(
      customer_id: 'CUST_TEST', user_private_pem: @priv, sdk_root: @tmp,
    )
    assert_equal 'CUST_TEST', result.customer_id
    assert_equal 1, result.matched_rsa_key_version
    refute_empty result.public_fingerprint
  end

  def test_wrong_key_raises_ownership_failed
    _, other_priv = generate_rsa_keypair
    err = assert_raises(RobocapCenc::SDK::Error) do
      RobocapCenc::SDK::Ownership.verify(
        customer_id: 'CUST_TEST', user_private_pem: other_priv, sdk_root: @tmp,
      )
    end
    assert_equal RobocapCenc::SDK::ErrorCode::ERR_KEY_OWNERSHIP_FAILED, err.code
  end

  def test_unknown_customer_raises_not_found
    err = assert_raises(RobocapCenc::SDK::Error) do
      RobocapCenc::SDK::Ownership.verify(
        customer_id: 'MISSING', user_private_pem: @priv, sdk_root: @tmp,
      )
    end
    assert_equal RobocapCenc::SDK::ErrorCode::ERR_CUSTOMER_NOT_FOUND, err.code
  end

  def test_invalid_pem_raises_ownership_failed
    err = assert_raises(RobocapCenc::SDK::Error) do
      RobocapCenc::SDK::Ownership.verify(
        customer_id: 'CUST_TEST', user_private_pem: 'not a pem', sdk_root: @tmp,
      )
    end
    assert_equal RobocapCenc::SDK::ErrorCode::ERR_KEY_OWNERSHIP_FAILED, err.code
  end

  def test_multi_version_matches_correct_version
    pub2, priv2 = generate_rsa_keypair(bits: 2048)
    import_rsa_vN(@tmp, 'CUST_MULTI', @pub, @priv, 1)
    import_rsa_vN(@tmp, 'CUST_MULTI', pub2, priv2, 2)
    result = RobocapCenc::SDK::Ownership.verify(
      customer_id: 'CUST_MULTI', user_private_pem: priv2, sdk_root: @tmp,
    )
    assert_equal 2, result.matched_rsa_key_version
  end
end
