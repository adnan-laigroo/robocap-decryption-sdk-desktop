# frozen_string_literal: true

require 'pathname'

module Robocap
  module SDK
    module Config
      VAULT_KEYS_DIR  = 'vault/keys'
      VAULT_FILES_DIR = 'vault/files'

      RSA_BITS                  = 4096
      RSA_BITS_ALLOWED          = [2048, 4096].freeze
      RSA_PUBLIC_EXPONENT       = 65_537
      RSA_PADDING_SCHEME        = 'OAEP_SHA256'
      RSA_OAEP_HASH             = 'sha256'
      RSA_OAEP_MGF_HASH         = 'sha256'
      RSA_OAEP_LABEL            = nil
      RSA_CIPHERTEXT_BYTES      = 512
      RSA_2048_CIPHERTEXT_BYTES = 256

      CEK_BYTES       = 16
      AES_KEY_BYTES   = 32
      AES_NONCE_BYTES = 12
      AES_TAG_BYTES   = 16

      K2_MAGIC               = "RCK2".b.freeze
      K2_FORMAT_VERSION      = 1
      K2_HEADER_BYTES        = 9
      K2_BLOB_MIN_BYTES      = K2_HEADER_BYTES + RSA_CIPHERTEXT_BYTES
      META_FORMAT_VERSION    = 1

      DEFAULT_AES_BACKEND     = 'cryptography'
      AES_BACKEND_OPENSSL     = 'openssl_cli'
      OPENSSL_ENV_VAR         = 'ROBOCAP_OPENSSL'
      FFMPEG_ENV_VAR          = 'ROBOCAP_FFMPEG'
      FFPROBE_ENV_VAR         = 'ROBOCAP_FFPROBE'

      MASTER_KEY_FILENAME  = '.master_key'
      DEVICE_AES_FILENAME  = 'device_aes.enc.pem'

      CUSTOMER_ID_PATTERN = /\A[A-Za-z0-9_\-]+\z/

      module_function

      def default_sdk_root
        path = ENV['ROBOCAP_SDK_ROOT']
        path && !path.empty? ? Pathname(path) : Pathname(Dir.home).join('.robocap-sdk')
      end

      def validate_customer_id!(customer_id)
        unless customer_id.is_a?(String) && customer_id.match?(CUSTOMER_ID_PATTERN)
          raise ArgumentError,
                "Invalid customer_id: #{customer_id.inspect} " \
                '(allowed: alphanumeric, underscore, hyphen)'
        end
      end

      def keys_vault_root(sdk_root)
        Pathname(sdk_root).join(VAULT_KEYS_DIR)
      end

      def files_vault_root(sdk_root)
        Pathname(sdk_root).join(VAULT_FILES_DIR)
      end
    end
  end
end
