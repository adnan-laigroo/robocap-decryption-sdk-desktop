# frozen_string_literal: true

require_relative 'sdk/version'
require_relative 'sdk/config'
require_relative 'sdk/errors'
require_relative 'sdk/rsa_key_meta'
require_relative 'sdk/rsa_oaep'
require_relative 'sdk/vault_layout'
require_relative 'sdk/key_vault'
require_relative 'sdk/ffmpeg_cli'
require_relative 'sdk/mp4_cenc'
require_relative 'sdk/ownership'
require_relative 'sdk/rsa_import'
require_relative 'sdk/rsa_delete'
require_relative 'sdk/decrypt_cenc'

module Robocap
  module SDK
    module_function

    def import_rsa_key_version(**kwargs)
      RsaImport.call(**kwargs)
    end

    def delete_rsa_key_version(**kwargs)
      RsaDelete.call(**kwargs)
    end

    def delete_rsa_key_dir(**kwargs)
      RsaDelete.call_with_dir(**kwargs)
    end

    def decrypt_cenc_mp4(**kwargs)
      DecryptCenc.call(**kwargs)
    end

    def verify_customer_private_key(**kwargs)
      Ownership.verify(**kwargs)
    end
  end
end
