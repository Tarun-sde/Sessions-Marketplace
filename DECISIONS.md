# Engineering Decisions Log

This document records non-trivial technical and architectural decisions made during development, formatted as: Problem/Ambiguity → Options Considered → Choice Made → Trade-offs.

---

### Decision 1: Custom User Model Established Prior to Initial Migrations

- **Problem / Ambiguity**: Django's default `auth.User` model becomes deeply embedded across foreign keys and migration history if initial migrations run before configuring `AUTH_USER_MODEL`. The PRD requires custom fields (`is_creator`, `oauth_provider`, `oauth_sub`, `bio`, `avatar_url`) and role switching.
- **Options Considered**:
  1. Use Django default `User` with a separate `UserProfile` table linked via `OneToOneField`.
  2. Subclass `AbstractUser` as `core.User` and define `AUTH_USER_MODEL = 'core.User'` in `settings.py` before generating any migration files.
- **Choice Made**: Option 2. Subclass `AbstractUser` directly in `core/models.py`.
- **Trade-offs**: Avoids extra SQL `JOIN` overhead for profile and creator flag lookups on every authenticated request, simplifies JWT claims generation, and prevents disastrous mid-project schema migration refactoring.

---

### Decision 2: 4-Container Docker Topology with Dedicated Nginx Reverse Proxy

- **Problem / Ambiguity**: How to structure the development and runtime environment so that frontend, backend, database, and routing operate with clear separation of concerns.
- **Options Considered**:
  1. Run frontend and backend directly on host ports (5173, 8000) with CORS headers handling cross-origin requests.
  2. Unify frontend, backend, PostgreSQL, and Nginx in Docker Compose, exposing port 80 as single entry point.
- **Choice Made**: Option 2. Nginx routes `/api/` to `backend:8000` and `/` to `frontend:5173`.
- **Trade-offs**: Single port entry point mirrors production topology and prevents CORS preflight issues across domain origins, while maintaining independent container rebuildability and lifecycle control.

---

### Decision 3: PostgreSQL Data Persistence via Named Docker Volume

- **Problem / Ambiguity**: Ensuring database records survive application-container restarts, builds, and code updates without accidental data loss.
- **Options Considered**:
  1. Bind-mount a host folder (`./postgres_data`).
  2. Use a Docker named volume (`ahoum_postgres_data`).
  3. Ephemeral container storage without persistence.
- **Choice Made**: Option 2. Named volume mapped to `/var/lib/postgresql/data`.
- **Trade-offs**: Avoids host filesystem permission and OS-specific file locking inconsistencies (especially across Windows/Linux Docker environments) while guaranteeing data survives container restarts.

---

### Decision 4: Stateless Google OAuth ID Token Verification with Development Auth Gating

- **Problem / Ambiguity**: How to authenticate users securely via OAuth without requiring server-side client secrets or fragile redirect loops, while allowing evaluators and automated test suites to run without hard dependencies on live third-party cloud credentials.
- **Options Considered**:
  1. Authorization Code Flow with backend client secret exchange.
  2. Frontend Google credential retrieval followed by backend ID token cryptographic verification (`google-auth` library) keyed on `(oauth_provider='google', oauth_sub=claims['sub'])`, augmented with a development token escape hatch (`devtoken:<email>`) strictly gated behind `AUTH_DEV_MODE=True` and `DEBUG=True`.
- **Choice Made**: Option 2. Cryptographic verification of Google ID token claims as the primary source of identity, with dual-condition development gating.
- **Trade-offs**: Simplifies client-side OAuth integration and guarantees immutable user lookup by stable Google `sub` claim. The development escape hatch provides 100% testability without committing live OAuth secrets, while `AUTH_DEV_MODE` and `DEBUG` guardrails prevent accidental activation in production.

---

### Decision 5: Partial Unique Index for Active Booking Uniqueness

- **Problem / Ambiguity**: A user may only hold at most one active booking for any given session, but should be permitted to cancel a booking and subsequently book the session again if seats remain available.
- **Options Considered**:
  1. Global unique constraint on `(user_id, session_id)` in the `Booking` table.
  2. Application-layer existence check (`Booking.objects.filter(user=..., session=..., status='active').exists()`).
  3. PostgreSQL partial unique constraint: `UNIQUE(user_id, session_id) WHERE status = 'active'`.
- **Choice Made**: Option 3. PostgreSQL partial unique index via Django's `UniqueConstraint(fields=['user', 'session'], condition=Q(status='active'))`.
- **Trade-offs**: Option 1 incorrectly prevents a user from re-booking after cancellation. Option 2 is vulnerable to concurrent race conditions and application logic bypasses. Option 3 guarantees database-level invariant enforcement without blocking valid lifecycle state transitions.
