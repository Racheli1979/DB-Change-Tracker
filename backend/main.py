import secrets
import sys
import time
from pathlib import Path
from typing import Literal, Optional

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from backend.db import check_connection
from backend.crypto import (
    CryptoError,
    get_key,
    load_config,
    save_config,
    delete_config,
)

RESOURCE_DIR = Path(
    getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent)
)
VERSION_FILE = RESOURCE_DIR / "version.txt"
FRONTEND_DIR = RESOURCE_DIR / "frontend"

SESSION_COOKIE_NAME = "dbct_session"
SESSION_MAX_AGE = 8 * 60 * 60
SESSIONS = {}


def read_version() -> str:
    try:
        return VERSION_FILE.read_text(encoding="utf-8").strip() or "unknown"
    except OSError:
        return "unknown"


APP_VERSION = read_version()

app = FastAPI(
    title="DB Change Tracker",
    version=APP_VERSION,
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
):
    return JSONResponse(
        status_code=422,
        content={"detail": "נתוני הבקשה אינם תקינים. בדקי את השדות ונסי שוב."},
    )


class ConnectionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Literal[
        "connect",
        "get_saved",
        "connect_saved",
        "delete_saved",
        "get_version",
        "get_session",
    ] = "connect"

    host: Optional[str] = None
    port: int = Field(default=1521, ge=1, le=65535)
    service: Optional[str] = None
    user: Optional[str] = None
    password: Optional[str] = Field(default=None, repr=False)
    save: bool = True


def require_connection_fields(data: ConnectionRequest) -> dict:
    fields = {
        "host": data.host,
        "service": data.service,
        "user": data.user,
        "password": data.password,
    }

    for field, value in fields.items():
        if not isinstance(value, str) or not value.strip():
            raise HTTPException(
                status_code=422,
                detail=f"השדה {field} הוא שדה חובה.",
            )

    return {
        "host": data.host.strip(),
        "port": data.port,
        "service": data.service.strip(),
        "user": data.user.strip(),
        "password": data.password,
    }


def connect_using_config(config: dict) -> dict:
    try:
        result = check_connection(
            host=config["host"],
            port=config["port"],
            service=config["service"],
            user=config["user"],
            password=config["password"],
        )
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="אירעה שגיאה לא צפויה בעת בדיקת החיבור.",
        )

    if not result.get("success"):
        error_messages = {
            "authentication": "שם המשתמש או הסיסמה שגויים.",
            "service_not_found": "שם שירות Oracle לא נמצא.",
            "service_unavailable": "שירות Oracle אינו זמין כרגע.",
            "database_unavailable": "לא ניתן להגיע לשרת Oracle.",
            "connection_error": "שגיאה בחיבור למסד הנתונים.",
        }
        error_type = result.get("error_type", "connection_error")
        raise HTTPException(
            status_code=400,
            detail=error_messages.get(
                error_type,
                "החיבור למסד הנתונים נכשל.",
            ),
        )

    return {
        "success": True,
        "db_version": str(result["db_version"]),
        "session_user": str(result["session_user"]),
    }


def create_session(response: Response, connection_result: dict) -> None:
    session_id = secrets.token_urlsafe(32)
    SESSIONS[session_id] = {
        "db_version": connection_result["db_version"],
        "session_user": connection_result["session_user"],
        "created_at": time.time(),
    }
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_id,
        httponly=True,
        secure=False,  
        samesite="strict",
        max_age=SESSION_MAX_AGE,
        path="/",
    )


def get_active_session(request: Request) -> Optional[dict]:
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    if not session_id:
        return None
    session = SESSIONS.get(session_id)
    if session is None:
        return None

    if time.time() - session["created_at"] > SESSION_MAX_AGE:
        SESSIONS.pop(session_id, None)
        return None

    return {
        "db_version": session["db_version"],
        "session_user": session["session_user"],
    }


@app.post("/api/connect")
def connect(
    data: ConnectionRequest,
    request: Request,
    response: Response,
):
    if data.action == "get_version":
        return {"version": APP_VERSION}

    if data.action == "get_session":
        session = get_active_session(request)
        if session is None:
            raise HTTPException(
                status_code=401,
                detail="נדרשת התחברות מחדש.",
            )
        return session

    if data.action == "connect":
        config = require_connection_fields(data)

        try:
            get_key()
        except CryptoError:
            raise HTTPException(
                status_code=500,
                detail="מפתח ההצפנה לא נמצא. יש להריץ את install.py תחילה.",
            )

        result = connect_using_config(config)

        if data.save:
            try:
                save_config(config)
            except CryptoError:
                raise HTTPException(
                    status_code=500,
                    detail="החיבור הצליח, אך שמירת פרטי החיבור נכשלה.",
                )

        create_session(response, result)
        return result

    if data.action == "get_saved":
        try:
            config = load_config()
        except CryptoError:
            raise HTTPException(
                status_code=500,
                detail="לא ניתן לקרוא את פרטי החיבור השמורים.",
            )

        if config is None:
            return {"exists": False}

        return {
            "exists": True,
            "host": config["host"],
            "port": config["port"],
            "service": config["service"],
            "user": config["user"],
            "password_saved": True,
        }

    if data.action == "connect_saved":
        try:
            config = load_config()
        except CryptoError:
            raise HTTPException(
                status_code=500,
                detail="לא ניתן לפענח את פרטי החיבור השמורים.",
            )

        if config is None:
            raise HTTPException(
                status_code=404,
                detail="לא נמצא חיבור שמור.",
            )

        result = connect_using_config(config)
        create_session(response, result)
        return result

    if data.action == "delete_saved":
        try:
            delete_config()
        except CryptoError:
            raise HTTPException(
                status_code=500,
                detail="לא ניתן למחוק את פרטי החיבור השמורים.",
            )

        return {
            "success": True,
            "message": "החיבור השמור נמחק בהצלחה.",
        }

    raise HTTPException(status_code=400, detail="פעולה לא מוכרת.")


@app.get("/changes", include_in_schema=False)
def changes(request: Request):
    """Only an authenticated Oracle session may open the changes screen."""
    if get_active_session(request) is None:
        return RedirectResponse(url="/login.html", status_code=303)

    changes_file = FRONTEND_DIR / "changes.html"
    if not changes_file.is_file():
        raise HTTPException(status_code=404, detail="מסך השינויים לא נמצא.")
    return FileResponse(changes_file)


if FRONTEND_DIR.exists():
    app.mount(
        "/",
        StaticFiles(directory=str(FRONTEND_DIR), html=True),
        name="frontend",
    )