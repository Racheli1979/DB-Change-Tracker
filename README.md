# 🗄️ DB Change Tracker

Desktop application for connecting to an Oracle database schema, testing connections, and securely storing connection details locally.

## 📌 Version

`0.1.0`

## ⚙️ Prerequisites

- Python 3.8 or newer
- Access to an Oracle database

## 🚀 User Installation and Usage

1. **Clone the repository:**

   ```bash
   git clone https://github.com/rivilev/DB-Change-Tracker
   cd DB-Change-Tracker
   ```

2. **Install the application:**

   ```bash
   python install.py
   ```

   The installer checks the Python version, installs the required dependencies, creates the local data directory, and generates the encryption key.

3. **Launch the application:**

   Open the `dist` folder and double-click `DBTracker_v0.1.0.exe` to launch the application.

4. **Connect to Oracle:**

   Enter the Oracle connection details and click **Connect**.

5. **Save your connection (optional):**

   Select **Remember Connection** to securely save your connection details for future use.

6. **Reuse or delete a saved connection:**

   On subsequent launches, select the saved connection to reconnect without entering the password again. You can also delete the saved connection and enter new connection details.

## 💻 Developer Setup

1. **Clone the repository:**

   ```bash
   git clone <repository-url>
   cd DB-Change-Tracker
   ```

2. **Install the dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application in development mode:**

   ```bash
   python run.py
   ```

4. **Build the executable (Windows):**

   The following command is intended for Windows:

   ```bash
   python -m PyInstaller --onefile --windowed --clean --name DBTracker_v0.1.0 --icon "frontend\icon.ico" --collect-all cryptography --add-data "frontend;frontend" --add-data "version.txt;." run.py
   ```

   The executable is generated in the `dist` directory.

## ✨ Features

- Oracle database connection testing.
- Secure local storage of connection details using Fernet encryption.
- Reuse and delete saved connections.
- Desktop interface powered by pywebview and FastAPI.
- Automatic navigation to the Changes screen after a successful connection.

## 📁 Local Data Storage

Application data is stored locally on the user's computer.

**Windows:**

```text
%LOCALAPPDATA%\DBChangeTracker\
```

**Linux / macOS (default):**

```text
~/.local/share/DBChangeTracker/
```

If `XDG_DATA_HOME` is configured, the application uses that location instead.

The directory contains:

- `secret.key` – encryption key.
- `config.enc` – encrypted Oracle connection details.

These files are stored locally and must not be committed to Git.

## 🔒 Security

- Connection details, including the password, are encrypted using Fernet.
- The password is not stored as plain text.
- The encryption key and encrypted connection details are stored locally.
- Never commit `config.enc`, `secret.key`, `.env`, or any file containing passwords or credentials to Git.
- These sensitive files are excluded from version control using `.gitignore`.

## 🐛 Issues and Feature Requests

For bug reports or feature requests, open an issue on the repository's [Issues](../../issues) page.