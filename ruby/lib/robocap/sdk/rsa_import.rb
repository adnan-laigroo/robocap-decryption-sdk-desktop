# frozen_string_literal: true

require 'pathname'
require_relative 'config'
require_relative 'key_vault'
require_relative 'rsa_key_meta'

module Robocap
  module SDK
    ImportRsaResult = Data.define(:customer_id, :rsa_key_version, :vault_rsa_dir)

    module RsaImport
      module_function

      def call(customer_id:, public_pem:, private_pem:, meta:, sdk_root: nil)
        root = Pathname(sdk_root || Config.default_sdk_root)
        vault = KeyVault.new(root)
        version = vault.import_rsa_version(
          customer_id: customer_id,
          public_pem: public_pem,
          private_pem: private_pem,
          meta: meta,
        )
        ImportRsaResult.new(
          customer_id: customer_id,
          rsa_key_version: version,
          vault_rsa_dir: vault.rsa_version_dir(customer_id, version),
        )
      end
    end
  end
end
