# Contributing to Py2Exe

Thank you for considering a contribution!

## Development Setup

```bash
# 1. Clone the repo
git clone https://github.com/varun-sv/py2exe.git
cd py2exe

# 2. Create a virtual environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3. Install in editable mode with dev extras
pip install -e ".[dev]"

# 4. Install pre-commit hooks
pre-commit install
```

## Running Tests

```bash
pytest tests/ -v
```

For coverage:

```bash
pytest tests/ --cov=Python_to_exe_maker --cov-report=term-missing
```

## Running Linters Manually

```bash
black .
isort .
flake8 .
mypy Python_to_exe_maker/
```

## Running the Streamlit App Locally

```bash
export GITHUB_TOKEN=ghp_...
export GITHUB_REPO=varun-sv/py2exe
streamlit run streamlit_app.py
```

## Pull Request Checklist

- [ ] Tests pass (`pytest`)
- [ ] Type check passes (`mypy Python_to_exe_maker/`)
- [ ] Code formatted (`black .` + `isort .`)
- [ ] No new flake8 violations
- [ ] PR description explains the change

## Code Style

- Line length: 100 characters (enforced by black)
- Import order: black-compatible isort profile
- Type hints: required on all public functions
- Comments: only when the *why* is non-obvious
