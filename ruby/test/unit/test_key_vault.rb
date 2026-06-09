# frozen_string_literal: true

require_relative '../test_helper'
require_relative '../helpers'
require 'robocap/sdk/config'
require 'robocap/sdk/errors'
require 'robocap/sdk/rsa_key_meta'
require 'robocap/sdk/rsa_oaep'
require 'robocap/sdk/vault_layout'
require 'robocap/sdk/key_vault'

class TestKeyVault < Minitest::Test
  include TestHelpers

  def setup
    @tmp = Pathname(Dir.mktmpdir('robocap-vault-'))
    @vault = Robocap::SDK::KeyVault.new(@tmp)
  end

  def teardown
    FileUtils.remove_entry(@tmp) if @tmp&.directory?
  end

  def make_meta(version: 1, bits: 2048)
    Robocap::SDK::RsaKeyMeta.new(
      rsa_key_version: version,
      effective_at: Time.utc(2026, 1, 1),
      device_id: 'CUST_TEST',
      rsa_bits: bits,
    )
  end

  def test_paths_compose_correctly
    assert_equal @tmp.join('vault/keys/c1'), @vault.customer_root('c1')
    assert_equal @tmp.join('vault/keys/c1/rsa/v3'), @vault.rsa_version_dir('c1', 3)
    assert_equal @tmp.join('vault/keys/c1/rsa/v3/public.pem'), @vault.public_pem('c1', 3)
    assert_equal @tmp.join('vault/keys/c1/rsa/v3/private.pem'), @vault.private_pem('c1', 3)
    assert_equal @tmp.join('vault/keys/c1/rsa/v3/meta.json'), @vault.rsa_meta_path('c1', 3)
  end

  def test_public_pem_path_for_dir_static
    key_dir = @tmp.join('vault/keys/c1/rsa/v3')
    assert_equal key_dir.join('public.pem'),
                 Robocap::SDK::KeyVault.public_pem_path_for_dir(key_dir)
  end

  def test_private_pem_path_for_dir_static
    key_dir = @tmp.join('vault/keys/c1/rsa/v3')
    assert_equal key_dir.join('private.pem'),
                 Robocap::SDK::KeyVault.private_pem_path_for_dir(key_dir)
  end

  def test_rsa_dir_path
    assert_equal @tmp.join('vault/keys/c1/rsa'), @vault.rsa_dir('c1')
  end

  def test_exists_customer_initially_false
    refute @vault.exists_customer?('c1')
  end

  def test_import_then_exists_customer
    pub, priv = generate_rsa_keypair(bits: 2048)
    @vault.import_rsa_version(
      customer_id: 'c1', public_pem: pub, private_pem: priv, meta: make_meta,
    )
    assert @vault.exists_customer?('c1')
  end

  def test_import_writes_three_files
    pub, priv = generate_rsa_keypair(bits: 2048)
    @vault.import_rsa_version(
      customer_id: 'c1', public_pem: pub, private_pem: priv, meta: make_meta,
    )
    assert @vault.public_pem('c1', 1).file?
    assert @vault.private_pem('c1', 1).file?
    assert @vault.rsa_meta_path('c1', 1).file?
  end

  def test_import_persists_meta_in_python_compatible_json
    pub, priv = generate_rsa_keypair(bits: 2048)
    @vault.import_rsa_version(
      customer_id: 'c1', public_pem: pub, private_pem: priv, meta: make_meta,
    )
    json = @vault.rsa_meta_path('c1', 1).read
    parsed = JSON.parse(json)
    assert_equal 1, parsed['rsa_key_version']
    assert_equal 'CUST_TEST', parsed['device_id']
    assert_equal 2048, parsed['rsa_bits']
    assert_match(/\A2026-01-01T00:00:00/, parsed['effective_at'])
  end

  def test_list_rsa_versions_sorted
    %w[v3 v1 v2].each do |v|
      pub, priv = generate_rsa_keypair(bits: 2048)
      @vault.import_rsa_version(
        customer_id: 'c1', public_pem: pub, private_pem: priv,
        meta: make_meta(version: v[1..].to_i),
      )
    end
    assert_equal [1, 2, 3], @vault.list_rsa_versions('c1')
  end

  def test_list_rsa_versions_empty_when_no_customer
    assert_equal [], @vault.list_rsa_versions('missing')
  end

  def test_get_latest_rsa_version_raises_when_empty
    pub, priv = generate_rsa_keypair(bits: 2048)
    @vault.import_rsa_version(
      customer_id: 'c1', public_pem: pub, private_pem: priv, meta: make_meta,
    )
    err = assert_raises(Robocap::SDK::Error) { @vault.get_latest_rsa_version('c2') }
    assert_equal Robocap::SDK::ErrorCode::ERR_RSA_NOT_IMPORTED, err.code
  end

  def test_import_rejects_invalid_bits
    pub, priv = generate_rsa_keypair(bits: 2048)
    err = assert_raises(Robocap::SDK::Error) do
      @vault.import_rsa_version(
        customer_id: 'c1', public_pem: pub, private_pem: priv,
        meta: make_meta(bits: 1024),
      )
    end
    assert_equal Robocap::SDK::ErrorCode::ERR_INVALID_RSA_BITS, err.code
  end

  def test_import_rejects_mismatched_pair
    pub_a, _ = generate_rsa_keypair(bits: 2048)
    _, priv_b = generate_rsa_keypair(bits: 2048)
    err = assert_raises(Robocap::SDK::Error) do
      @vault.import_rsa_version(
        customer_id: 'c1', public_pem: pub_a, private_pem: priv_b, meta: make_meta,
      )
    end
    assert_equal Robocap::SDK::ErrorCode::ERR_RSA_IMPORT_INVALID, err.code
  end

  def test_import_rejects_duplicate_version
    pub, priv = generate_rsa_keypair(bits: 2048)
    @vault.import_rsa_version(
      customer_id: 'c1', public_pem: pub, private_pem: priv, meta: make_meta,
    )
    err = assert_raises(Robocap::SDK::Error) do
      @vault.import_rsa_version(
        customer_id: 'c1', public_pem: pub, private_pem: priv, meta: make_meta,
      )
    end
    assert_equal Robocap::SDK::ErrorCode::ERR_CUSTOMER_ALREADY_EXISTS, err.code
  end

  def test_delete_rsa_version_removes_dir
    pub, priv = generate_rsa_keypair(bits: 2048)
    @vault.import_rsa_version(
      customer_id: 'c1', public_pem: pub, private_pem: priv, meta: make_meta,
    )
    @vault.delete_rsa_version('c1', 1)
    refute @vault.rsa_version_dir('c1', 1).exist?
    assert_equal [], @vault.list_rsa_versions('c1')
  end

  def test_delete_unknown_customer_raises
    err = assert_raises(Robocap::SDK::Error) { @vault.delete_rsa_version('missing', 1) }
    assert_equal Robocap::SDK::ErrorCode::ERR_CUSTOMER_NOT_FOUND, err.code
  end

  def test_delete_unknown_version_raises
    pub, priv = generate_rsa_keypair(bits: 2048)
    @vault.import_rsa_version(
      customer_id: 'c1', public_pem: pub, private_pem: priv, meta: make_meta,
    )
    err = assert_raises(Robocap::SDK::Error) { @vault.delete_rsa_version('c1', 99) }
    assert_equal Robocap::SDK::ErrorCode::ERR_RSA_VERSION_MISSING, err.code
  end

  def test_get_public_key_returns_rsa_public_key
    pub, priv = generate_rsa_keypair(bits: 2048)
    @vault.import_rsa_version(
      customer_id: 'c1', public_pem: pub, private_pem: priv, meta: make_meta,
    )
    key = @vault.get_public_key('c1', 1)
    assert_kind_of OpenSSL::PKey::RSA, key
    refute key.private?
  end

  def test_trial_unwrap_cek_finds_correct_version
    pub_v1, priv_v1 = generate_rsa_keypair(bits: 2048)
    pub_v2, priv_v2 = generate_rsa_keypair(bits: 2048)
    @vault.import_rsa_version(customer_id: 'c1', public_pem: pub_v1, private_pem: priv_v1, meta: make_meta(version: 1))
    @vault.import_rsa_version(customer_id: 'c1', public_pem: pub_v2, private_pem: priv_v2, meta: make_meta(version: 2))

    cek = SecureRandom.bytes(Robocap::SDK::Config::CEK_BYTES)
    wrapped_with_v2 = Robocap::SDK::RSAOAEP.wrap_cek(cek, OpenSSL::PKey::RSA.new(pub_v2))
    trial = @vault.trial_unwrap_cek('c1', wrapped_with_v2)
    assert_equal cek, trial.cek
    assert_equal 2, trial.rsa_key_version
  end

  def test_trial_unwrap_cek_rejects_wrong_length
    pub, priv = generate_rsa_keypair(bits: 2048)
    @vault.import_rsa_version(customer_id: 'c1', public_pem: pub, private_pem: priv, meta: make_meta)
    err = assert_raises(Robocap::SDK::Error) { @vault.trial_unwrap_cek('c1', 'short') }
    assert_equal Robocap::SDK::ErrorCode::ERR_CENC_CEKA_WRAP, err.code
  end

  def test_trial_unwrap_cek_skips_4096
    pub_2048, priv_2048 = generate_rsa_keypair(bits: 2048)
    pub_4096, priv_4096 = generate_rsa_keypair(bits: 4096)
    @vault.import_rsa_version(customer_id: 'c1', public_pem: pub_4096, private_pem: priv_4096, meta: make_meta(version: 1, bits: 4096))
    @vault.import_rsa_version(customer_id: 'c1', public_pem: pub_2048, private_pem: priv_2048, meta: make_meta(version: 2, bits: 2048))
    cek = SecureRandom.bytes(Robocap::SDK::Config::CEK_BYTES)
    wrapped = Robocap::SDK::RSAOAEP.wrap_cek(cek, OpenSSL::PKey::RSA.new(pub_2048))
    trial = @vault.trial_unwrap_cek('c1', wrapped)
    assert_equal 2, trial.rsa_key_version
  end

  def test_list_rsa_key_dirs_returns_empty_when_no_customer
    assert_equal [], @vault.list_rsa_key_dirs('missing')
  end

  def test_list_rsa_key_dirs_sorts_case_insensitively
    [1, 2, 3].each do |v|
      pub, priv = generate_rsa_keypair(bits: 2048)
      @vault.import_rsa_version(
        customer_id: 'c1', public_pem: pub, private_pem: priv,
        meta: make_meta(version: v),
      )
    end
    dirs = @vault.list_rsa_key_dirs('c1')
    assert_equal %w[v1 v2 v3], dirs.map { |d| d.basename.to_s }
  end

  def test_list_rsa_key_dirs_skips_invalid_dirs
    pub, priv = generate_rsa_keypair(bits: 2048)
    @vault.import_rsa_version(
      customer_id: 'c1', public_pem: pub, private_pem: priv, meta: make_meta,
    )
    # Add a sibling dir under rsa/ with NO pem files.
    FileUtils.mkdir_p(@vault.rsa_dir('c1').join('vbogus'))
    dirs = @vault.list_rsa_key_dirs('c1')
    assert_equal %w[v1], dirs.map { |d| d.basename.to_s }
  end

  def test_delete_rsa_key_dir_removes_dir
    pub, priv = generate_rsa_keypair(bits: 2048)
    @vault.import_rsa_version(
      customer_id: 'c1', public_pem: pub, private_pem: priv, meta: make_meta,
    )
    target = @vault.rsa_version_dir('c1', 1)
    @vault.delete_rsa_key_dir('c1', target)
    refute target.exist?
    assert_equal [], @vault.list_rsa_versions('c1')
  end

  def test_delete_rsa_key_dir_rejects_unknown_customer
    target = @vault.rsa_version_dir('c1', 1)
    err = assert_raises(Robocap::SDK::Error) do
      @vault.delete_rsa_key_dir('missing', target)
    end
    assert_equal Robocap::SDK::ErrorCode::ERR_CUSTOMER_NOT_FOUND, err.code
  end

  def test_delete_rsa_key_dir_rejects_path_outside_rsa_dir
    pub, priv = generate_rsa_keypair(bits: 2048)
    @vault.import_rsa_version(
      customer_id: 'c1', public_pem: pub, private_pem: priv, meta: make_meta,
    )
    # A path under vault/keys/c1/ but NOT under rsa/.
    stray = @vault.customer_root('c1').join('stray')
    FileUtils.mkdir_p(stray)
    FileUtils.touch(stray.join('public.pem'))
    FileUtils.touch(stray.join('private.pem'))
    err = assert_raises(Robocap::SDK::Error) do
      @vault.delete_rsa_key_dir('c1', stray)
    end
    assert_equal Robocap::SDK::ErrorCode::ERR_RSA_VERSION_MISSING, err.code
  end

  def test_delete_rsa_key_dir_rejects_dir_missing_pems
    pub, priv = generate_rsa_keypair(bits: 2048)
    @vault.import_rsa_version(
      customer_id: 'c1', public_pem: pub, private_pem: priv, meta: make_meta,
    )
    empty_dir = @vault.rsa_dir('c1').join('vbogus')
    FileUtils.mkdir_p(empty_dir)
    err = assert_raises(Robocap::SDK::Error) do
      @vault.delete_rsa_key_dir('c1', empty_dir)
    end
    assert_equal Robocap::SDK::ErrorCode::ERR_RSA_VERSION_MISSING, err.code
  end

  def test_trial_unwrap_cek_no_eligible_keys
    pub_4096, priv_4096 = generate_rsa_keypair(bits: 4096)
    @vault.import_rsa_version(customer_id: 'c1', public_pem: pub_4096, private_pem: priv_4096, meta: make_meta(bits: 4096))
    bogus = SecureRandom.bytes(Robocap::SDK::Config::RSA_2048_CIPHERTEXT_BYTES)
    err = assert_raises(Robocap::SDK::Error) { @vault.trial_unwrap_cek('c1', bogus) }
    assert_equal Robocap::SDK::ErrorCode::ERR_CENC_CEKA_TRIAL_FAILED, err.code
  end
end
