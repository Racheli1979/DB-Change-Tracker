import pytest

from backend import crypto


@pytest.fixture
def crypto_files(tmp_path, monkeypatch):
    monkeypatch.setattr(crypto, "KEY_FILE", tmp_path / "secret.key")
    monkeypatch.setattr(crypto, "CONFIG_FILE", tmp_path / "config.enc")

    return tmp_path


@pytest.fixture
def sample_config():
    return {
        "host": "localhost",
        "port": 1521,
        "service": "ORCL",
        "user": "test_user",
        "password": "  MySecret123  ",
    }


def _create_key(tmp_path):
    from cryptography.fernet import Fernet
    key = Fernet.generate_key()
    (tmp_path / "secret.key").write_bytes(key)
    return key


def test_create_encryption_key(crypto_files):
    key = _create_key(crypto_files)

    assert isinstance(key, bytes)
    assert (crypto_files / "secret.key").exists()


def test_existing_key_is_reused(crypto_files):
    first_key = _create_key(crypto_files)
    second_key = crypto.get_key()

    assert first_key == second_key


def test_encrypt_and_decrypt(crypto_files):
    _create_key(crypto_files)
    original = "MySecret123"

    encrypted = crypto.encrypt_data(original)
    decrypted = crypto.decrypt_data(encrypted)

    assert encrypted != original.encode("utf-8")
    assert decrypted == original


def test_save_and_load_config(crypto_files, sample_config):
    _create_key(crypto_files)
    crypto.save_config(sample_config)

    loaded = crypto.load_config()

    assert loaded == sample_config
    assert (crypto_files / "config.enc").exists()


def test_password_is_not_saved_as_plain_text(
    crypto_files, sample_config
):
    _create_key(crypto_files)
    crypto.save_config(sample_config)

    encrypted_file = (crypto_files / "config.enc").read_bytes()

    assert sample_config["password"].encode("utf-8") not in encrypted_file


def test_password_whitespace_is_preserved(crypto_files, sample_config):
    _create_key(crypto_files)
    crypto.save_config(sample_config)

    loaded = crypto.load_config()

    assert loaded["password"] == "  MySecret123  "


def test_load_config_when_file_does_not_exist(crypto_files):
    assert crypto.load_config() is None


def test_decryption_fails_without_key(crypto_files):
    with pytest.raises(crypto.CryptoError):
        crypto.decrypt_data(b"invalid-data")


def test_decryption_fails_with_wrong_data(crypto_files):
    _create_key(crypto_files)

    with pytest.raises(crypto.CryptoError):
        crypto.decrypt_data(b"invalid-data")


def test_invalid_key_is_not_replaced(crypto_files):
    key_file = crypto_files / "secret.key"
    key_file.write_bytes(b"invalid-key")

    with pytest.raises(crypto.CryptoError):
        crypto.get_key()

    assert key_file.read_bytes() == b"invalid-key"


def test_delete_config(crypto_files, sample_config):
    _create_key(crypto_files)
    crypto.save_config(sample_config)

    crypto.delete_config()

    assert not (crypto_files / "config.enc").exists()
    assert (crypto_files / "secret.key").exists()


def test_invalid_port_is_rejected(crypto_files, sample_config):
    _create_key(crypto_files)
    sample_config["port"] = 70000

    with pytest.raises(crypto.CryptoError):
        crypto.save_config(sample_config)


def test_missing_password_is_rejected(crypto_files, sample_config):
    _create_key(crypto_files)
    sample_config["password"] = ""

    with pytest.raises(crypto.CryptoError):
        crypto.save_config(sample_config)