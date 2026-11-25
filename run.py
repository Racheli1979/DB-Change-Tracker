import socket
import sys
import threading
import time
from pathlib import Path

import uvicorn
import webview

from backend.main import APP_VERSION, app

HOST = "127.0.0.1"
RESOURCE_DIR = Path(
    getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)
)
LOGIN_FILE = RESOURCE_DIR / "frontend" / "login.html"


def find_available_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((HOST, 0))
        return sock.getsockname()[1]


def start_server(port: int) -> None:
    config = uvicorn.Config(
        app,
        host=HOST,
        port=port,
        log_level="error",
        access_log=False,
    )
    server = uvicorn.Server(config)
    server.run()


def wait_for_server(port: int, timeout: float = 15.0) -> bool:
    deadline = time.time() + timeout

    while time.time() < deadline:
        try:
            with socket.create_connection((HOST, port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.2)

    return False


def main() -> None:
    if not LOGIN_FILE.is_file():
        raise FileNotFoundError(
            "Login screen was not found. Check the application files and PyInstaller build."
        )

    port = find_available_port()
    server_thread = threading.Thread(
        target=start_server,
        args=(port,),
        daemon=True,
    )
    server_thread.start()

    if not wait_for_server(port):
        raise RuntimeError("השרת המקומי לא עלה בזמן.")

    webview.create_window(
        f"DB Change Tracker v{APP_VERSION}",
        f"http://{HOST}:{port}/login.html",
        width=1000,
        height=750,
        min_size=(700, 550),
    )

    webview.start()


if __name__ == "__main__":
    main()