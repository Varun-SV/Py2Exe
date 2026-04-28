# Py2Exe

Convert any Python script into a standalone executable — **Linux binary** or **Windows .exe** — with a single command or via a hosted web app.

## Features

- **CLI**: run `p2e` on your machine, get a binary for your current OS
- **Web app**: upload a ZIP of your project on Streamlit, receive both a Linux binary and a Windows `.exe` (built via GitHub Actions)
- **Code quality check**: flake8 runs on your code before building; fix issues or skip
- **Cross-platform**: Linux, Windows, and macOS support via PyInstaller

---

## Web App (Streamlit)

The easiest way to use Py2Exe — no local setup needed.

1. Visit the hosted app (deploy it yourself — see [Deployment](#deployment))
2. Upload your Python project as a `.zip` file
3. Type the name of your main Python file (e.g. `main.py`)
4. Click **Check & Build**
5. Download the Linux binary and/or Windows `.exe`

The app checks your code with flake8 first. If issues are found you can fix them or build anyway.
Temporary build branches are automatically deleted after each build.

---

## CLI

### Installation

```bash
# From source
git clone https://github.com/varun-sv/py2exe.git
cd py2exe
pip install -e .
```

### Usage

```bash
p2e
# Python script (with location): /path/to/your/script.py
```

The binary is placed in the same directory as your script.

**Platform output:**
| OS      | Output         |
|---------|----------------|
| Linux   | `script` (no extension) |
| macOS   | `script` (no extension) |
| Windows | `script.exe`   |

---

## Deployment

### Streamlit Community Cloud (free)

1. Fork this repository
2. Go to [share.streamlit.io](https://share.streamlit.io) → **New app** → select your fork → set main file to `streamlit_app.py`
3. Under **Advanced settings → Secrets**, add:

```toml
GITHUB_TOKEN = "ghp_..."   # Personal Access Token: repo + actions scopes
GITHUB_REPO  = "your-username/py2exe"
```

> Streamlit Cloud uses `requirements.txt` in the repo root to install Python
> dependencies (streamlit + requests). No extra configuration needed.

4. Click **Deploy** — your app is live instantly

> **Note**: GitHub artifact downloads require the user to be logged in to GitHub. Artifacts expire after 1 day.

---

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md) for full dev setup instructions.

```bash
pip install -e ".[dev]"
pre-commit install
pytest tests/ -v
```

---

## Security

See [SECURITY.md](SECURITY.md) for the vulnerability disclosure policy and a summary of security fixes in 1.0.0 (command injection, bare except, input validation).

---

## License

MIT — see [LICENSE](LICENSE).
