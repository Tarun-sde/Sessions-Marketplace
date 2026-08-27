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
- **Choice Made**: Option 2. Named volume mapped to `/var/lib/postgresql/data`.
- **Trade-offs**: Avoids host filesystem permission and OS-specific file locking inconsistencies (especially across Windows/Linux Docker environments) while guaranteeing data survives container restarts.
