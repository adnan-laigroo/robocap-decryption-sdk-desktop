# frozen_string_literal: true

require 'fileutils'
require 'openssl'
require 'pathname'
require_relative 'config'
require_relative 'errors'
require_relative 'rsa_key_meta'
require_relative 'rsa_oaep'
require_relative 'vault_layout'

module RobocapCenc
  module SDK
    CekTrialUnwrapResult = Data.define(:cek, :rsa_key_version)

    class KeyVault
      RSA_VERSION_DIR_RE = /\Av(\d+)\z/

      def initialize(sdk_root)
        @sdk_root  = Pathname(sdk_root)
        @keys_root = Config.keys_vault_root(@sdk_root)
      end

      attr_reader :sdk_root

      def customer_root(customer_id)
        Config.validate_customer_id!(customer_id)
        @keys_root.join(customer_id)
      end

      def rsa_version_dir(customer_id, version)
        customer_root(customer_id).join('rsa', "v#{version}")
      end

      def public_pem(customer_id, version)
        rsa_version_dir(customer_id, version).join('public.pem')
      end

      def private_pem(customer_id, version)
        rsa_version_dir(customer_id, version).join('private.pem')
      end

      def rsa_meta_path(customer_id, version)
        rsa_version_dir(customer_id, version).join('meta.json')
      end

      def self.public_pem_path_for_dir(key_dir)
        Pathname(key_dir).join('public.pem')
      end

      def self.private_pem_path_for_dir(key_dir)
        Pathname(key_dir).join('private.pem')
      end

      def rsa_dir(customer_id)
        customer_root(customer_id).join('rsa')
      end

      def exists_customer?(customer_id)
        customer_root(customer_id).directory?
      end

      def list_rsa_versions(customer_id)
        rsa_dir = customer_root(customer_id).join('rsa')
        return [] unless rsa_dir.directory?
        rsa_dir.children.each_with_object([]) do |child, acc|
          next unless child.directory?
          m = RSA_VERSION_DIR_RE.match(child.basename.to_s)
          acc << m[1].to_i if m
        end.sort
      end

      def get_latest_rsa_version(customer_id)
        versions = list_rsa_versions(customer_id)
        if versions.empty?
          raise Error.new(
            code: ErrorCode::ERR_RSA_NOT_IMPORTED,
            message: "No RSA keys imported for customer #{customer_id}",
          )
        end
        versions.max
      end

      def get_public_key(customer_id, version)
        path = public_pem(customer_id, version)
        unless path.file?
          raise Error.new(
            code: ErrorCode::ERR_RSA_VERSION_MISSING,
            message: "RSA public key v#{version} not found for #{customer_id}",
          )
        end
        load_public_key_from(path)
      end

      def get_private_key(customer_id, version)
        path = private_pem(customer_id, version)
        unless path.file?
          raise Error.new(
            code: ErrorCode::ERR_RSA_VERSION_MISSING,
            message: "RSA private key v#{version} not found for #{customer_id}",
          )
        end
        load_private_key_from(path)
      end

      def get_latest_public_key(customer_id)
        get_public_key(customer_id, get_latest_rsa_version(customer_id))
      end

      def load_rsa_meta(customer_id, version)
        path = rsa_meta_path(customer_id, version)
        unless path.file?
          raise Error.new(
            code: ErrorCode::ERR_RSA_VERSION_MISSING,
            message: "RSA meta v#{version} not found for #{customer_id}",
          )
        end
        RsaKeyMeta.from_json(path.read(encoding: 'UTF-8'))
      end

      def import_rsa_version(customer_id:, public_pem:, private_pem:, meta:)
        Config.validate_customer_id!(customer_id)
        version = meta.rsa_key_version
        pub_key  = OpenSSL::PKey::RSA.new(public_pem)
        priv_key = OpenSSL::PKey::RSA.new(private_pem)

        if pub_key.private? || !priv_key.private?
          raise Error.new(code: ErrorCode::ERR_RSA_IMPORT_INVALID, message: 'Invalid RSA key pair PEM')
        end

        unless Config::RSA_BITS_ALLOWED.include?(meta.rsa_bits)
          raise Error.new(
            code: ErrorCode::ERR_INVALID_RSA_BITS,
            message: "RSA rsa_bits must be one of #{Config::RSA_BITS_ALLOWED}",
          )
        end

        actual_bits_pub  = pub_key.n.num_bits
        actual_bits_priv = priv_key.n.num_bits
        if actual_bits_pub != meta.rsa_bits || actual_bits_priv != meta.rsa_bits
          raise Error.new(
            code: ErrorCode::ERR_INVALID_RSA_BITS,
            message: "RSA keys must be #{meta.rsa_bits} bits",
          )
        end

        if pub_key.n != priv_key.n || pub_key.e != priv_key.e
          raise Error.new(
            code: ErrorCode::ERR_RSA_IMPORT_INVALID,
            message: 'Public and private key do not match',
          )
        end

        dir = rsa_version_dir(customer_id, version)
        if dir.exist?
          raise Error.new(
            code: ErrorCode::ERR_CUSTOMER_ALREADY_EXISTS,
            message: "RSA version v#{version} already exists for #{customer_id}",
          )
        end

        VaultLayout.ensure_private_dir(dir)
        VaultLayout.atomic_write_bytes(self.public_pem(customer_id, version),  public_pem)
        VaultLayout.atomic_write_bytes(self.private_pem(customer_id, version), private_pem)
        VaultLayout.atomic_write_text(rsa_meta_path(customer_id, version), meta.to_pretty_json)
        VaultLayout.ensure_private_dir(customer_root(customer_id))
        version
      end

      def delete_rsa_version(customer_id, version)
        Config.validate_customer_id!(customer_id)
        unless exists_customer?(customer_id)
          raise Error.new(
            code: ErrorCode::ERR_CUSTOMER_NOT_FOUND,
            message: "Customer not found: #{customer_id}",
          )
        end
        dir = rsa_version_dir(customer_id, version)
        unless dir.directory?
          raise Error.new(
            code: ErrorCode::ERR_RSA_VERSION_MISSING,
            message: "RSA version v#{version} not found for #{customer_id}",
          )
        end
        begin
          FileUtils.remove_entry_secure(dir)
        rescue SystemCallError => exc
          raise Error.new(
            code: ErrorCode::ERR_VAULT_IO,
            message: "Failed to delete RSA version v#{version}: #{exc.message}",
          )
        end
      end

      def list_rsa_key_dirs(customer_id)
        Config.validate_customer_id!(customer_id)
        dir = rsa_dir(customer_id)
        return [] unless dir.directory?
        dir.children.sort_by { |c| c.basename.to_s.downcase }.filter_map do |child|
          next nil unless valid_rsa_key_dir?(child)
          Pathname(child.realpath)
        end
      end

      def delete_rsa_key_dir(customer_id, key_dir)
        Config.validate_customer_id!(customer_id)
        unless exists_customer?(customer_id)
          raise Error.new(
            code: ErrorCode::ERR_CUSTOMER_NOT_FOUND,
            message: "Customer not found: #{customer_id}",
          )
        end
        resolved_rsa_dir = Pathname(rsa_dir(customer_id).realpath)
        resolved = Pathname(key_dir).expand_path
        resolved = Pathname(resolved.realpath) if resolved.exist?
        unless resolved.parent == resolved_rsa_dir
          raise Error.new(
            code: ErrorCode::ERR_RSA_VERSION_MISSING,
            message: "Key folder is not under rsa/ for #{customer_id}",
          )
        end
        unless valid_rsa_key_dir?(resolved)
          raise Error.new(
            code: ErrorCode::ERR_RSA_VERSION_MISSING,
            message: "Key folder missing public.pem or private.pem: #{resolved.basename}",
          )
        end
        begin
          FileUtils.remove_entry_secure(resolved)
        rescue SystemCallError => exc
          raise Error.new(
            code: ErrorCode::ERR_VAULT_IO,
            message: "Failed to delete key folder #{resolved.basename}: #{exc.message}",
          )
        end
      end

      def trial_unwrap_cek(customer_id, cek_wrapped)
        Config.validate_customer_id!(customer_id)
        unless cek_wrapped.bytesize == Config::RSA_2048_CIPHERTEXT_BYTES
          raise Error.new(
            code: ErrorCode::ERR_CENC_CEKA_WRAP,
            message: "Wrapped CEK must be #{Config::RSA_2048_CIPHERTEXT_BYTES} bytes",
          )
        end

        eligible = list_rsa_versions(customer_id).filter_map do |version|
          meta = load_rsa_meta(customer_id, version)
          next nil unless meta.rsa_bits == 2048
          priv = get_private_key(customer_id, version)
          next nil unless priv.n.num_bits == 2048
          [version, priv]
        end

        if eligible.empty?
          raise Error.new(
            code: ErrorCode::ERR_CENC_CEKA_TRIAL_FAILED,
            message: "No 2048-bit RSA keys available for trial unwrap: #{customer_id}",
          )
        end

        first_success = nil
        eligible.each do |version, priv|
          begin
            cek = RSAOAEP.unwrap_cek(cek_wrapped, priv)
          rescue Error
            next
          end
          return first_success if first_success
          first_success = CekTrialUnwrapResult.new(cek: cek, rsa_key_version: version)
        end

        unless first_success
          raise Error.new(
            code: ErrorCode::ERR_CENC_CEKA_TRIAL_FAILED,
            message: "CEK trial unwrap failed for all vault versions: #{customer_id}",
          )
        end
        first_success
      end

      private

      def valid_rsa_key_dir?(path)
        path = Pathname(path)
        path.directory? &&
          self.class.public_pem_path_for_dir(path).file? &&
          self.class.private_pem_path_for_dir(path).file?
      end

      def load_public_key_from(path)
        key = OpenSSL::PKey::RSA.new(path.binread)
        if key.private?
          raise Error.new(code: ErrorCode::ERR_RSA_IMPORT_INVALID, message: 'PEM is not an RSA public key')
        end
        key
      end

      def load_private_key_from(path)
        key = OpenSSL::PKey::RSA.new(path.binread)
        unless key.private?
          raise Error.new(code: ErrorCode::ERR_RSA_IMPORT_INVALID, message: 'PEM is not an RSA private key')
        end
        key
      end
    end
  end
end
