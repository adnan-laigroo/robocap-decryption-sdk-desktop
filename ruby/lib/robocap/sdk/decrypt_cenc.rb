# frozen_string_literal: true

require 'pathname'
require_relative 'config'
require_relative 'errors'
require_relative 'key_vault'
require_relative 'mp4_cenc'
require_relative 'ownership'
require_relative 'ffmpeg_cli'
require_relative 'vault_layout'

module RobocapCenc
  module SDK
    DecryptCencResult = Data.define(:output_path, :customer_id, :rsa_key_version, :kid_hex)

    module DecryptCenc
      module_function

      def call(mp4_path:, user_private_pem:, output_dir:,
               sdk_root: nil, ffprobe_executable: nil, ffmpeg_executable: nil)
        mp4_path   = Pathname(mp4_path)
        output_dir = Pathname(output_dir)

        meta = Mp4Cenc.load_cenc_metadata(mp4_path, ffprobe_executable: ffprobe_executable)

        root = Pathname(sdk_root || Config.default_sdk_root)
        vault = KeyVault.new(root)

        unless vault.exists_customer?(meta.customer_id)
          raise Error.new(
            code: ErrorCode::ERR_CUSTOMER_NOT_FOUND,
            message: "Customer not found in vault: #{meta.customer_id}",
          )
        end

        Ownership.verify(
          customer_id: meta.customer_id,
          user_private_pem: user_private_pem,
          key_vault: vault,
        )

        trial = vault.trial_unwrap_cek(meta.customer_id, meta.cek_wrapped)
        cek_hex = trial.cek.unpack1('H*')

        VaultLayout.ensure_private_dir(output_dir)
        out_path = output_dir.join(mp4_path.basename)
        FfmpegCli.decrypt_cenc_copy(
          input_mp4: mp4_path,
          output_mp4: out_path,
          cek_hex: cek_hex,
          kid_hex: meta.kid_hex,
          ffmpeg_executable: ffmpeg_executable,
        )

        DecryptCencResult.new(
          output_path: out_path,
          customer_id: meta.customer_id,
          rsa_key_version: trial.rsa_key_version,
          kid_hex: meta.kid_hex,
        )
      end
    end
  end
end
