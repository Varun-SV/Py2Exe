# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 1.x     | Yes       |

## Reporting a Vulnerability

Please **do not** open a public GitHub issue for security vulnerabilities.

Report vulnerabilities via [GitHub private security advisories](https://github.com/varun-sv/py2exe/security/advisories/new).
You can expect an initial response within **72 hours**.

## Security Notes

### Fixed in 1.0.0

- **Command injection** — the original `p2e.py` used `os.system()` to build shell
  strings from unsanitized user input. All shell invocations now use
  `subprocess.run(..., check=True)` with argument lists, eliminating shell
  injection entirely.

- **Bare `except` clause** — the original code silently swallowed all exceptions
  (including `KeyboardInterrupt` and `SystemExit`). All exception handling is now
  explicit with typed clauses.

- **Unvalidated input** — file paths supplied by the user are now resolved with
  `Path.resolve()` and validated before use.

### Streamlit App

The Streamlit app uses a GitHub Personal Access Token stored as a Streamlit
secret. The token requires **only** `repo` and `actions` scopes. Temporary build
branches are created and deleted automatically after each build; no user code is
persisted in the repository.
