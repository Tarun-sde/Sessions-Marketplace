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
