# frozen_string_literal: true

require_relative '../test_helper'
require_relative '../helpers'
require 'robocap/sdk/config'
require 'robocap/sdk/errors'
require 'robocap/sdk/rsa_oaep'
require 'robocap/sdk/ffmpeg_cli'
require 'robocap/sdk/mp4_cenc'

class TestMp4Cenc < Minitest::Test
  include TestHelpers

  def setup
    @tmp = Pathname(Dir.mktmpdir('robocap-mp4-'))
    @mp4 = @tmp.join('clip.mp4')
    @mp4.write('fake-mp4-bytes')
  end

  def teardown
    FileUtils.remove_entry(@tmp) if @tmp&.directory?
  end

  def stub_ffprobe(tags)
    payload = JSON.generate(format: { tags: tags })
    RobocapCenc::SDK::FfmpegCli.stub :resolve_ffprobe_executable, ->(_explicit = nil) { 'ffprobe' } do
      RobocapCenc::SDK::FfmpegCli.stub :open3_capture3, ->(*_args) { [payload, '', Struct.new(:exitstatus).new(0)] } do
        yield
      end
    end
  end

  def test_parse_cenc_metadata_minimal_tags
    pub, priv = generate_rsa_keypair(bits: 2048)
    tags = build_cenc_tag_payload(pub, priv, customer_id: 'CENC_CUST')
    meta = RobocapCenc::SDK::Mp4Cenc.parse_cenc_metadata_from_tags(tags)
    assert_equal 'CENC_CUST', meta.customer_id
    assert_equal RobocapCenc::SDK::Config::RSA_2048_CIPHERTEXT_BYTES, meta.cek_wrapped.bytesize
  end

  def test_parse_missing_ceka_raises
    err = assert_raises(RobocapCenc::SDK::Error) do
      RobocapCenc::SDK::Mp4Cenc.parse_cenc_metadata_from_tags('cenc_customer_id' => 'X')
    end
    assert_equal RobocapCenc::SDK::ErrorCode::ERR_CENC_TAGS_MISSING, err.code
  end

  def test_parse_missing_customer_id_raises
    pub, priv = generate_rsa_keypair(bits: 2048)
    tags = build_cenc_tag_payload(pub, priv)
    tags.delete('cenc_customer_id')
    err = assert_raises(RobocapCenc::SDK::Error) do
      RobocapCenc::SDK::Mp4Cenc.parse_cenc_metadata_from_tags(tags)
    end
    assert_equal RobocapCenc::SDK::ErrorCode::ERR_CENC_TAGS_MISSING, err.code
  end

  def test_parse_customer_id_username_fallback
    pub, priv = generate_rsa_keypair(bits: 2048)
    tags = build_cenc_tag_payload(pub, priv, customer_id: 'CENC_CUST')
    tags.delete('cenc_customer_id')
    tags['username'] = 'frodobot'
    meta = RobocapCenc::SDK::Mp4Cenc.parse_cenc_metadata_from_tags(tags)
    assert_equal 'frodobot', meta.customer_id
  end

  def test_parse_prefers_cenc_customer_id_over_username
    pub, priv = generate_rsa_keypair(bits: 2048)
    tags = build_cenc_tag_payload(pub, priv, customer_id: 'PRIMARY')
    tags['username'] = 'frodobot'
    meta = RobocapCenc::SDK::Mp4Cenc.parse_cenc_metadata_from_tags(tags)
    assert_equal 'PRIMARY', meta.customer_id
  end

  def test_parse_invalid_customer_id
    pub, priv = generate_rsa_keypair(bits: 2048)
    tags = build_cenc_tag_payload(pub, priv, customer_id: 'bad id')
    err = assert_raises(RobocapCenc::SDK::Error) do
      RobocapCenc::SDK::Mp4Cenc.parse_cenc_metadata_from_tags(tags)
    end
    assert_equal RobocapCenc::SDK::ErrorCode::ERR_CENC_CUSTOMER_ID_INVALID, err.code
  end

  def test_parse_invalid_base64
    pub, priv = generate_rsa_keypair(bits: 2048)
    tags = build_cenc_tag_payload(pub, priv)
    tags['cenc_cek_wrapped_b64'] = 'not-valid-base64!!'
    err = assert_raises(RobocapCenc::SDK::Error) do
      RobocapCenc::SDK::Mp4Cenc.parse_cenc_metadata_from_tags(tags)
    end
    assert_equal RobocapCenc::SDK::ErrorCode::ERR_CENC_TAGS_MISSING, err.code
  end

  def test_parse_wrapped_length
    pub, priv = generate_rsa_keypair(bits: 2048)
    tags = build_cenc_tag_payload(pub, priv)
    tags['cenc_cek_wrapped_b64'] = 'AA=='
    err = assert_raises(RobocapCenc::SDK::Error) do
      RobocapCenc::SDK::Mp4Cenc.parse_cenc_metadata_from_tags(tags)
    end
    assert_equal RobocapCenc::SDK::ErrorCode::ERR_CENC_CEKA_WRAP, err.code
  end

  def test_read_format_tags_with_stubbed_ffprobe
    pub, priv = generate_rsa_keypair(bits: 2048)
    tags = build_cenc_tag_payload(pub, priv, customer_id: 'CENC_CUST')
    parsed = stub_ffprobe(tags) { RobocapCenc::SDK::Mp4Cenc.read_format_tags(@mp4) }
    assert_equal 'CENC_CUST', parsed['cenc_customer_id']
  end

  def test_has_cenc_tags_true
    pub, priv = generate_rsa_keypair(bits: 2048)
    tags = build_cenc_tag_payload(pub, priv)
    result = stub_ffprobe(tags) { RobocapCenc::SDK::Mp4Cenc.has_cenc_tags(@mp4) }
    assert_equal true, result
  end

  def test_has_cenc_tags_requires_customer_source
    only_cek = { 'cenc_cek_wrapped_b64' => 'abc' }
    result = stub_ffprobe(only_cek) { RobocapCenc::SDK::Mp4Cenc.has_cenc_tags(@mp4) }
    assert_equal false, result
  end

  def test_load_cenc_metadata_roundtrip
    pub, priv = generate_rsa_keypair(bits: 2048)
    tags = build_cenc_tag_payload(pub, priv, customer_id: 'CENC_CUST')
    meta = stub_ffprobe(tags) { RobocapCenc::SDK::Mp4Cenc.load_cenc_metadata(@mp4) }
    assert_equal 'CENC_CUST', meta.customer_id
  end

  def test_read_format_tags_missing_file
    err = assert_raises(RobocapCenc::SDK::Error) do
      RobocapCenc::SDK::Mp4Cenc.read_format_tags(@tmp.join('nope.mp4'))
    end
    assert_equal RobocapCenc::SDK::ErrorCode::ERR_CENC_TAGS_MISSING, err.code
  end

  def test_cenc_strip_tags_on_decrypt_contents
    assert_equal ['cenc_cek_wrapped_b64', 'cenc_wrapped_algo'],
                 RobocapCenc::SDK::Mp4Cenc::CENC_STRIP_TAGS_ON_DECRYPT
  end
end
