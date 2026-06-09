# frozen_string_literal: true

require 'base64'
require 'json'
require 'pathname'
require_relative 'config'
require_relative 'errors'
require_relative 'ffmpeg_cli'

module Robocap
  module SDK
    CencMp4Metadata = Data.define(:customer_id, :cek_wrapped, :kid_hex)

    module Mp4Cenc
      CEKA_TAG                 = 'cenc_cek_wrapped_b64'
      CUSTOMER_ID_TAG          = 'cenc_customer_id'
      CUSTOMER_ID_FALLBACK_TAG = 'username'
      KID_TAG                  = 'cenc_kid_hex'

      CENC_WRAPPED_ALGO_TAG = 'cenc_wrapped_algo'

      CENC_STRIP_TAGS_ON_DECRYPT = [
        CEKA_TAG,
        CENC_WRAPPED_ALGO_TAG,
      ].freeze

      module_function

      def read_format_tags(mp4_path, ffprobe_executable: nil)
        path = Pathname(mp4_path).expand_path
        unless path.file?
          raise Error.new(
            code: ErrorCode::ERR_CENC_TAGS_MISSING,
            message: "MP4 file not found: #{path}",
          )
        end
        exe = FfmpegCli.resolve_ffprobe_executable(ffprobe_executable)
        stdout, stderr, status = FfmpegCli.open3_capture3(
          exe, '-v', 'error', '-show_format', '-print_format', 'json', path.to_s,
        )
        unless status.exitstatus.zero?
          raise Error.new(
            code: ErrorCode::ERR_CENC_FFPROBE_FAILED,
            message: "ffprobe failed: #{stderr}",
          )
        end

        payload = parse_ffprobe_json(stdout)
        fmt = payload['format']
        unless fmt.is_a?(Hash)
          raise Error.new(
            code: ErrorCode::ERR_CENC_TAGS_MISSING,
            message: 'ffprobe output missing format section',
          )
        end
        tags = fmt['tags']
        unless tags.is_a?(Hash)
          raise Error.new(
            code: ErrorCode::ERR_CENC_TAGS_MISSING,
            message: 'MP4 has no format metadata tags',
          )
        end
        tags.transform_keys(&:to_s).transform_values(&:to_s)
      end

      def parse_cenc_metadata_from_tags(tags)
        unless tags[CEKA_TAG] && !tags[CEKA_TAG].empty?
          raise Error.new(
            code: ErrorCode::ERR_CENC_TAGS_MISSING,
            message: "Missing CENC tags: #{CEKA_TAG}",
          )
        end

        customer_id = resolve_customer_id(tags)

        begin
          cek_wrapped = Base64.strict_decode64(tags[CEKA_TAG])
        rescue ArgumentError
          raise Error.new(
            code: ErrorCode::ERR_CENC_TAGS_MISSING,
            message: 'Invalid cenc_cek_wrapped_b64 Base64',
          )
        end

        unless cek_wrapped.bytesize == Config::RSA_2048_CIPHERTEXT_BYTES
          raise Error.new(
            code: ErrorCode::ERR_CENC_CEKA_WRAP,
            message: "Wrapped CEK must be #{Config::RSA_2048_CIPHERTEXT_BYTES} bytes",
          )
        end

        kid = tags[KID_TAG]
        kid = kid.strip.downcase if kid
        kid = nil if kid && kid.empty?

        CencMp4Metadata.new(customer_id: customer_id, cek_wrapped: cek_wrapped, kid_hex: kid)
      end

      def load_cenc_metadata(mp4_path, ffprobe_executable: nil)
        parse_cenc_metadata_from_tags(
          read_format_tags(mp4_path, ffprobe_executable: ffprobe_executable),
        )
      end

      def has_cenc_tags(mp4_path, ffprobe_executable: nil)
        tags = read_format_tags(mp4_path, ffprobe_executable: ffprobe_executable)
        return false unless tags[CEKA_TAG] && !tags[CEKA_TAG].empty?
        has_customer_id_source?(tags)
      rescue Error
        false
      end

      class << self
        private

        def parse_ffprobe_json(raw)
          JSON.parse(raw)
        rescue JSON::ParserError
          raise Error.new(
            code: ErrorCode::ERR_CENC_FFPROBE_FAILED,
            message: 'ffprobe returned invalid JSON',
          )
        end

        def resolve_customer_id(tags)
          raw = tags[CUSTOMER_ID_TAG] || tags[CUSTOMER_ID_FALLBACK_TAG]
          if raw.nil? || raw.strip.empty?
            raise Error.new(
              code: ErrorCode::ERR_CENC_TAGS_MISSING,
              message: "Missing CENC customer id: #{CUSTOMER_ID_TAG} or #{CUSTOMER_ID_FALLBACK_TAG} tag required",
            )
          end
          customer = raw.strip
          begin
            Config.validate_customer_id!(customer)
          rescue ArgumentError
            raise Error.new(
              code: ErrorCode::ERR_CENC_CUSTOMER_ID_INVALID,
              message: "Invalid customer id: #{customer.inspect}",
            )
          end
          customer
        end

        def has_customer_id_source?(tags)
          [CUSTOMER_ID_TAG, CUSTOMER_ID_FALLBACK_TAG].any? do |k|
            v = tags[k]
            v && !v.strip.empty?
          end
        end
      end
    end
  end
end
