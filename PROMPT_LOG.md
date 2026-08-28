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

### [Phase 3] Sessions, Authorization & Concurrency-Safe Booking

- **Model / Tool**: Antigravity (Gemini 3.7 Flash) / IDE Pair Programmer
- **Prompt**: "Implement ONLY Phase 3 — Sessions, Authorization & Concurrency-Safe Booking. Implement Session CRUD (`/api/sessions/`, `/api/sessions/<id>/`), creator permissions (`IsCreator`, `IsSessionOwnerOrReadOnly`), creator booking counts (`/api/sessions/<id>/bookings/`), transactional booking endpoint (`/api/bookings/`) with PostgreSQL `select_for_update` row locking and live count verification, `/api/bookings/mine/` with read-time active/past partitioning, serialized booking cancellation (`/api/bookings/<id>/`), multi-threaded PostgreSQL concurrency race test with 10 threads, and full authorization edge case test suite."
- **What was used**:
  - `IsCreator` and `IsSessionOwnerOrReadOnly` permissions for server-side authorization.
  - Atomic `select_for_update()` transaction locking in `POST /api/bookings/` and `DELETE /api/bookings/<id>/`.
  - Multi-threaded `TransactionTestCase` using `threading.Barrier` for 10-thread simultaneous race condition verification.
  - Read-time partition calculation for `/api/bookings/mine/`.
- **What was changed / rejected**:
  - Rejected caching or pre-calculating booking counts before acquiring the row lock; the count is strictly queried live *inside* the locked transaction.
  - Rejected denormalized seat counters (`seats_remaining` column) to eliminate count drift bugs.
  - Rejected Phase 4 frontend features (Creator Dashboard UI, Booking UI, Catalog UI) to strictly respect Phase 3 boundaries.
- **How it was verified**:
  - Executed full test suite: 48/48 tests passed in 1.77s.
  - Executed 10-thread PostgreSQL concurrency test (`test_booking_concurrency`) 3 consecutive times with 100% stability (exactly 1 success, 9 `SESSION_FULL` rejections, exactly 1 active DB booking).
  - Verified live HTTP booking collision and cancellation/re-booking flows via Nginx and curl/PowerShell.

---

### [Phase 4] Frontend Application & API Integration

- **Model / Tool**: Antigravity (Gemini 3.7 Flash) / IDE Pair Programmer
- **Prompt**: "Implement ONLY Phase 4 — Frontend Application & API Integration. Implement authentication UI (Google login + Dev login fallback), central AuthContext and API client with concurrency-safe JWT refresh handling, Session catalog, Session detail with real-time booking CTA and 409 conflict handling, My Bookings with Active and Past tabs & cancellation, Creator Dashboard with enrollment metrics and attendee list viewer modal, Create/Edit Session forms, Profile management with Creator Mode toggle, responsive layout with design tokens, and build verification."
- **What was used**:
  - React Router v6 with `ProtectedRoute` guards checking `isAuthenticated` and `is_creator`.
  - Unified `client.js` with subscriber queue for mutex-controlled JWT token refresh.
  - Modular pages: `Login`, `Sessions`, `SessionDetail`, `Bookings`, `CreatorDashboard`, `CreateSession`, `EditSession`, `Profile`.
  - Clean vanilla CSS design system with design tokens (`index.css`), glassmorphism, responsive navigation drawer, and Lucide icons.
- **What was changed / rejected**:
  - Rejected optimistic UI updates for booking actions; enforced server-confirmed transitions to prevent race condition rollbacks.
  - Rejected storing tokens in URL query params; strictly isolated tokens to storage and client headers.
  - Rejected hardcoded API endpoints (`localhost:8000`), routing all requests through Nginx proxy `/api/`.
- **How it was verified**:
  - Ran `docker compose exec frontend npm run build` (built cleanly in 2.70s with 0 errors).
  - Executed complete end-to-end integration test of all user and creator flows through Nginx.
  - Re-verified all 48 backend tests and concurrency tests (`test_booking_concurrency`).

---

### [Phase 5] Edge Cases, Concurrency Hardening & Regression Testing

