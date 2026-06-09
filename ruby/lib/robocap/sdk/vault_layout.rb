# frozen_string_literal: true

require 'fileutils'
require 'pathname'
require 'tempfile'
require_relative 'errors'

module Robocap
  module SDK
    module VaultLayout
      module_function

      def ensure_private_dir(path)
        path = Pathname(path)
        FileUtils.mkdir_p(path)
        File.chmod(0o700, path) unless Gem.win_platform?
      end

      def atomic_write_bytes(target, data)
        target = Pathname(target)
        tmp = nil
        begin
          ensure_private_dir(target.parent)
          tmp = Tempfile.new(['.tmp_', ''], target.parent.to_s, binmode: true)
          tmp.write(data)
          tmp.flush
          tmp.fsync rescue nil
          tmp.close
          File.rename(tmp.path, target.to_s)
          tmp = nil
        rescue SystemCallError => exc
          raise Error.new(
            code: ErrorCode::ERR_VAULT_IO,
            message: "Failed to write #{target}",
            detail: { path: target.to_s, reason: exc.message },
          )
        ensure
          if tmp
            tmp.close unless tmp.closed?
            File.unlink(tmp.path) if File.exist?(tmp.path)
          end
        end
      end

      def atomic_write_text(target, text, encoding: 'UTF-8')
        atomic_write_bytes(target, text.encode(encoding).b)
      end
    end
  end
end
