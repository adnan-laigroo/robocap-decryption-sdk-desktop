# frozen_string_literal: true

require 'digest'
require 'openssl'
require_relative 'config'
require_relative 'errors'
require_relative 'key_vault'

module RobocapCenc
  module SDK
    VerifiedKeyVersion = Data.define(:customer_id, :matched_rsa_key_version, :public_fingerprint)

    module Ownership
      module_function

      def spki_fingerprint(public_key)
        der = public_key.public_to_der
        Digest::SHA256.hexdigest(der)
      end

      def verify(customer_id:, user_private_pem:, key_vault: nil, sdk_root: nil)
        vault = key_vault || KeyVault.new(sdk_root || Config.default_sdk_root)

        unless vault.exists_customer?(customer_id)
          raise Error.new(
            code: ErrorCode::ERR_CUSTOMER_NOT_FOUND,
            message: "Customer #{customer_id} not found in key vault",
          )
        end

        priv = begin
          OpenSSL::PKey::RSA.new(user_private_pem)
        rescue OpenSSL::PKey::RSAError, OpenSSL::PKey::PKeyError => exc
          raise Error.new(
            code: ErrorCode::ERR_KEY_OWNERSHIP_FAILED,
            message: 'Failed to parse user private key',
            detail: { reason: exc.message },
          )
        end

        unless priv.private?
          raise Error.new(
            code: ErrorCode::ERR_KEY_OWNERSHIP_FAILED,
            message: 'User key is not an RSA private key',
          )
        end

        user_fp = spki_fingerprint(priv.public_key)

        vault.list_rsa_versions(customer_id).each do |version|
          archived = vault.get_public_key(customer_id, version)
          archived_fp = spki_fingerprint(archived)
          if archived_fp == user_fp
            return VerifiedKeyVersion.new(
              customer_id: customer_id,
              matched_rsa_key_version: version,
              public_fingerprint: user_fp,
            )
          end
        end

        raise Error.new(
          code: ErrorCode::ERR_KEY_OWNERSHIP_FAILED,
          message: "User private key does not match any archived key for #{customer_id}",
        )
      end
    end
  end
end
