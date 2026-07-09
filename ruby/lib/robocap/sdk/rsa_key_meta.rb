# frozen_string_literal: true

require 'json'
require 'time'
require_relative 'config'

module RobocapCenc
  module SDK
    class RsaKeyMeta < Data.define(:rsa_key_version, :effective_at, :device_id, :rsa_bits)
      def initialize(rsa_key_version:, effective_at:, device_id:, rsa_bits: Config::RSA_BITS)
        unless rsa_key_version.is_a?(Integer) && rsa_key_version >= 1
          raise ArgumentError, "rsa_key_version must be an integer >= 1 (got #{rsa_key_version.inspect})"
        end
        unless effective_at.is_a?(Time)
          raise ArgumentError, "effective_at must be a Time (got #{effective_at.class})"
        end
        unless device_id.is_a?(String)
          raise ArgumentError, "device_id must be a String (got #{device_id.class})"
        end
        unless rsa_bits.is_a?(Integer)
          raise ArgumentError, "rsa_bits must be an Integer (got #{rsa_bits.class})"
        end
        super
      end

      def to_json(*_args)
        JSON.generate(
          rsa_key_version: rsa_key_version,
          effective_at: effective_at.getutc.iso8601,
          device_id: device_id,
          rsa_bits: rsa_bits,
        )
      end

      def to_pretty_json
        JSON.pretty_generate(
          'rsa_key_version' => rsa_key_version,
          'effective_at' => effective_at.getutc.iso8601,
          'device_id' => device_id,
          'rsa_bits' => rsa_bits,
        )
      end

      def self.from_json(str)
        h = JSON.parse(str)
        new(
          rsa_key_version: h.fetch('rsa_key_version'),
          effective_at: Time.iso8601(h.fetch('effective_at')),
          device_id: h.fetch('device_id'),
          rsa_bits: h.fetch('rsa_bits', Config::RSA_BITS),
        )
      end
    end
  end
end
