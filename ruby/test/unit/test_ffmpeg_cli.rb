# frozen_string_literal: true

require_relative '../test_helper'
require 'robocap/sdk/errors'
require 'robocap/sdk/ffmpeg_cli'
require 'robocap/sdk/mp4_cenc'

class TestFfmpegCli < Minitest::Test
  def setup
    @tmp = Pathname(Dir.mktmpdir('robocap-ff-'))
  end

  def teardown
    FileUtils.remove_entry(@tmp) if @tmp&.directory?
  end

  def test_resolve_ffprobe_explicit_existing_file
    fake = @tmp.join('my-ffprobe')
    fake.write('#!/bin/sh\nexit 0\n')
    fake.chmod(0o755)
    assert_equal fake.to_s,
                 Robocap::SDK::FfmpegCli.resolve_ffprobe_executable(fake.to_s)
  end

  def test_resolve_ffprobe_explicit_basename_passes_through
    assert_equal 'ffprobe',
                 Robocap::SDK::FfmpegCli.resolve_ffprobe_executable('ffprobe')
  end

  def test_resolve_ffprobe_explicit_missing_path_raises
    err = assert_raises(Robocap::SDK::Error) do
      Robocap::SDK::FfmpegCli.resolve_ffprobe_executable(@tmp.join('nope').to_s)
    end
    assert_equal Robocap::SDK::ErrorCode::ERR_FFPROBE_NOT_FOUND, err.code
  end

  def test_resolve_ffprobe_honors_env_var
    fake = @tmp.join('env-ffprobe')
    fake.write('#!/bin/sh\nexit 0\n'); fake.chmod(0o755)
    ENV['ROBOCAP_FFPROBE'] = fake.to_s
    assert_equal fake.to_s, Robocap::SDK::FfmpegCli.resolve_ffprobe_executable
  ensure
    ENV.delete('ROBOCAP_FFPROBE')
  end

  def test_resolve_ffmpeg_falls_back_to_path
    skip 'ffmpeg not on PATH' if `which ffmpeg`.strip.empty?
    path = Robocap::SDK::FfmpegCli.resolve_ffmpeg_executable
    refute_empty path
  end

  def test_resolve_ffmpeg_raises_when_missing
    saved = ENV.to_h.slice('PATH', 'ROBOCAP_FFMPEG')
    ENV['PATH'] = @tmp.to_s
    ENV.delete('ROBOCAP_FFMPEG')
    err = assert_raises(Robocap::SDK::Error) do
      Robocap::SDK::FfmpegCli.resolve_ffmpeg_executable
    end
    assert_equal Robocap::SDK::ErrorCode::ERR_FFMPEG_NOT_FOUND, err.code
  ensure
    ENV['PATH'] = saved['PATH']
    ENV['ROBOCAP_FFMPEG'] = saved['ROBOCAP_FFMPEG'] if saved['ROBOCAP_FFMPEG']
  end

  def test_decrypt_cenc_copy_invokes_ffmpeg_with_expected_args
    input  = @tmp.join('in.mp4'); input.write('x')
    output = @tmp.join('out.mp4')
    fake_ffmpeg = @tmp.join('fake-ffmpeg')
    fake_ffmpeg.write("#!/bin/sh\nexit 0\n")
    fake_ffmpeg.chmod(0o755)
    captured = nil
    Robocap::SDK::FfmpegCli.stub :open3_capture3, ->(*args) { captured = args; ['', '', Struct.new(:exitstatus).new(0)] } do
      Robocap::SDK::FfmpegCli.decrypt_cenc_copy(
        input_mp4: input, output_mp4: output, cek_hex: 'aa' * 16,
        kid_hex: '00' * 16, ffmpeg_executable: fake_ffmpeg.to_s,
      )
    end
    refute_nil captured
    assert_includes captured, '-decryption_key'
    assert_includes captured, '-decryption_kid'
    assert_includes captured, '-i'
    assert_includes captured, '-c'
    assert_includes captured, 'copy'
    assert_includes captured, '-map'
    assert_includes captured, '0'
    assert_includes captured, '-map_metadata'
    assert_includes captured, '-movflags'
    assert_includes captured, '+use_metadata_tags'
    assert_includes captured, '-metadata'
    assert_includes captured, 'cenc_cek_wrapped_b64='
    assert_includes captured, 'cenc_wrapped_algo='
  end

  def test_decrypt_cenc_copy_clears_strip_tags
    input  = @tmp.join('in.mp4'); input.write('x')
    output = @tmp.join('out.mp4')
    fake_ffmpeg = @tmp.join('fake-ffmpeg')
    fake_ffmpeg.write("#!/bin/sh\nexit 0\n")
    fake_ffmpeg.chmod(0o755)
    captured = nil
    Robocap::SDK::FfmpegCli.stub :open3_capture3, ->(*args) { captured = args; ['', '', Struct.new(:exitstatus).new(0)] } do
      Robocap::SDK::FfmpegCli.decrypt_cenc_copy(
        input_mp4: input, output_mp4: output, cek_hex: 'aa' * 16,
        ffmpeg_executable: fake_ffmpeg.to_s,
      )
    end
    Robocap::SDK::Mp4Cenc::CENC_STRIP_TAGS_ON_DECRYPT.each do |tag|
      assert_includes captured, "#{tag}="
    end
  end

  def test_decrypt_cenc_copy_surfaces_nonzero_exit
    input  = @tmp.join('in.mp4'); input.write('x')
    output = @tmp.join('out.mp4')
    fake_ffmpeg = @tmp.join('fake-ffmpeg')
    fake_ffmpeg.write("#!/bin/sh\nexit 1\n")
    fake_ffmpeg.chmod(0o755)
    nonzero = Struct.new(:exitstatus).new(1)
    Robocap::SDK::FfmpegCli.stub :open3_capture3, ->(*_args) { ['', 'bad', nonzero] } do
      err = assert_raises(Robocap::SDK::Error) do
        Robocap::SDK::FfmpegCli.decrypt_cenc_copy(
          input_mp4: input, output_mp4: output, cek_hex: 'aa' * 16,
          ffmpeg_executable: fake_ffmpeg.to_s,
        )
      end
      assert_equal Robocap::SDK::ErrorCode::ERR_CENC_DECRYPT_FAILED, err.code
    end
  end
end
