# frozen_string_literal: true

require_relative '../test_helper'
require 'robocap/sdk/errors'

class TestErrors < Minitest::Test
  EXPECTED_CODES = {
    ERR_CUSTOMER_NOT_FOUND:        1001,
    ERR_CUSTOMER_ALREADY_EXISTS:   1002,
    ERR_KEY_OWNERSHIP_FAILED:      2001,
    ERR_CUSTOMER_MISMATCH:         2002,
    ERR_RSA_VERSION_MISSING:       3001,
    ERR_K2_META_VERSION_MISMATCH:  3002,
    ERR_K2_DECODE:                 3003,
    ERR_K2_PLAINTEXT_LENGTH:       3004,
    ERR_SIDECAR_INCOMPLETE:        4001,
    ERR_META_VALIDATION:           4002,
    ERR_DECRYPT_AUTH_TAG:          5001,
    ERR_SHA256_MISMATCH:           5002,
    ERR_VAULT_IO:                  6001,
    ERR_MASTER_KEY:                6002,
    ERR_OPENSSL_CLI_UNAVAILABLE:   6003,
    ERR_INVALID_RSA_BITS:          6004,
    ERR_OPENSSL_CLI_FAILED:        6005,
    ERR_RSA_IMPORT_INVALID:        6006,
    ERR_RSA_NOT_IMPORTED:          6007,
    ERR_DEVICE_AES_EXISTS:         6008,
    ERR_RSA_V1_REQUIRED:           6009,
    ERR_CENC_TAGS_MISSING:         7001,
    ERR_CENC_CEKA_WRAP:            7004,
    ERR_CENC_CEKA_LENGTH:          7005,
    ERR_FFMPEG_NOT_FOUND:          7006,
    ERR_FFPROBE_NOT_FOUND:         7007,
    ERR_CENC_DECRYPT_FAILED:       7008,
    ERR_CENC_FFPROBE_FAILED:       7009,
    ERR_CENC_CUSTOMER_ID_INVALID:  7010,
    ERR_CENC_CEKA_TRIAL_FAILED:    7011,
  }.freeze

  def test_error_code_integers_match_python
    EXPECTED_CODES.each do |name, value|
      assert_equal value,
                   RobocapCenc::SDK::ErrorCode.const_get(name),
                   "ErrorCode::#{name} value mismatch"
    end
  end

  def test_error_code_count_is_30
    int_consts = RobocapCenc::SDK::ErrorCode.constants.select do |c|
      RobocapCenc::SDK::ErrorCode.const_get(c).is_a?(Integer)
    end
    assert_equal 30, int_consts.length
  end

  def test_name_for_returns_constant_name
    assert_equal 'ERR_CUSTOMER_NOT_FOUND',
                 RobocapCenc::SDK::ErrorCode.name_for(1001)
  end

  def test_name_for_unknown_code
    assert_equal 'ERR_UNKNOWN_9999', RobocapCenc::SDK::ErrorCode.name_for(9999)
  end

  def test_error_message_includes_code_name
    err = RobocapCenc::SDK::Error.new(
      code: RobocapCenc::SDK::ErrorCode::ERR_CUSTOMER_NOT_FOUND,
      message: 'no such customer',
    )
    assert_match(/ERR_CUSTOMER_NOT_FOUND/, err.message)
    assert_match(/no such customer/, err.message)
  end

  def test_error_carries_code_and_detail
    err = RobocapCenc::SDK::Error.new(
      code: 6001,
      message: 'io failure',
      detail: { path: '/x/y' },
    )
    assert_equal 6001, err.code
    assert_equal({ path: '/x/y' }, err.detail)
  end

  def test_error_to_h_matches_python_to_dict_shape
    err = RobocapCenc::SDK::Error.new(code: 6001, message: 'io failure', detail: { p: 1 })
    h = err.to_h
    assert_equal 6001, h[:code]
    assert_equal 'ERR_VAULT_IO', h[:error]
    assert_equal 'io failure', h[:message]
    assert_equal({ p: 1 }, h[:detail])
  end

  def test_error_to_h_with_nil_detail
    err = RobocapCenc::SDK::Error.new(code: 6001, message: 'x')
    assert_nil err.to_h[:detail]
  end
end
