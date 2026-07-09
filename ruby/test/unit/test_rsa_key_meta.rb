# frozen_string_literal: true

require_relative '../test_helper'
require 'robocap/sdk/config'
require 'robocap/sdk/rsa_key_meta'

class TestRsaKeyMeta < Minitest::Test
  def make(**overrides)
    RobocapCenc::SDK::RsaKeyMeta.new(
      rsa_key_version: overrides.fetch(:rsa_key_version, 1),
      effective_at: overrides.fetch(:effective_at, Time.utc(2026, 1, 1)),
      device_id: overrides.fetch(:device_id, 'DEV_TEST'),
      rsa_bits: overrides.fetch(:rsa_bits, 2048),
    )
  end

  def test_default_rsa_bits_falls_back_to_config
    meta = RobocapCenc::SDK::RsaKeyMeta.new(
      rsa_key_version: 1,
      effective_at: Time.utc(2026, 1, 1),
      device_id: 'D',
    )
    assert_equal RobocapCenc::SDK::Config::RSA_BITS, meta.rsa_bits
  end

  def test_rejects_zero_version
    assert_raises(ArgumentError) { make(rsa_key_version: 0) }
  end

  def test_rejects_negative_version
    assert_raises(ArgumentError) { make(rsa_key_version: -1) }
  end

  def test_rejects_non_integer_version
    assert_raises(ArgumentError) { make(rsa_key_version: '1') }
  end

  def test_rejects_non_string_device_id
    assert_raises(ArgumentError) { make(device_id: 123) }
  end

  def test_to_json_round_trip
    meta = make
    json = meta.to_json
    parsed = RobocapCenc::SDK::RsaKeyMeta.from_json(json)
    assert_equal meta, parsed
  end

  def test_to_json_includes_iso8601_effective_at
    meta = make(effective_at: Time.utc(2026, 5, 28, 12, 0, 0))
    data = JSON.parse(meta.to_json)
    assert_equal 1, data['rsa_key_version']
    assert_equal '2026-05-28T12:00:00Z', data['effective_at']
    assert_equal 'DEV_TEST', data['device_id']
    assert_equal 2048, data['rsa_bits']
  end

  def test_from_json_accepts_python_dumped_json
    python_style = JSON.generate(
      rsa_key_version: 2,
      effective_at: '2026-02-01T00:00:00+00:00',
      device_id: 'D2',
      rsa_bits: 4096,
    )
    meta = RobocapCenc::SDK::RsaKeyMeta.from_json(python_style)
    assert_equal 2, meta.rsa_key_version
    assert_equal 'D2', meta.device_id
    assert_equal 4096, meta.rsa_bits
    assert_equal Time.utc(2026, 2, 1), meta.effective_at
  end

  def test_equal_when_fields_match
    a = make
    b = make
    assert_equal a, b
  end
end
