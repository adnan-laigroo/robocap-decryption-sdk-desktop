# frozen_string_literal: true

require 'json'
require 'optparse'
require 'pathname'
require 'time'
require_relative '../sdk'

module Robocap
  module SDK
    module CLI
      module_function

      USAGE = <<~TXT
        Usage: robocap-sdk <command> [options]

        Commands:
          import-rsa     Import an RSA key pair into the vault
          delete-rsa     Delete one RSA key version from the vault
          decrypt-cenc   Decrypt a CENC MP4 (RSA-OAEP CEK unwrap + ffmpeg)

        Run `robocap-sdk <command> --help` for command-specific options.
      TXT

      def run(argv)
        command = argv.shift
        case command
        when 'import-rsa'   then with_error_handling { cmd_import_rsa(argv) }
        when 'delete-rsa'   then with_error_handling { cmd_delete_rsa(argv) }
        when 'decrypt-cenc' then with_error_handling { cmd_decrypt_cenc(argv) }
        when '--help', '-h', nil
          warn(USAGE)
          0
        else
          warn("Unknown command: #{command}\n\n#{USAGE}")
          2
        end
      end

      def with_error_handling
        yield
        0
      rescue Error => exc
        warn(JSON.generate(exc.to_h))
        1
      rescue OptionParser::ParseError => exc
        warn(exc.message)
        2
      end

      def emit_json(data)
        puts JSON.generate(data)
      end

      def cmd_import_rsa(argv)
        opts = {}
        OptionParser.new do |o|
          o.banner = 'Usage: robocap-sdk import-rsa [options]'
          o.on('--customer-id CID')       { |v| opts[:customer_id] = v }
          o.on('--public-key PATH')       { |v| opts[:public_key] = Pathname(v) }
          o.on('--private-key PATH')      { |v| opts[:private_key] = Pathname(v) }
          o.on('--rsa-key-version N', Integer) { |v| opts[:rsa_key_version] = v }
          o.on('--rsa-bits N',     ['2048', '4096']) { |v| opts[:rsa_bits] = v.to_i }
          o.on('--device-id ID')          { |v| opts[:device_id] = v }
          o.on('--effective-at ISO8601')  { |v| opts[:effective_at] = v }
          o.on('--sdk-root PATH')         { |v| opts[:sdk_root] = Pathname(v) }
        end.parse!(argv)

        require_opts!(opts, %i[customer_id public_key private_key rsa_key_version])
        opts[:rsa_bits] ||= 2048
        eff = opts[:effective_at] ? Time.iso8601(opts[:effective_at]) : Time.now.utc
        meta = RsaKeyMeta.new(
          rsa_key_version: opts[:rsa_key_version],
          effective_at: eff,
          device_id: opts[:device_id] || opts[:customer_id],
          rsa_bits: opts[:rsa_bits],
        )
        result = Robocap::SDK.import_rsa_key_version(
          customer_id: opts[:customer_id],
          public_pem: opts[:public_key].binread,
          private_pem: opts[:private_key].binread,
          meta: meta,
          sdk_root: opts[:sdk_root],
        )
        emit_json(
          status: 'ok',
          customer_id: result.customer_id,
          rsa_key_version: result.rsa_key_version,
          vault_rsa_dir: result.vault_rsa_dir.to_s,
        )
      end

      def cmd_delete_rsa(argv)
        opts = {}
        OptionParser.new do |o|
          o.banner = 'Usage: robocap-sdk delete-rsa [options]'
          o.on('--customer-id CID') { |v| opts[:customer_id] = v }
          o.on('--rsa-key-version N', Integer) { |v| opts[:rsa_key_version] = v }
          o.on('--sdk-root PATH')   { |v| opts[:sdk_root] = Pathname(v) }
        end.parse!(argv)

        require_opts!(opts, %i[customer_id rsa_key_version])
        result = Robocap::SDK.delete_rsa_key_version(
          customer_id: opts[:customer_id],
          rsa_key_version: opts[:rsa_key_version],
          sdk_root: opts[:sdk_root],
        )
        emit_json(
          status: 'ok',
          customer_id: result.customer_id,
          rsa_key_version: opts[:rsa_key_version],
          folder_name: result.folder_name,
        )
      end

      def cmd_decrypt_cenc(argv)
        opts = {}
        OptionParser.new do |o|
          o.banner = 'Usage: robocap-sdk decrypt-cenc [options]'
          o.on('--mp4-path PATH')     { |v| opts[:mp4_path] = Pathname(v) }
          o.on('--private-key PATH')  { |v| opts[:private_key] = Pathname(v) }
          o.on('--output-dir PATH')   { |v| opts[:output_dir] = Pathname(v) }
          o.on('--sdk-root PATH')     { |v| opts[:sdk_root] = Pathname(v) }
          o.on('--ffmpeg PATH')       { |v| opts[:ffmpeg_executable] = v }
          o.on('--ffprobe PATH')      { |v| opts[:ffprobe_executable] = v }
        end.parse!(argv)

        require_opts!(opts, %i[mp4_path private_key output_dir])
        opts[:output_dir].mkpath
        result = Robocap::SDK.decrypt_cenc_mp4(
          mp4_path: opts[:mp4_path],
          user_private_pem: opts[:private_key].binread,
          output_dir: opts[:output_dir],
          sdk_root: opts[:sdk_root],
          ffmpeg_executable: opts[:ffmpeg_executable],
          ffprobe_executable: opts[:ffprobe_executable],
        )
        emit_json(
          status: 'ok',
          output_path: result.output_path.to_s,
          customer_id: result.customer_id,
          rsa_key_version: result.rsa_key_version,
          kid_hex: result.kid_hex,
        )
      end

      def require_opts!(opts, keys)
        missing = keys.reject { |k| opts.key?(k) }
        return if missing.empty?
        raise OptionParser::ParseError, "missing required option(s): #{missing.map { |k| "--#{k.to_s.tr('_', '-')}" }.join(', ')}"
      end
    end
  end
end
