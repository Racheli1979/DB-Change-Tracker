from unittest.mock import MagicMock, patch

from backend.db import check_connection


@patch("backend.db.oracledb.connect")
def test_connection_success(mock_connect):
    mock_connection = MagicMock()
    mock_cursor = MagicMock()

    mock_connect.return_value.__enter__.return_value = mock_connection
    mock_connection.cursor.return_value.__enter__.return_value = mock_cursor

    mock_cursor.fetchone.return_value = ("APP_USER",)
    mock_connection.version = "Oracle Database 23c"

    result = check_connection(
        host="localhost",
        port=1521,
        service="FREEPDB1",
        user="APP_USER",
        password="test-password",
    )

    assert result["success"] is True
    assert result["session_user"] == "APP_USER"
    assert result["db_version"] == "Oracle Database 23c"

    mock_connect.assert_called_once()


@patch("backend.db.oracledb.connect")
def test_connection_failure(mock_connect):
    import oracledb

    mock_connect.side_effect = oracledb.Error(
        "Simulated connection error"
    )

    result = check_connection(
        host="localhost",
        port=1521,
        service="FREEPDB1",
        user="APP_USER",
        password="wrong-password",
    )

    assert result["success"] is False
    assert result["error_type"] == "connection_error"

    mock_connect.assert_called_once()