# frozen_string_literal: true

require 'openssl'
require 'securerandom'
require_relative 'config'
require_relative 'errors'

module RobocapCenc
  module SDK
    module RSAOAEP
      module_function

      def cipher_len_for_key(key)
        key.n.num_bytes
      end

      def wrap_key(plaintext, public_key, plain_len:, cipher_len: nil)
        unless plaintext.bytesize == plain_len
          raise ArgumentError, "plaintext must be #{plain_len} bytes (got #{plaintext.bytesize})"
        end
        expected = cipher_len || cipher_len_for_key(public_key)
        ciphertext = public_key.encrypt(
          plaintext,
          rsa_padding_mode: 'oaep',
          rsa_oaep_md: 'sha256',
          rsa_mgf1_md: 'sha256',
        )
        unless ciphertext.bytesize == expected
          raise ArgumentError, "RSA ciphertext length #{ciphertext.bytesize} != #{expected}"
        end
        ciphertext
      end

      def unwrap_key(ciphertext, private_key,
                     plain_len:, cipher_len: nil,
                     decode_error: ErrorCode::ERR_K2_DECODE,
                     length_error: ErrorCode::ERR_K2_PLAINTEXT_LENGTH)
        expected = cipher_len || cipher_len_for_key(private_key)
        unless ciphertext.bytesize == expected
          raise Error.new(code: decode_error, message: "RSA ciphertext must be #{expected} bytes")
        end
        plaintext = begin
          private_key.decrypt(
            ciphertext,
            rsa_padding_mode: 'oaep',
            rsa_oaep_md: 'sha256',
            rsa_mgf1_md: 'sha256',
          )
        rescue OpenSSL::PKey::PKeyError, OpenSSL::PKey::RSAError => exc
          raise Error.new(code: decode_error, message: 'RSA-OAEP unwrap failed', detail: { reason: exc.message })
        end
        unless plaintext.bytesize == plain_len
          raise Error.new(code: length_error, message: "Decrypted key length #{plaintext.bytesize} != #{plain_len}")
        end
        plaintext
      end

      def wrap_aes_key(device_aes, public_key)
        wrap_key(
          device_aes, public_key,
          plain_len: Config::AES_KEY_BYTES,
          cipher_len: Config::RSA_CIPHERTEXT_BYTES,
        )
      end

      def unwrap_aes_key(ciphertext, private_key)
        unwrap_key(
          ciphertext, private_key,
          plain_len: Config::AES_KEY_BYTES,
          cipher_len: Config::RSA_CIPHERTEXT_BYTES,
        )
      end

      def wrap_cek(cek, public_key)
        wrap_key(
          cek, public_key,
          plain_len: Config::CEK_BYTES,
          cipher_len: Config::RSA_2048_CIPHERTEXT_BYTES,
        )
      end

      def unwrap_cek(ciphertext, private_key)
        unwrap_key(
          ciphertext, private_key,
          plain_len: Config::CEK_BYTES,
          cipher_len: Config::RSA_2048_CIPHERTEXT_BYTES,
          decode_error: ErrorCode::ERR_CENC_CEKA_WRAP,
          length_error: ErrorCode::ERR_CENC_CEKA_LENGTH,
        )
      end
    end
  end
end
