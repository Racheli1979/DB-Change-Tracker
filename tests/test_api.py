import pytest

from fastapi.testclient import TestClient
from unittest.mock import patch

from backend.main import app, SESSIONS


client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_sessions_and_cookies():
    SESSIONS.clear()
    client.cookies.clear()
    yield
    SESSIONS.clear()
    client.cookies.clear()


@pytest.fixture
def mock_oracle_connection():
    with patch(
        "backend.main.check_connection"
    ) as mock:

        mock.return_value = {
            "success": True,
            "db_version": "19.0.0.0.0",
            "session_user": "TEST_USER",
        }

        yield mock


@pytest.fixture
def temporary_saved_config(tmp_path, monkeypatch):
    from backend import crypto
    from cryptography.fernet import Fernet

    monkeypatch.setattr(
        crypto,
        "KEY_FILE",
        tmp_path / "secret.key",
    )

    monkeypatch.setattr(
        crypto,
        "CONFIG_FILE",
        tmp_path / "config.enc",
    )

    (tmp_path / "secret.key").write_bytes(Fernet.generate_key())


@pytest.fixture
def connection_data():
    return {
        "host": "localhost",
        "port": 1521,
        "service": "ORCL",
        "user": "test_user",
        "password": "MySecret123",
        "save": True,
    }


def test_saved_connection_does_not_expose_password(
    temporary_saved_config,
    connection_data,
):
    from backend.crypto import save_config

    save_config(connection_data)

    response = client.post(
        "/api/connect",
        json={"action": "get_saved"},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["exists"] is True
    assert "password" not in data
    assert "encrypted_password" not in data
    assert data["password_saved"] is True


def test_connect_with_save_true_saves_config(
    temporary_saved_config,
    mock_oracle_connection,
    connection_data,
):
    response = client.post(
        "/api/connect",
        json=connection_data,
    )

    assert response.status_code == 200
    assert response.json()["success"] is True

    from backend.crypto import load_config

    saved = load_config()

    assert saved is not None
    assert saved["host"] == connection_data["host"]
    assert saved["user"] == connection_data["user"]
    assert saved["password"] == connection_data["password"]


def test_connect_with_save_false_does_not_save_config(
    temporary_saved_config,
    mock_oracle_connection,
    connection_data,
):
    connection_data["save"] = False

    response = client.post(
        "/api/connect",
        json=connection_data,
    )

    assert response.status_code == 200
    assert response.json()["success"] is True

    from backend.crypto import load_config

    assert load_config() is None


def test_connect_saved_uses_decrypted_password(
    temporary_saved_config,
    mock_oracle_connection,
    connection_data,
):
    from backend.crypto import save_config

    save_config(connection_data)

    response = client.post(
        "/api/connect",
        json={"action": "connect_saved"},
    )

    assert response.status_code == 200
    assert response.json()["success"] is True

    mock_oracle_connection.assert_called_once()

    call_kwargs = mock_oracle_connection.call_args.kwargs

    assert call_kwargs["password"] == connection_data["password"]


def test_password_whitespace_is_preserved(
    temporary_saved_config,
    mock_oracle_connection,
):
    data = {
        "host": "localhost",
        "port": 1521,
        "service": "ORCL",
        "user": "test_user",
        "password": "  MySecret123  ",
        "save": True,
    }

    response = client.post(
        "/api/connect",
        json=data,
    )

    assert response.status_code == 200

    mock_oracle_connection.assert_called_once()

    call_kwargs = mock_oracle_connection.call_args.kwargs

    assert call_kwargs["password"] == "  MySecret123  "

    from backend.crypto import load_config

    saved = load_config()

    assert saved["password"] == "  MySecret123  "


def test_invalid_port_returns_422(
    mock_oracle_connection,
    connection_data,
):
    connection_data["port"] = 70000

    response = client.post(
        "/api/connect",
        json=connection_data,
    )

    assert response.status_code == 422
    assert connection_data["password"] not in response.text


def test_missing_required_fields_returns_422(
    mock_oracle_connection,
):
    data = {
        "host": "localhost",
        "port": 1521,
        "service": "ORCL",
        "user": "test_user",
        "save": True,
    }

    response = client.post(
        "/api/connect",
        json=data,
    )

    assert response.status_code == 422

    assert "MySecret123" not in response.text


def test_delete_saved_connection_successfully(
    temporary_saved_config,
    connection_data,
):
    from backend.crypto import save_config, load_config

    save_config(connection_data)

    response = client.post(
        "/api/connect",
        json={"action": "delete_saved"},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["success"] is True
    assert data["message"] == "החיבור השמור נמחק בהצלחה."
    assert load_config() is None


def test_delete_saved_connection_when_none_exists(
    temporary_saved_config,
):
    from backend.crypto import load_config

    response = client.post(
        "/api/connect",
        json={"action": "delete_saved"},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["success"] is True
    assert data["message"] == "החיבור השמור נמחק בהצלחה."
    assert load_config() is None


def test_changes_redirects_without_authenticated_session():
    response = client.get(
        "/changes?db_version=FAKE&session_user=FAKE",
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/login.html"


def test_successful_connection_opens_changes_screen(
    temporary_saved_config,
    mock_oracle_connection,
    connection_data,
):
    response = client.post("/api/connect", json=connection_data)

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "db_version": "19.0.0.0.0",
        "session_user": "TEST_USER",
    }
    assert "httponly" in response.headers.get("set-cookie", "").lower()

    changes_response = client.get("/changes")
    assert changes_response.status_code == 200
    assert "היסטוריית שינויים" in changes_response.text

    session_response = client.post(
        "/api/connect",
        json={"action": "get_session"},
    )
    assert session_response.status_code == 200
    assert session_response.json() == {
        "db_version": "19.0.0.0.0",
        "session_user": "TEST_USER",
    }