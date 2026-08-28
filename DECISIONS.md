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

---

### Decision 6: Concurrency-Safe Capacity Enforcement via PostgreSQL Row-Level Lock (`select_for_update`) + Live Aggregate Count

- **Problem / Ambiguity**: When multiple users simultaneously attempt to book the final available seat on a session, frontend checks or non-atomic application checks suffer from race conditions leading to oversold sessions.
- **Options Considered**:
  1. Rely on frontend-rendered `remaining_seats` to disable booking buttons.
  2. Denormalized counter column on `Session` (`seats_remaining`) decremented via `F('seats_remaining') - 1` with a check constraint.
  3. PostgreSQL row-level locking (`Session.objects.select_for_update().get(id=session_id)`) inside `transaction.atomic()`, followed by a fresh live count of `Booking.objects.filter(session=session, status='active').count()`.
- **Choice Made**: Option 3. Row-level lock serializes competing transactions on the parent Session row; fresh count inside the lock eliminates count drift.
- **Trade-offs**: Option 1 offers 0 race condition protection (renders stale immediately). Option 2 risks silent counter drift if records are modified outside a single ORM path. Option 3 incurs one extra indexed `COUNT()` query per booking attempt in exchange for 100% provable consistency under high contention.

---

### Decision 7: Serialized Booking Cancellation with Parent Session Row Locking

- **Problem / Ambiguity**: If User A cancels a booking at the exact same millisecond that User B attempts to book a full session, an unsynchronized cancellation could interleave with the booking count check and cause race anomalies or deadlocks.
- **Options Considered**:
  1. Execute a simple `Booking.objects.filter(id=pk).update(status='cancelled')` without locking the parent session.
  2. Acquire a `select_for_update()` lock on the parent `Session` inside the cancellation transaction before flipping `status = 'cancelled'`.
- **Choice Made**: Option 2. Lock the parent `Session` during cancellation.
- **Trade-offs**: Slightly increased lock coordination during cancellation in exchange for strictly serialized interleaving between seat releases and new booking claims.

---

### Decision 8: Read-Time Partitioning of Active vs. Past User Bookings

- **Problem / Ambiguity**: Bookings naturally transition from "active" to "past" as real time passes beyond `session.starts_at`. How to present this split to users in `/api/bookings/mine/`.
- **Options Considered**:
  1. A background cron worker / celery beat task running every minute to flip database status columns from `'active'` to `'past'`.
  2. Compute the active vs. past partition at read time based on `booking.session.starts_at <= timezone.now()`.
- **Choice Made**: Option 2. Dynamically partition at read time.
- **Trade-offs**: Avoids adding an asynchronous worker, message broker, and cron infrastructure to the stack, eliminating a significant operational failure mode while guaranteeing real-time accuracy down to the second.

---

### Decision 9: Centralized API Client with Subscriber Queue for Coordinated JWT Refresh

- **Problem / Ambiguity**: When a user's short-lived JWT access token expires while multiple asynchronous components fire API requests simultaneously, naive interceptors fire multiple concurrent `/api/auth/refresh/` requests or trigger infinite redirect loops.
- **Options Considered**:
  1. Catch 401 in individual page components and trigger full page reloads.
  2. Interceptor with a boolean mutex (`isRefreshing`) and subscriber queue (`refreshSubscribers`) in `client.js`. While one refresh request is in flight, subsequent 401s subscribe to the pending refresh promise and replay automatically once the new access token arrives.
- **Choice Made**: Option 2. Centralized client-level subscriber queue.
- **Trade-offs**: Small amount of queue state management in exchange for zero duplicate refresh calls, seamless transparent request replay, and guaranteed prevention of 401 redirect loops.

---

### Decision 10: Server-Confirmed Booking State Interleaving over Optimistic Updates

- **Problem / Ambiguity**: If the frontend optimistically marks a booking as "Confirmed" before the backend responds, high-contention scenarios (where another user claimed the last seat) result in jarring UI rollback and corrupted user expectations.
- **Options Considered**:
  1. Optimistically display "Booked" immediately upon button click, and revert if the server returns 409 `SESSION_FULL`.
  2. Show a clean pending spinner on the button, wait for server confirmation, and on 409 conflict, immediately re-fetch the session detail to update remaining seats and display the specific collision error message.
- **Choice Made**: Option 2. Server-confirmed state transitions with instant conflict-triggered re-sync.
- **Trade-offs**: Eliminates ghost confirmations and ensures that the user interface never lies about seat acquisition under concurrency.
