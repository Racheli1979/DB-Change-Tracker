import json
import os
from pathlib import Path
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken


def _get_data_dir() -> Path:
    if os.name == "nt":
        base_dir = Path(
            os.environ.get(
                "LOCALAPPDATA",
                str(Path.home() / "AppData" / "Local"),
            )
        )
    else:
        base_dir = Path(
            os.environ.get(
                "XDG_DATA_HOME",
                str(Path.home() / ".local" / "share"),
            )
        )

    return base_dir / "DBChangeTracker"


DATA_DIR = _get_data_dir()
KEY_FILE = DATA_DIR / "secret.key"
CONFIG_FILE = DATA_DIR / "config.enc"


class CryptoError(Exception):
    """Raised when encrypted connection data cannot be processed."""


def get_key() -> bytes:
    try:
        if not KEY_FILE.exists():
            raise CryptoError("The encryption key was not found.")

        key = KEY_FILE.read_bytes()

        try:
            Fernet(key)
        except (ValueError, TypeError) as exc:
            raise CryptoError("The encryption key is invalid.") from exc

        return key

    except CryptoError:
        raise

    except OSError as exc:
        raise CryptoError("Could not read the encryption key.") from exc


def encrypt_data(data: str) -> bytes:
    if not isinstance(data, str):
        raise TypeError("Data to encrypt must be a string.")

    try:
        cipher = Fernet(get_key())
        return cipher.encrypt(data.encode("utf-8"))

    except CryptoError:
        raise

    except (OSError, ValueError, TypeError) as exc:
        raise CryptoError("Could not encrypt the data.") from exc


def decrypt_data(encrypted_data: bytes) -> str:
    try:
        cipher = Fernet(get_key())
        decrypted = cipher.decrypt(encrypted_data)

        return decrypted.decode("utf-8")

    except CryptoError:
        raise

    except (
        InvalidToken,
        ValueError,
        TypeError,
        UnicodeDecodeError,
        OSError,
    ) as exc:
        raise CryptoError(
            "Could not decrypt the saved connection."
        ) from exc


def _validate_config(config: dict) -> dict:
    if not isinstance(config, dict):
        raise ValueError("Connection configuration must be a dictionary.")

    required_fields = ("host", "service", "user", "password")

    for field in required_fields:
        value = config.get(field)

        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Invalid connection field: {field}.")

    port = config.get("port", 1521)

    if (
        isinstance(port, bool)
        or not isinstance(port, int)
        or not 1 <= port <= 65535
    ):
        raise ValueError(
            "Port must be an integer between 1 and 65535."
        )

    return {
        "host": config["host"].strip(),
        "port": port,
        "service": config["service"].strip(),
        "user": config["user"].strip(),
        "password": config["password"],
    }


def save_config(config: dict) -> None:
    try:
        safe_config = _validate_config(config)

        config_json = json.dumps(
            safe_config,
            ensure_ascii=False,
        )

        encrypted_config = encrypt_data(config_json)

        DATA_DIR.mkdir(parents=True, exist_ok=True)
        try:
            DATA_DIR.chmod(0o700)
        except OSError:
            pass

        temp_file = CONFIG_FILE.with_suffix(".tmp")

        try:
            temp_file.write_bytes(encrypted_config)
            try:
                temp_file.chmod(0o600)
            except OSError:
                pass
            temp_file.replace(CONFIG_FILE)

        finally:
            if temp_file.exists():
                temp_file.unlink()

    except (OSError, TypeError, ValueError, CryptoError) as exc:
        raise CryptoError(
            "Could not save the encrypted connection."
        ) from exc


def load_config() -> Optional[dict]:
    if not CONFIG_FILE.exists():
        return None

    try:
        encrypted_data = CONFIG_FILE.read_bytes()
        config_json = decrypt_data(encrypted_data)
        config = json.loads(config_json)

        return _validate_config(config)

    except CryptoError:
        raise

    except (
        OSError,
        json.JSONDecodeError,
        TypeError,
        ValueError,
    ) as exc:
        raise CryptoError(
            "The saved connection file is invalid."
        ) from exc


def delete_config() -> None:
    try:
        if CONFIG_FILE.exists():
            CONFIG_FILE.unlink()

    except OSError as exc:
        raise CryptoError(
            "Could not delete the saved connection."
        ) from exc