- **Model / Tool**: Antigravity (Gemini 3.7 Flash) / IDE Pair Programmer
- **Prompt**: "Implement ONLY Phase 5 — Edge Cases, Concurrency Hardening & Regression Testing. Harden booking edge cases, cancellation edge cases, cancel/re-book race, multi-capacity concurrency (capacity=1, 2, 5), past/active boundary edge cases, session ownership persistence across creator mode toggle, dev-auth security gating, DB constraint regression, frontend build and Docker persistence."
- **What was used**:
  - Expanded `BookingConcurrencyTestCase` to prove concurrency safety across capacities 1, 2, and 5 with 10 contending threads each.
  - Added concurrent cancel-vs-rebook race test proving `active_bookings <= capacity` under mixed cancellation and booking transactions.
  - Added creator toggle ownership persistence test: user creates session, switches `is_creator=False`, verifies that session ownership and edit/delete permissions are fully preserved while new session creation is blocked.
  - Added dev-auth security gating tests verifying devtoken rejection when `DEBUG=False` or `AUTH_DEV_MODE=False`.
  - Added negative and zero capacity DB constraint regression tests (`CheckConstraint(capacity >= 1)`).
- **What was changed / rejected**:
  - Rejected modifying the core PostgreSQL locking architecture or replacing `select_for_update()`.
  - Rejected weakening any concurrency assertion.
  - Rejected faking browser test results when Playwright driver installation failed; reported limitation honestly while performing comprehensive live HTTP verification.
- **How it was verified**:
  - Full backend test suite executed: 58/58 tests passed in 3.46s.
  - Concurrency test suite executed: 4/4 concurrency scenarios passed in 1.41s.
  - Frontend build re-verified cleanly: 0 errors in 2.90s.
  - PostgreSQL persistence verified across `docker compose restart backend`.

---

### [Phase 6] Production Readiness, Documentation & Deployment Verification

- **Model / Tool**: Antigravity (Gemini 3.7 Flash) / IDE Pair Programmer
- **Prompt**: "Implement ONLY Phase 6 — Production Readiness, Documentation & Deployment Verification. Conduct repository audit, secret scan, .gitignore verification, environment configuration audit, Django security & CORS review, Nginx reverse proxy review, Dockerfile/Compose review, migration reproducibility check, PostgreSQL constraint verification, live smoke testing via http://localhost/, assignment traceability matrix, and evaluator quick-start documentation."
- **What was used**:
  - Repository-wide secret and ignored-file audit confirming zero exposed credentials or temporary artifacts.
  - PostgreSQL live constraint schema verification with `\d+ core_session` and `\d+ core_booking`.
  - Migration reproducibility check with `python manage.py makemigrations --check` (0 drift) and `showmigrations` (all applied).
  - Database persistence check surviving both `backend` and `db` container restarts.
  - Comprehensive Evaluator Quick Start and Assignment Traceability Matrix added to `README.md`.
- **What was changed / rejected**:
  - Rejected squashing git commit history; preserved clean incremental commit progression across all phases.
  - Rejected pushing to GitHub; left remote synchronization strictly to Phase 7.
- **How it was verified**:
  - Executed full suite: 58/58 backend tests passed.
  - Executed 4 multi-threaded concurrency scenarios: 4/4 passed.
  - Production frontend build completed with 0 errors in 2.76s.
  - Database persistence across `docker compose restart backend` and `docker compose restart db` verified without data loss.

---

### What AI Got Wrong / What Was Corrected

1. **Implicit Dependency Assumption (`requests` package missing from `google-auth`)**:
   - *What happened*: AI assumed installing `google-auth` in `requirements.txt` was sufficient to use `from google.auth.transport import requests`. However, `google-auth` does not list `requests` as a hard dependency in its base package distribution, resulting in an `ImportError` on startup.
   - *Correction*: Identified the missing transport requirement, explicitly added `requests>=2.31.0` to `requirements.txt`, rebuilt the container image, and verified clean module resolution.

2. **Permissive Field Mutation in User Profile Updates**:
   - *What happened*: Standard DRF `ModelSerializer` without explicit field fencing would allow a client to update immutable identity attributes (such as `id`, `email`, `oauth_provider`, `oauth_sub`) via `PATCH /api/me/`.
   - *Correction*: Implemented a dedicated `UserProfileUpdateSerializer` with strictly restricted fields (`name`, `first_name`, `last_name`, `bio`, `avatar_url`, `is_creator`) and wrote unit tests verifying that attempts to overwrite `oauth_sub` or `email` are safely ignored.
