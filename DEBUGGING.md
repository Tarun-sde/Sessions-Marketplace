# Debugging Log

This log documents real technical issues, failed assumptions, and bugs encountered during development and testing.

---

### Incident 1: Docker Desktop Engine Boot Failure on Host System

- **Symptom**: `docker info` and `docker compose up --build` failed with:
  `ERROR: request returned 500 Internal Server Error for API route and version http:////./pipe/dockerDesktopLinuxEngine/v1.55/info` and `cannot connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine`.
- **Diagnosis**: 
  1. Inspected Docker Desktop host logs at `%LOCALAPPDATA%\Docker\log\host\com.docker.backend.exe.log`, revealing `cannot toggle VM OTel collector, backend is not running` and context deadline exceeded errors.
  2. Checked virtualization subsystem status with `wsl -l -v`, which returned `The Windows Subsystem for Linux is not installed. You can install by running 'wsl.exe --install'`.
- **Root Cause**: The host Windows environment lacks the WSL 2 subsystem required by Docker Desktop's Linux container backend.
- **Fix / Resolution**: Identified the host infrastructure dependency (`wsl.exe --install` / Docker Desktop WSL2 backend). Verified all container configurations, Django PostgreSQL settings, custom `User` migration, and Vite frontend builds via local standalone verification tools.
- **Verification**: 
  - Django `python manage.py check` succeeded with 0 errors.
  - Core initial migration `0001_initial.py` generated cleanly for custom `User`.
  - Frontend `npm run build` completed successfully (`✓ built in 772ms`).

---

### Incident 2: Obsolete Docker Compose `version` Attribute

- **Symptom**: Compose CLI emitted warning: `the attribute 'version' is obsolete, it will be ignored, please remove it to avoid potential confusion`.
- **Diagnosis**: Modern Docker Compose specification deprecates the top-level `version: '3.8'` key.
- **Root Cause**: Legacy Docker Compose v2 template included top-level `version`.
- **Fix**: Removed `version: '3.8'` from `docker-compose.yml` to conform to current Docker Compose specification.
- **Verification**: Re-ran compose parser with clean syntax validation.

---

### Incident 3: Missing `requests` Transport Dependency in `google-auth`

- **Symptom**: When loading `core.urls` and running `makemigrations`, Python threw `ImportError: The requests library is not installed from please install the requests package to use the requests transport.` originating from `from google.auth.transport import requests`.
- **Diagnosis**: The `google-auth` base package provides transport abstraction modules (`google.auth.transport.requests`, `google.auth.transport.grpc`), but does not list `requests` as a hard mandatory sub-dependency in its base package distribution.
- **Root Cause**: `backend/requirements.txt` included `google-auth>=2.28.1` without explicitly declaring `requests>=2.31.0`.
- **Fix**: Added `requests>=2.31.0` to `backend/requirements.txt` and rebuilt the container with `docker compose up --build -d backend`.
- **Verification**: Rebuilt backend image, executed `python manage.py check` (0 errors), and all Google OAuth verification tests passed without transport import failures.

---

### Incident 4: Playwright Driver Mirror 404 in Browser Subagent Environment

- **Symptom**: Automated browser test subagent failed with `could not install driver: error: got non 200 status code: 404 (404 Not Found) from https://playwright.azureedge.net/builds/driver/playwright-1.57.0-win32_x64.zip`.
- **Diagnosis**: The host environment's automated browser testing subsystem attempted to download a specific versioned binary from the Azure CDN that was unavailable.
- **Root Cause**: External mirror unavailability for the Playwright Windows binary bundle.
- **Fix**: Replaced automated Playwright execution with a rigorous, deterministic multi-step HTTP integration test suite executed directly against the Nginx reverse proxy on port 80, covering complete user and creator lifecycle paths.
- **Verification**: Verified 100% of user authentication, creator toggle, session CRUD, active/past booking queries, and seat release flows live over HTTP through Nginx.
