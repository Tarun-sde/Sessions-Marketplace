# Ahoum Sessions Marketplace

A compact sessions marketplace where **Users** discover and book sessions, and **Creators** create and manage sessions they offer.

---

## 1. Proving Booking Correctness Under Concurrency

The core engineering mandate of this assignment is provable capacity safety under concurrent race conditions.

To execute the multi-threaded PostgreSQL race condition test:

```bash
docker compose exec backend python manage.py test core.tests.test_booking_concurrency
```

### Concurrency Mechanism & Invariants Tested
- **Test Setup**: Creates a Session with `capacity = 1` and synchronizes **10 concurrent worker threads** using `threading.Barrier` so all requests hit the database at the exact same millisecond.
- **Locking Pattern**: Uses PostgreSQL row-level locking (`Session.objects.select_for_update()`) inside an atomic database transaction (`transaction.atomic()`).
- **Fresh Count Rule**: Re-queries `Booking.objects.filter(session=session, status='active').count()` *after* acquiring the row lock, ensuring sequential evaluation of the remaining seat.
- **Database Backstop**: Protected by a PostgreSQL partial unique index (`UNIQUE(user_id, session_id) WHERE status='active'`).
- **Guaranteed Invariants**:
  1. Exactly **1 request** receives `201 Created`.
  2. The remaining **9 requests** receive `409 Conflict` (`SESSION_FULL`).
  3. Zero `500` server errors.
  4. Final database active booking count is **exactly 1** (0 oversold).

---

## 2. Tech Stack

- **Backend**: Django 5.x, Django REST Framework, PostgreSQL (`psycopg2-binary`), `djangorestframework-simplejwt`, `google-auth`, `requests`
- **Frontend**: React 18, Vite, React Router, Lucide Icons
- **Database**: PostgreSQL 16
- **Reverse Proxy**: Nginx (Alpine)
- **Infrastructure**: Docker & Docker Compose

---

## 3. Getting Started

### Prerequisites
- Docker & Docker Compose
- (Optional for local non-Docker development): Python 3.11+, Node.js 20+

### Setup & Run
1. Copy the environment configuration:
   ```bash
   cp .env.example .env
   ```
2. Start the full stack with a single command:
   ```bash
   docker compose up --build
   ```
3. Access the application:
   - **Frontend / Application Root**: `http://localhost` (or `http://localhost:5173`)
   - **Backend API Health Check**: `http://localhost/api/health/` (or `http://localhost:8000/api/health/`)
   - **Django Admin**: `http://localhost/admin/`

---

## 4. API Surface

### Authentication & Profile
| Method | Endpoint | Auth Required | Description |
|---|---|---|---|
| `POST` | `/api/auth/google/` | No | Exchange Google ID token (or devtoken) → `{ access, refresh, user }` |
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
| `GET` | `/api/bookings/mine/` | Bearer JWT | User's bookings split into `active` and `past` |
| `DELETE` | `/api/bookings/{id}/` | Owner only | Cancel active booking with session row lock (frees seat) |

---

## 5. Running the Complete Automated Test Suite

To run all 48 unit, permission, constraint, and concurrency tests:

```bash
docker compose exec backend python manage.py test core.tests -v 2
```

---

## 6. Database Persistence Mechanism

Database data is persisted using a named Docker volume `ahoum_postgres_data` mapped to `/var/lib/postgresql/data` inside the PostgreSQL container:

```yaml
volumes:
  - postgres_data:/var/lib/postgresql/data
```

This ensures database records survive container restarts and rebuilds.
