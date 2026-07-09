# frozen_string_literal: true

require_relative '../test_helper'
require 'robocap/sdk/config'
require 'robocap/sdk/errors'
require 'robocap/sdk/rsa_oaep'

class TestRsaOaep < Minitest::Test
  CEK_BYTES                 = RobocapCenc::SDK::Config::CEK_BYTES
  AES_KEY_BYTES             = RobocapCenc::SDK::Config::AES_KEY_BYTES
  RSA_2048_CIPHERTEXT_BYTES = RobocapCenc::SDK::Config::RSA_2048_CIPHERTEXT_BYTES
  RSA_CIPHERTEXT_BYTES      = RobocapCenc::SDK::Config::RSA_CIPHERTEXT_BYTES

  def keypair(bits)
    rsa = OpenSSL::PKey::RSA.generate(bits, 0x10001)
    [rsa.public_key, rsa]
  end

  def test_rsa_wrap_unwrap_roundtrip_2048
    pub, priv = keypair(2048)
    payload = SecureRandom.bytes(CEK_BYTES)
    wrapped = RobocapCenc::SDK::RSAOAEP.wrap_key(
      payload, pub, plain_len: CEK_BYTES, cipher_len: RSA_2048_CIPHERTEXT_BYTES,
    )
    assert_equal RSA_2048_CIPHERTEXT_BYTES, wrapped.bytesize
    unwrapped = RobocapCenc::SDK::RSAOAEP.unwrap_key(
      wrapped, priv, plain_len: CEK_BYTES, cipher_len: RSA_2048_CIPHERTEXT_BYTES,
    )
    assert_equal payload, unwrapped
  end

  def test_rsa_wrap_unwrap_roundtrip_4096
    pub, priv = keypair(4096)
    payload = SecureRandom.bytes(32)
    wrapped = RobocapCenc::SDK::RSAOAEP.wrap_key(payload, pub, plain_len: 32, cipher_len: 512)
    assert_equal 512, wrapped.bytesize
    assert_equal payload,
                 RobocapCenc::SDK::RSAOAEP.unwrap_key(wrapped, priv, plain_len: 32, cipher_len: 512)
  end

  def test_wrap_unwrap_cek
    pub, priv = keypair(2048)
    cek = SecureRandom.bytes(CEK_BYTES)
    wrapped = RobocapCenc::SDK::RSAOAEP.wrap_cek(cek, pub)
    assert_equal RSA_2048_CIPHERTEXT_BYTES, wrapped.bytesize
    assert_equal cek, RobocapCenc::SDK::RSAOAEP.unwrap_cek(wrapped, priv)
  end

  def test_wrap_unwrap_aes_key
    pub, priv = keypair(4096)
    aes = SecureRandom.bytes(AES_KEY_BYTES)
    wrapped = RobocapCenc::SDK::RSAOAEP.wrap_aes_key(aes, pub)
    assert_equal RSA_CIPHERTEXT_BYTES, wrapped.bytesize
    assert_equal aes, RobocapCenc::SDK::RSAOAEP.unwrap_aes_key(wrapped, priv)
  end

  def test_wrap_rejects_wrong_plaintext_length
    pub, _ = keypair(2048)
    assert_raises(ArgumentError) do
      RobocapCenc::SDK::RSAOAEP.wrap_key(
        SecureRandom.bytes(15), pub, plain_len: CEK_BYTES,
        cipher_len: RSA_2048_CIPHERTEXT_BYTES,
      )
    end
  end

  def test_unwrap_rejects_wrong_ciphertext_length
    _, priv = keypair(2048)
    err = assert_raises(RobocapCenc::SDK::Error) do
      RobocapCenc::SDK::RSAOAEP.unwrap_key(
        'short', priv, plain_len: CEK_BYTES, cipher_len: RSA_2048_CIPHERTEXT_BYTES,
      )
    end
    assert_equal RobocapCenc::SDK::ErrorCode::ERR_K2_DECODE, err.code
  end

  def test_unwrap_with_wrong_key_raises
    _, priv = keypair(2048)
    bogus = SecureRandom.bytes(RSA_2048_CIPHERTEXT_BYTES)
    err = assert_raises(RobocapCenc::SDK::Error) do
      RobocapCenc::SDK::RSAOAEP.unwrap_key(
        bogus, priv, plain_len: CEK_BYTES, cipher_len: RSA_2048_CIPHERTEXT_BYTES,
      )
    end
    assert_equal RobocapCenc::SDK::ErrorCode::ERR_K2_DECODE, err.code
  end

  def test_unwrap_cek_uses_cenc_error_codes
    _, priv = keypair(2048)
    bogus = SecureRandom.bytes(RSA_2048_CIPHERTEXT_BYTES)
    err = assert_raises(RobocapCenc::SDK::Error) do
      RobocapCenc::SDK::RSAOAEP.unwrap_cek(bogus, priv)
    end
    assert_equal RobocapCenc::SDK::ErrorCode::ERR_CENC_CEKA_WRAP, err.code
  end

  def test_cross_language_compat_python_wrapped_2048
    # Uses the embedded test keypair from python/tests/helpers_cenc.py.
    # If this passes, RSA-OAEP-SHA256 in Ruby matches Python output.
    public_pem = <<~PEM
      -----BEGIN PUBLIC KEY-----
      MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA0VO2bntFtlrbEmP84IJ4
      qQ6FubUCe1NLVg4WSD5NAYB4EwNDqMzjCiPOUBhCC7axzy7Vpufp310KMmpLldD6
      tbPQqPO9aMtYfMIdYXnOMe84QVBs5DUEO/ExUCTxqjjCh5pwswZK6qoAXKAlQ3jo
      maEFxvEsBidmgfxt35idbzKje3Uhv1t233SEP/xmYys/mJZfM40S9+E6XM6KK84e
      KJXiQf0dbNdQhL9AJfDF+2BZu/JMrQT5OQPDy6X3GNgpDvoHHstDC4gDCy2B8uFZ
      opvO4FCmIUNfWwSVZcdE4JGKa3Y0F1JptHoSz1evYJ4JYaAnaUWP8SzqY2yOfFdT
      3wIDAQAB
      -----END PUBLIC KEY-----
    PEM
    private_pem = <<~PEM
      -----BEGIN PRIVATE KEY-----
      MIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQDRU7Zue0W2WtsS
      Y/zggnipDoW5tQJ7U0tWDhZIPk0BgHgTA0OozOMKI85QGEILtrHPLtWm5+nfXQoy
      akuV0Pq1s9Co871oy1h8wh1hec4x7zhBUGzkNQQ78TFQJPGqOMKHmnCzBkrqqgBc
      oCVDeOiZoQXG8SwGJ2aB/G3fmJ1vMqN7dSG/W3bfdIQ//GZjKz+Yll8zjRL34Tpc
      zoorzh4oleJB/R1s11CEv0Al8MX7YFm78kytBPk5A8PLpfcY2CkO+gcey0MLiAML
      LYHy4Vmim87gUKYhQ19bBJVlx0TgkYprdjQXUmm0ehLPV69gnglhoCdpRY/xLOpj
      bI58V1PfAgMBAAECggEAFVIXTvR7sBcGoOkR7NTNMRGbbu6wCdtSMo8tF376UptW
      X5Vhsv6UvMfTL+xF7zHUtYYPLo4I5P5x10W6siU+y/q8gjY6m225cxJFx35ju/P3
      gQuN3nFEn6MG7fioAWRWR//j17rd2ZNRhchX/fcsNdhP9tNCCSnCh/Mr8RjMfEf3
      EceuRxS3v4M7s0FfB1wWmztaiQ7PotLJRTXtevAKjMDfgp+DxhgGLRwPPMeEKewx
      8gLQMpx8AV+iDz2MPQqAVvojwWp3Ysoygg0ke7mxDg+ym2gQMMvs9MDNIZG6gUNP
      Aw2oTn4CdZ4Zix4YgNkykbv5XzGp+HOzwy7AU4XzqQKBgQDy3DKCq6i9nKrmMo7G
      BY2w1LXZp1vz37dwe3vPKpcQ228b3MwhB8zECj9Ra859gt0YchacrvSNUeNTE14W
      KyR/gRKIY6N4cEfH7T68SXYOtybS4ZUYHTPoiBZ+HlrngkJ9wqutQkqK2KILi9cG
      HaIXoYhmWzd6YGtT7mrbz12vFwKBgQDcpw4ajrWgMIogGFe/v0jrCDHVvkCZ+pw8
      ywBqUbaThNi7sGc+cAEsoKmu/mVCUvqSBBz3QG4devO+ooz+mJkQYyF8W4mh+FNq
      CvFxTQMGQVQD30jbDKcqP8X8i/56xW+HV+o5DOVrmjkM7MdtVxdznb9qKFsp5Ltq
      8h0hpZg+eQKBgQCJ5miz8/77s6MC1UBmxq5+8zlTHonC/4wszaEusDNZOhBsFMLA
      Gqq1wk/TztBQSmd6wwV98IYiXJYlDQFGuzadQ9AfK9ydvbu0lU0jIt9rWaos4jSD
      nclkxylmcZwSis9wk4Jh/htPndTdk4kECv2IR4uo+zCUR32KCf4ZVDUQ/wKBgEeg
      SunADaFUYGIOxN1PoMH6xQKXYa0aNwFc/GOG5vd4FkrG9pzECv2LoclWd1RST1h6
      0VRJq/UR5nGpno8+xeEV7NbLeCAF1j4EE2AuGZ88MaOYJbRFpTYHwaM7Zn4//PY4
      SaX/U7HcPEy/x/TsYoZ7XJl/RCiTQWtz8JTthkAxAoGBAOunl5ArkBEeqPshtNP+
      Ix/7NgxFat/lOTWcw2TaXMIMDcMchIvpEGJMggCuCuTat3ogUKO3pGBXvTzEj5bb
      KoI0GRqzrN4lhSQBy9YDhs262xnseE+uz2tLqQlwqOqhUZFxOpvJ4VIRxAOzXCzl
      Crtz8iuJ9NCC3lz3SVR7z/8H
      -----END PRIVATE KEY-----
    PEM

    pub  = OpenSSL::PKey::RSA.new(public_pem)
    priv = OpenSSL::PKey::RSA.new(private_pem)
    cek  = ("\x01".b * CEK_BYTES)
    wrapped = RobocapCenc::SDK::RSAOAEP.wrap_cek(cek, pub)
    assert_equal cek, RobocapCenc::SDK::RSAOAEP.unwrap_cek(wrapped, priv)
  end
end
