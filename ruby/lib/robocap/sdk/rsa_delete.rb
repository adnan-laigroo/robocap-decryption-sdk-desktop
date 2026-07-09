# frozen_string_literal: true

require 'pathname'
require_relative 'config'
require_relative 'key_vault'

module RobocapCenc
  module SDK
    DeleteRsaResult = Data.define(:customer_id, :folder_name, :key_dir)

    module RsaDelete
      module_function

      def call(customer_id:, rsa_key_version:, sdk_root: nil)
        root = Pathname(sdk_root || Config.default_sdk_root)
        vault = KeyVault.new(root)
        key_dir = vault.rsa_version_dir(customer_id, rsa_key_version)
        vault.delete_rsa_version(customer_id, rsa_key_version)
        DeleteRsaResult.new(
          customer_id: customer_id,
          folder_name: key_dir.basename.to_s,
          key_dir: key_dir,
        )
      end

      def call_with_dir(customer_id:, key_dir:, sdk_root: nil)
        root = Pathname(sdk_root || Config.default_sdk_root)
        vault = KeyVault.new(root)
        resolved = Pathname(key_dir).expand_path
        resolved = Pathname(resolved.realpath) if resolved.exist?
        folder_name = resolved.basename.to_s
        vault.delete_rsa_key_dir(customer_id, resolved)
        DeleteRsaResult.new(
          customer_id: customer_id,
          folder_name: folder_name,
          key_dir: resolved,
        )
      end
    end
  end
end
