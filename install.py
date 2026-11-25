import os
import platform
import subprocess
import sys
from pathlib import Path


APP_NAME = "DBChangeTracker"
BASE_DIR = Path(__file__).resolve().parent
REQUIREMENTS_FILE = BASE_DIR / "requirements.txt"


def print_rtl(message: str = "", **kwargs) -> None:
    from bidi.algorithm import get_display

    print(get_display(str(message)), **kwargs)


def input_rtl(message: str) -> str:
    from bidi.algorithm import get_display

    print(get_display(message), end="", flush=True)
    return input()


def get_data_dir() -> Path:
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

    return base_dir / APP_NAME


DATA_DIR = get_data_dir()
KEY_FILE = DATA_DIR / "secret.key"
CONFIG_FILE = DATA_DIR / "config.enc"


def check_python_version() -> None:
    print_rtl("בודק Python...", end=" ", flush=True)

    if sys.version_info < (3, 8):
        print_rtl("נכשל")
        print_rtl("נדרשת גרסת Python 3.8 ומעלה.")
        sys.exit(1)

    version = platform.python_version()
    print(f"OK ({version})")


def choose_installation_action() -> str:
    if not KEY_FILE.exists() and not CONFIG_FILE.exists():
        return "new"

    print()
    print_rtl("נמצאה התקנה קיימת.")

    while True:
        print_rtl("בחרי פעולה:")
        print_rtl("1. עדכון – שמירת החיבור והמפתח הקיימים")
        print_rtl("2. דריסה – מחיקת החיבור והמפתח ויצירת מפתח חדש")
        print_rtl("3. ביטול")

        choice = input_rtl("בחירה (1/2/3): ").strip()

        if choice == "1":
            return "update"

        if choice == "2":
            confirmation = input_rtl(
                "הדריסה תמחק את החיבור השמור. להמשיך? (כן/לא): "
            ).strip().lower()

            if confirmation in ("כן", "y", "yes"):
                return "overwrite"

            print_rtl("הדריסה בוטלה.")

        elif choice == "3":
            return "cancel"

        else:
            print_rtl("בחירה לא תקינה. נסי שוב.")


def install_dependencies() -> None:
    print_rtl("מתקין תלויות...", end=" ", flush=True)

    if not REQUIREMENTS_FILE.exists():
        print_rtl("נכשל")
        raise FileNotFoundError(
            f"לא נמצא קובץ requirements.txt: {REQUIREMENTS_FILE}"
        )

    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "-r",
            str(REQUIREMENTS_FILE),
        ],
        check=True,
    )

    # Linux needs an explicit pywebview GUI backend.
    if sys.platform.startswith("linux"):
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "pywebview[qt]==5.3.2",
            ],
            check=True,
        )

    print("OK")


def create_data_directory() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def create_secret_key(action: str) -> None:
    from cryptography.fernet import Fernet

    print_rtl("יוצר secret.key...", end=" ", flush=True)

    if action == "overwrite":
        if CONFIG_FILE.exists():
            CONFIG_FILE.unlink()

        if KEY_FILE.exists():
            KEY_FILE.unlink()

    if KEY_FILE.exists():
        key = KEY_FILE.read_bytes()

        try:
            Fernet(key)
        except (ValueError, TypeError) as exc:
            raise RuntimeError(
                "מפתח ההצפנה הקיים אינו תקין."
            ) from exc

        print_rtl("OK (המפתח הקיים נשמר)")
        return

    if CONFIG_FILE.exists():
        raise RuntimeError(
            "קיים config.enc אך secret.key חסר. "
            "לא ניתן ליצור מפתח חדש עבור חיבור מוצפן קיים."
        )

    key = Fernet.generate_key()

    with KEY_FILE.open("xb") as file:
        file.write(key)

    try:
        KEY_FILE.chmod(0o600)
    except OSError:
        pass

    print("OK")


def read_version_for_installer() -> str:
    version_file = BASE_DIR / "version.txt"

    try:
        return version_file.read_text(encoding="utf-8").strip() or "0.1.0"
    except OSError:
        return "0.1.0"


def main() -> None:
    try:
        print_rtl("=== DB Change Tracker — התקנה ===")

        check_python_version()

        action = choose_installation_action()

        if action == "cancel":
            print_rtl("ההתקנה בוטלה.")
            return

        install_dependencies()

        print_rtl("יוצר תיקיית נתונים מקומית...", end=" ", flush=True)
        create_data_directory()
        print("OK")

        create_secret_key(action)

        print()
        print_rtl("=== התקנה הסתיימה! ===")
        print_rtl("הרץ: DBTracker.exe")

    except subprocess.CalledProcessError:
        print()
        print_rtl("ההתקנה נכשלה בעת התקנת התלויות.")
        sys.exit(1)

    except (OSError, RuntimeError, ImportError) as exc:
        print()
        print_rtl(f"ההתקנה נכשלה: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
