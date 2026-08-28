# AI Prompt & Supervision Log

This log documents AI interactions, model responses, supervision, rejections/modifications, and verification methods.

---

### [Phase 1] Project Foundation & Docker Infrastructure Scaffolding

- **Model / Tool**: Antigravity (Gemini 3.7 Flash) / IDE Pair Programmer
- **Prompt**: "Implement ONLY Phase 1 — Foundation (hours 0–3) from the Implementation Plan. Initialize Django with custom User model before initial migrations, Docker Compose (db, backend, frontend, nginx), .env.example, .gitignore, README.md, DECISIONS.md, DEBUGGING.md, PROMPT_LOG.md."
- **What was used**:
  - 4-container Docker Compose definition (`db`, `backend`, `frontend`, `nginx`) with health checks.
  - Custom `User` model inheriting from `AbstractUser` with `AUTH_USER_MODEL = 'core.User'`.
  - Nginx reverse proxy routing `/api/` to Django and `/` to Vite dev server.
- **What was changed / rejected**:
  - Rejected creating default auth migrations prior to setting `AUTH_USER_MODEL`.
  - Rejected hardcoded database credentials in `settings.py`, routing all config through environment variables loaded via `dotenv` and Compose.
  - Rejected complex UI templates or feature implementations at this stage, strictly keeping frontend and backend to minimal booting foundations.
- **How it was verified**:
  - Executed `docker compose up --build` and verified all 4 containers (`db`, `backend`, `frontend`, `nginx`) healthy and running.
  - Verified backend communication with PostgreSQL via `/api/health/`.
  - Executed `docker compose restart backend` to verify database persistence across backend container restarts.

---

### [Phase 2] Data Models, Google OAuth, and JWT Authentication

- **Model / Tool**: Antigravity (Gemini 3.7 Flash) / IDE Pair Programmer
- **Prompt**: "Implement ONLY Phase 2 — Models + Authentication. Complete User, Session, and Booking models with DB constraints (capacity >= 1 CheckConstraint, UNIQUE(user_id, session_id) WHERE status='active' partial unique index), Google ID token verification in oauth.py with dev escape hatch, JWT issuance/refresh, GET/PATCH /api/me/ endpoints, DRF custom exception handler, and comprehensive tests."
- **What was used**:
  - `Session` and `Booking` models with PostgreSQL `CheckConstraint` and `UniqueConstraint(condition=Q(status='active'))`.
  - Google ID-token cryptographic verification using `google.auth` and SimpleJWT token generator (`RefreshToken.for_user`).
  - `/api/auth/google/`, `/api/auth/refresh/`, and `/api/me/` endpoints.
  - Custom exception handler normalizing errors to `{"error": {"code": "...", "message": "..."}}`.
- **What was changed / rejected**:
  - Rejected unverified JWT payload extraction without cryptographic signature verification.
  - Rejected allowing `id`, `email`, `oauth_provider`, `oauth_sub`, or `password` modifications via `PATCH /api/me/`.
  - Rejected Phase 3 booking concurrency implementation (`select_for_update`, booking creation endpoint) to keep phase boundaries strictly respected.
- **How it was verified**:
  - Executed `python manage.py test core.tests` (22/22 unit and integration tests passed).
  - Verified PostgreSQL table schemas and constraints with `\d+ core_session` and `\d+ core_booking`.
  - Verified live API endpoints over HTTP via Nginx reverse proxy using curl and PowerShell `Invoke-RestMethod`.

---

### What AI Got Wrong / What Was Corrected

1. **Implicit Dependency Assumption (`requests` package missing from `google-auth`)**:
   - *What happened*: AI assumed installing `google-auth` in `requirements.txt` was sufficient to use `from google.auth.transport import requests`. However, `google-auth` does not list `requests` as a hard dependency in its base package distribution, resulting in an `ImportError` on startup.
   - *Correction*: Identified the missing transport requirement, explicitly added `requests>=2.31.0` to `requirements.txt`, rebuilt the container image, and verified clean module resolution.

2. **Permissive Field Mutation in User Profile Updates**:
   - *What happened*: Standard DRF `ModelSerializer` without explicit field fencing would allow a client to update immutable identity attributes (such as `id`, `email`, `oauth_provider`, `oauth_sub`) via `PATCH /api/me/`.
   - *Correction*: Implemented a dedicated `UserProfileUpdateSerializer` with strictly restricted fields (`name`, `first_name`, `last_name`, `bio`, `avatar_url`, `is_creator`) and wrote unit tests verifying that attempts to overwrite `oauth_sub` or `email` are safely ignored.
