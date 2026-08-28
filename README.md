# Ahoum Sessions Marketplace

A compact, concurrency-safe sessions marketplace where **Users** discover and book sessions, and **Creators** create and manage sessions they offer.

---

## 1. Quick Start (Evaluator Setup)

1. **Clone the repository & enter workspace**:
   ```bash
   git clone https://github.com/Tarun-sde/Sessions-Marketplace.git
   cd Sessions-Marketplace
   ```

2. **Copy environment configuration**:
   ```bash
   cp .env.example .env
   ```

3. **Start the complete multi-container stack**:
   ```bash
   docker compose up --build -d
   ```

4. **Verify container health**:
   ```bash
   docker compose ps
   ```

5. **Access the application**:
   - **Marketplace Web App**: `http://localhost/`
   - **Backend API Health Check**: `http://localhost/api/health/`
   - **Django Administration**: `http://localhost/admin/`

---

## 2. Test Execution Commands

All tests run directly against PostgreSQL inside Docker using real multi-threading and database locking (no SQLite, no mocks for concurrency).

### 1. Django System & Configuration Check
```bash
docker compose exec backend python manage.py check
```

### 2. Migration Drift Check (Ensures zero pending schema migrations)
```bash
docker compose exec backend python manage.py makemigrations --check
```

### 3. Multi-Threaded PostgreSQL Concurrency Proof
```bash
docker compose exec backend python manage.py test core.tests.test_booking_concurrency -v 2
```

### 4. Complete Backend Test Suite (58 tests covering auth, models, constraints, permissions, edge cases)
```bash
docker compose exec backend python manage.py test core.tests -v 2
```

### 5. Frontend Production Bundle Build
```bash
docker compose exec frontend npm run build
```

---

## 3. Proving Booking Correctness Under Concurrency

The core engineering mandate of this assignment is provable capacity safety under high-contention concurrent race conditions.

### Concurrency Mechanism
1. **Row-Level Serialization**: Every booking attempt acquires an exclusive row lock on the parent Session row via `Session.objects.select_for_update().get(id=session_id)` within an atomic database transaction (`transaction.atomic()`).
2. **Fresh Aggregate Count**: The active booking count `Booking.objects.filter(session=session, status='active').count()` is evaluated *after* acquiring the row lock, guaranteeing zero count drift.
3. **Database Constraint Backstop**: In addition to application row locking, PostgreSQL enforces a partial unique index:
   ```sql
   CREATE UNIQUE INDEX unique_active_user_session_booking 
   ON core_booking (user_id, session_id) 
   WHERE status = 'active';
   ```
4. **Capacity Constraint**:
   ```sql
   ALTER TABLE core_session ADD CONSTRAINT session_capacity_gte_1 CHECK (capacity >= 1);
   ```

### Concurrency Scenarios Tested (`test_booking_concurrency.py`)
- **10 Workers vs Capacity = 1**: 10 threads synchronized via `threading.Barrier` fire simultaneously. Exactly **1 booking succeeds (201 Created)**, exactly **9 requests receive 409 Conflict (`SESSION_FULL`)**, 0 oversells, active DB bookings == 1.
- **10 Workers vs Capacity = 2**: Exactly **2 succeed (201)**, **8 receive 409 Conflict**, active DB bookings == 2.
- **10 Workers vs Capacity = 5**: Exactly **5 succeed (201)**, **5 receive 409 Conflict**, active DB bookings == 5.
- **Cancel vs. Booking Race**: User A cancels active booking on a full session while multiple users attempt to book the freed seat simultaneously. Row locking on the parent session serializes state transitions; the active booking count never exceeds capacity (`active_bookings <= capacity`).

---

## 4. Authentication Architecture

- **Primary Authentication**: Google OAuth ID token verification. The frontend retrieves Google credentials and POSTs to `/api/auth/google/`. The backend verifies the cryptographic signature with `google-auth` against Google public certificates and matches the immutable Google `sub` claim.
- **Development Escape Hatch (`devtoken:<email>`)**: Enables automated test suites and local evaluators to authenticate without a live Google Client ID.
- **Production Guardrails**: Development authentication is strictly gated behind **dual conditions**:
  ```python
  if not (settings.DEBUG and settings.AUTH_DEV_MODE):
      raise AuthenticationFailed("Development token login is disabled in production.", code="dev_auth_disabled")
  ```
- **JWT Lifecycles**: DRF SimpleJWT issues a 60-minute access token and 7-day refresh token.
- **Coordinated Refresh Queue**: The frontend API client (`client.js`) implements a mutex queue preventing duplicate refresh requests or infinite redirect loops when tokens expire during parallel component fetches.

---

## 5. Architecture & Tech Stack

| Layer | Technology | Role |
|---|---|---|
| **Reverse Proxy** | Nginx (Alpine) | Single entry point on port 80; routes `/api/` to Django and `/` to Vite frontend |
| **Backend** | Django 5.x, DRF | REST API, permissions, serializers, transaction management |
| **Database** | PostgreSQL 16 | Relational data, row-level locks (`select_for_update`), partial unique indices, check constraints |
| **Frontend** | React 18, Vite | SPA catalog, session detail, real-time booking CTA, creator dashboard, profile toggle |
| **Styling** | Vanilla CSS Design System | Design tokens, responsive grid, glassmorphism, Lucide icons |
| **Containerization**| Docker & Docker Compose | Named volumes for persistence, health check dependencies |

---

## 6. Frontend Routes

