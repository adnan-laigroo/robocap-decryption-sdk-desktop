# frozen_string_literal: true

require_relative '../test_helper'
require_relative '../helpers'
require 'robocap/sdk/config'
require 'robocap/sdk/errors'
require 'robocap/sdk/rsa_key_meta'
require 'robocap/sdk/rsa_oaep'
require 'robocap/sdk/vault_layout'
require 'robocap/sdk/key_vault'
require 'robocap/sdk/ffmpeg_cli'
require 'robocap/sdk/mp4_cenc'
require 'robocap/sdk/ownership'
require 'robocap/sdk/decrypt_cenc'

class TestDecryptCenc < Minitest::Test
  include TestHelpers

  def setup
    @tmp = Pathname(Dir.mktmpdir('robocap-dec-'))
    @mp4 = @tmp.join('segment.mp4'); @mp4.write('encrypted')
    @out = @tmp.join('out')
  end

  def teardown
    FileUtils.remove_entry(@tmp) if @tmp&.directory?
  end

  def stub_pipeline(tags, &block)
    meta = Robocap::SDK::Mp4Cenc.parse_cenc_metadata_from_tags(tags)
    Robocap::SDK::Mp4Cenc.stub :load_cenc_metadata, ->(_mp4, **_opts) { meta } do
      Robocap::SDK::FfmpegCli.stub :resolve_ffmpeg_executable, ->(_x = nil) { 'ffmpeg' } do
        Robocap::SDK::FfmpegCli.stub :open3_capture3, ->(*_args) { ['', '', Struct.new(:exitstatus).new(0)] } do
          block.call
        end
      end
    end
  end

  def test_decrypt_uses_v1_when_only_v1_present
    import_rsa_v1(@tmp, 'CENC_CUST', TestHelpers::EMBEDDED_CENC_PUBLIC_PEM, TestHelpers::EMBEDDED_CENC_PRIVATE_PEM)
    tags = build_cenc_tag_payload(
      TestHelpers::EMBEDDED_CENC_PUBLIC_PEM, TestHelpers::EMBEDDED_CENC_PRIVATE_PEM, customer_id: 'CENC_CUST',
    )
    result = stub_pipeline(tags) do
      Robocap::SDK::DecryptCenc.call(
        mp4_path: @mp4, user_private_pem: TestHelpers::EMBEDDED_CENC_PRIVATE_PEM,
        output_dir: @out, sdk_root: @tmp,
      )
    end
    assert_equal @out.join('segment.mp4'), result.output_path
    assert_equal 'CENC_CUST', result.customer_id
    assert_equal 1, result.rsa_key_version
  end

  def test_decrypt_picks_v2_when_wrapped_with_v2
    pub_v1, priv_v1 = generate_rsa_keypair(bits: 2048)
    pub_v2, priv_v2 = generate_rsa_keypair(bits: 2048)
    import_rsa_vN(@tmp, 'CUST', pub_v1, priv_v1, 1)
    import_rsa_vN(@tmp, 'CUST', pub_v2, priv_v2, 2)
    tags = build_cenc_tag_payload(pub_v2, priv_v2, customer_id: 'CUST')
    # The user's private key is v1; ownership verifies any matching archived
    # key, and the wrapped CEK can only be unwrapped by v2.
    result = stub_pipeline(tags) do
      Robocap::SDK::DecryptCenc.call(
        mp4_path: @mp4, user_private_pem: priv_v1, output_dir: @out, sdk_root: @tmp,
      )
    end
    assert_equal 2, result.rsa_key_version
  end

  def test_decrypt_trial_failed_when_wrapping_version_missing
    pub_v1, priv_v1 = generate_rsa_keypair(bits: 2048)
    pub_v2, priv_v2 = generate_rsa_keypair(bits: 2048)
    import_rsa_vN(@tmp, 'CUST', pub_v2, priv_v2, 2)
    tags = build_cenc_tag_payload(pub_v1, priv_v1, customer_id: 'CUST')
    err = assert_raises(Robocap::SDK::Error) do
      stub_pipeline(tags) do
        Robocap::SDK::DecryptCenc.call(
          mp4_path: @mp4, user_private_pem: priv_v2, output_dir: @out, sdk_root: @tmp,
        )
      end
    end
    assert_equal Robocap::SDK::ErrorCode::ERR_CENC_CEKA_TRIAL_FAILED, err.code
  end

  def test_decrypt_customer_not_in_vault
    import_rsa_v1(@tmp, 'CENC_CUST', TestHelpers::EMBEDDED_CENC_PUBLIC_PEM, TestHelpers::EMBEDDED_CENC_PRIVATE_PEM)
    tags = build_cenc_tag_payload(
      TestHelpers::EMBEDDED_CENC_PUBLIC_PEM, TestHelpers::EMBEDDED_CENC_PRIVATE_PEM, customer_id: 'OTHER',
    )
    err = assert_raises(Robocap::SDK::Error) do
      stub_pipeline(tags) do
        Robocap::SDK::DecryptCenc.call(
          mp4_path: @mp4, user_private_pem: TestHelpers::EMBEDDED_CENC_PRIVATE_PEM,
          output_dir: @out, sdk_root: @tmp,
        )
      end
    end
    assert_equal Robocap::SDK::ErrorCode::ERR_CUSTOMER_NOT_FOUND, err.code
  end
end
