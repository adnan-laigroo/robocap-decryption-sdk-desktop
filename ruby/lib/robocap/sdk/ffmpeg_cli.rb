# frozen_string_literal: true

require 'open3'
require 'fileutils'
require 'pathname'
require_relative 'config'
require_relative 'errors'

module Robocap
  module SDK
    module FfmpegCli
      module_function

      def open3_capture3(*args)
        Open3.capture3(*args)
      end

      def resolve_ffprobe_executable(explicit = nil)
        resolve_executable(
          explicit: explicit,
          tool: 'ffprobe',
          sibling_for: ENV['ROBOCAP_FFMPEG'],
          missing_code: ErrorCode::ERR_FFPROBE_NOT_FOUND,
          env_key: Config::FFPROBE_ENV_VAR,
        )
      end

      def resolve_ffmpeg_executable(explicit = nil)
        resolve_executable(
          explicit: explicit,
          tool: 'ffmpeg',
          sibling_for: nil,
          missing_code: ErrorCode::ERR_FFMPEG_NOT_FOUND,
          env_key: Config::FFMPEG_ENV_VAR,
        )
      end

      def decrypt_cenc_copy(input_mp4:, output_mp4:, cek_hex:, kid_hex: nil, ffmpeg_executable: nil)
        exe = resolve_ffmpeg_executable(ffmpeg_executable)
        FileUtils.mkdir_p(Pathname(output_mp4).parent)
        cmd = [exe, '-y', '-decryption_key', cek_hex]
        cmd.push('-decryption_kid', kid_hex) if kid_hex && !kid_hex.empty?
        cmd.push(
          '-i', input_mp4.to_s,
          '-map', '0',
          '-map_metadata', '0',
          '-c', 'copy',
          '-movflags', '+use_metadata_tags',
        )
        Mp4Cenc::CENC_STRIP_TAGS_ON_DECRYPT.each do |tag|
          cmd.push('-metadata', "#{tag}=")
        end
        cmd.push(output_mp4.to_s)

        begin
          _stdout, stderr, status = open3_capture3(*cmd)
        rescue SystemCallError => exc
          raise Error.new(
            code: ErrorCode::ERR_CENC_DECRYPT_FAILED,
            message: 'ffmpeg CENC decrypt subprocess failed',
            detail: { reason: exc.message },
          )
        end

        return if status.exitstatus.zero?
        raise Error.new(
          code: ErrorCode::ERR_CENC_DECRYPT_FAILED,
          message: "ffmpeg CENC decrypt failed: #{stderr}",
        )
      end

      class << self
        private

        def resolve_executable(explicit:, tool:, sibling_for:, missing_code:, env_key:)
          if explicit && !explicit.empty?
            path = Pathname(explicit)
            return path.to_s if path.file?
            return explicit unless explicit.include?('/') || explicit.include?('\\')
            raise Error.new(code: missing_code, message: "#{tool} executable not found: #{explicit}")
          end
          env_path = ENV[env_key]
          return env_path if env_path && Pathname(env_path).file?
          if sibling_for
            sib = Pathname(sibling_for)
            if sib.file?
              sibling = sib.dirname.join(tool + (sib.extname.downcase == '.exe' ? '.exe' : ''))
              return sibling.to_s if sibling.file?
            end
          end
          found = which(tool)
          return found if found
          raise Error.new(code: missing_code, message: "#{tool} executable not found in PATH")
        end

        def which(name)
          exts = ENV['PATHEXT'] ? ENV['PATHEXT'].split(File::PATH_SEPARATOR) : ['']
          ENV.fetch('PATH', '').split(File::PATH_SEPARATOR).each do |dir|
            exts.each do |ext|
              candidate = File.join(dir, name + ext)
              return candidate if File.executable?(candidate) && !File.directory?(candidate)
            end
          end
          nil
        end
      end
    end
  end
end