| Route | Access | Description |
|---|---|---|
| `/login` | Public | Google OAuth login + Development login escape hatch |
| `/sessions` | Authenticated | Session catalog with search, status filters, and seat availability badges |
| `/sessions/:id` | Authenticated | Session detail, creator bio, and live concurrency-safe booking CTA |
| `/bookings` | Authenticated | User bookings partitioned into Active and Past tabs with cancellation |
| `/profile` | Authenticated | Profile view/edit and **Creator Mode** toggle switch |
| `/creator` | Creator Only | Creator dashboard, enrollment metrics, attendee list modal, session actions |
| `/creator/sessions/new` | Creator Only | Create new session form with client & server validation |
| `/creator/sessions/:id/edit` | Creator Only | Edit existing session form |

---

## 7. API Surface

### Authentication & Profile
| Method | Endpoint | Auth Required | Description |
|---|---|---|---|
| `POST` | `/api/auth/google/` | No | Exchange Google ID token (or `devtoken:<email>`) → `{ access, refresh, user }` |
| `POST` | `/api/auth/refresh/` | No | Refresh JWT access token → `{ access }` |
| `GET` | `/api/me/` | Bearer JWT | Retrieve authenticated user profile |
| `PATCH` | `/api/me/` | Bearer JWT | Update profile (`name`, `bio`, `avatar_url`, `is_creator`) |
| `GET` | `/api/health/` | No | Service health check |

### Sessions
| Method | Endpoint | Auth Required | Description |
|---|---|---|---|
| `GET` | `/api/sessions/` | Bearer JWT | Catalog listing (available to all authenticated users) |
| `GET` | `/api/sessions/{id}/` | Bearer JWT | Session detail view with live `remaining_seats` |
| `POST` | `/api/sessions/` | Creator only | Create a new session (`starts_at` in future, `1 <= capacity <= 10000`) |
| `PATCH` | `/api/sessions/{id}/` | Owner only | Update own session details |
| `DELETE` | `/api/sessions/{id}/` | Owner only | Delete own session |
| `GET` | `/api/sessions/{id}/bookings/` | Owner only | View booking list/count for own session |

### Bookings
| Method | Endpoint | Auth Required | Description |
|---|---|---|---|
| `POST` | `/api/bookings/` | Bearer JWT | Concurrency-safe booking with `select_for_update` |
| `GET` | `/api/bookings/mine/` | Bearer JWT | User's bookings split dynamically into `active` and `past` |
| `DELETE` | `/api/bookings/{id}/` | Owner only | Cancel active booking with session row lock (frees seat) |

---

## 8. Assignment Traceability Matrix

| Requirement | Implementation Component | Verification / Test Evidence | Status |
|---|---|---|---|
| **Docker Multi-Container** | `docker-compose.yml`, `backend/Dockerfile`, `frontend/Dockerfile`, `nginx/nginx.conf` | 4 containers (`db`, `backend`, `frontend`, `nginx`) running on port 80 | PASS |
| **PostgreSQL Persistence** | Named volume `ahoum_postgres_data` mapped to `/var/lib/postgresql/data` | Records survive container restarts (`docker compose restart db`) | PASS |
| **Custom User Model** | `core.User` subclassing `AbstractUser` with `AUTH_USER_MODEL` set before migration 0001 | Initial migration `0001_initial.py` applied cleanly | PASS |
| **Google OAuth + JWT** | `core/oauth.py`, SimpleJWT, `/api/auth/google/`, `/api/auth/refresh/` | Cryptographic signature verification + `test_auth_permissions.py` | PASS |
| **Dev Auth Guard** | Gated behind `DEBUG=True` and `AUTH_DEV_MODE=True` | Rejection verified when `DEBUG=False` or `AUTH_DEV_MODE=False` | PASS |
| **Session Management** | CRUD views in `core/views.py`, serializers in `core/serializers.py` | `test_sessions_and_bookings.py` (18 API tests) | PASS |
| **Creator Role & Toggle** | `IsCreator` permission, profile toggle via `PATCH /api/me/` | Creator toggle retains existing session ownership (`test_creator_toggle_retains_existing_session_ownership`) | PASS |
| **Concurrency Row Lock** | `select_for_update()` inside `transaction.atomic()` on parent Session | 10-thread simultaneous race tests (`test_booking_concurrency.py`) | PASS |
| **Capacity Safety** | Fresh count query after acquiring row lock + DB check constraint | 0 oversells across capacity 1, 2, 5 race tests | PASS |
| **Active Booking Uniqueness**| PostgreSQL partial unique index `UNIQUE(user_id, session_id) WHERE status='active'` | `test_booking_active_partial_unique_constraint`, duplicate booking returns 409 | PASS |
| **Booking Cancellation** | `DELETE /api/bookings/{id}/` with parent session row lock | Seat freed immediately; allows re-booking (`test_user_can_rebook_after_own_cancellation`) | PASS |
| **Active vs Past Split** | Read-time dynamic partition in `/api/bookings/mine/` | `test_user_bookings_mine_split_active_and_past` | PASS |
| **Frontend Application** | React 18, Vite, React Router v6, custom CSS design system | `npm run build` succeeds (0 errors), responsive navigation | PASS |
| **Engineering Docs** | `README.md`, `DECISIONS.md`, `DEBUGGING.md`, `PROMPT_LOG.md` | 11 decisions, 4 debugging stories, full prompt logs | PASS |

---

## 9. Known Limitations

1. **Live Google Cloud OAuth**: Requires an external `GOOGLE_CLIENT_ID` provisioned in Google Cloud Console. When not configured, the application seamlessly uses the verified development authentication escape hatch (`devtoken:<email>`).
2. **Browser Playwright Automation**: The host environment's Playwright binary installer encountered an upstream CDN mirror 404 on Windows. Complete end-to-end user workflows were verified via deterministic live HTTP integration tests against Nginx on `http://localhost/`.
