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

### What AI Got Wrong / What Was Corrected

*(Specific corrections and rejected patterns will be documented here as development progresses)*
