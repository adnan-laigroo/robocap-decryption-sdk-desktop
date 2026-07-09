# frozen_string_literal: true

require_relative '../test_helper'
require 'robocap/sdk/errors'
require 'robocap/sdk/vault_layout'

class TestVaultLayout < Minitest::Test
  def setup
    @tmp = Pathname(Dir.mktmpdir('robocap-test-'))
  end

  def teardown
    FileUtils.remove_entry(@tmp) if @tmp&.directory?
  end

  def test_ensure_private_dir_creates_with_0700
    skip 'POSIX permission test' if Gem.win_platform?
    target = @tmp.join('a/b/c')
    RobocapCenc::SDK::VaultLayout.ensure_private_dir(target)
    assert target.directory?
    mode = (target.stat.mode & 0o777)
    assert_equal 0o700, mode
  end

  def test_ensure_private_dir_is_idempotent
    target = @tmp.join('idempotent')
    RobocapCenc::SDK::VaultLayout.ensure_private_dir(target)
    RobocapCenc::SDK::VaultLayout.ensure_private_dir(target)
    assert target.directory?
  end

  def test_atomic_write_bytes_writes_payload
    target = @tmp.join('out/data.bin')
    payload = (0..255).to_a.pack('C*')
    RobocapCenc::SDK::VaultLayout.atomic_write_bytes(target, payload)
    assert_equal payload, target.binread
  end

  def test_atomic_write_bytes_does_not_leave_tmp_files
    target = @tmp.join('out/data.bin')
    RobocapCenc::SDK::VaultLayout.atomic_write_bytes(target, 'hello')
    leftovers = target.parent.children.select { |c| c.basename.to_s.start_with?('.tmp_') }
    assert_empty leftovers
  end

  def test_atomic_write_bytes_overwrites_existing
    target = @tmp.join('over/data.bin')
    RobocapCenc::SDK::VaultLayout.atomic_write_bytes(target, 'first')
    RobocapCenc::SDK::VaultLayout.atomic_write_bytes(target, 'second')
    assert_equal 'second', target.binread
  end

  def test_atomic_write_text_utf8
    target = @tmp.join('text.json')
    RobocapCenc::SDK::VaultLayout.atomic_write_text(target, '{"k":"値"}')
    assert_equal '{"k":"値"}', target.read(encoding: 'UTF-8')
  end

  def test_atomic_write_bytes_raises_vault_io_on_failure
    bad = Pathname('/this/path/does/not/exist/and/cant/be/created/file')
    err = assert_raises(RobocapCenc::SDK::Error) do
      RobocapCenc::SDK::VaultLayout.atomic_write_bytes(bad, 'x')
    end
    assert_equal RobocapCenc::SDK::ErrorCode::ERR_VAULT_IO, err.code
  end if Process.uid != 0
end
