# Ahoum Sessions Marketplace

A compact sessions marketplace where **Users** discover and book sessions, and **Creators** create and manage sessions they offer.

---

## 1. Tech Stack

- **Backend**: Django 5.x, Django REST Framework, PostgreSQL (`psycopg2-binary`), `djangorestframework-simplejwt`, `google-auth`
- **Frontend**: React 18, Vite, React Router, Lucide Icons
- **Database**: PostgreSQL 16
- **Reverse Proxy**: Nginx (Alpine)
- **Infrastructure**: Docker & Docker Compose

---

## 2. Repository Structure

```text
ahoum-sessions-marketplace/
├── docker-compose.yml           # 4-container orchestration (db, backend, frontend, nginx)
├── .env.example                 # Environment variable template
├── README.md                    # Setup, architecture & persistence documentation
├── DECISIONS.md                 # Technical decision log
├── DEBUGGING.md                 # Real debugging log and issue resolutions
├── PROMPT_LOG.md                # AI supervision and prompt log
├── backend/
│   ├── Dockerfile               # Python 3.11-slim container definition
│   ├── requirements.txt         # Python dependencies
│   ├── entrypoint.sh            # DB wait & migration entrypoint
│   ├── manage.py
│   ├── config/
│   │   ├── settings.py          # Django settings (PostgreSQL, custom User, CORS)
│   │   ├── urls.py              # Root URL configuration (/api/ routing)
│   │   └── wsgi.py
│   └── core/
│       ├── admin.py             # User admin registration
│       ├── apps.py
│       ├── models.py            # Custom User model (configured before migrations)
│       ├── urls.py              # Core API endpoints & health check
│       ├── views.py
│       └── migrations/
├── frontend/
│   ├── Dockerfile               # Node 20-alpine container
│   ├── package.json
│   ├── vite.config.js           # Vite dev server configuration (host 0.0.0.0, port 5173)
│   ├── index.html
│   └── src/
│       ├── App.jsx              # Foundational React application
│       ├── main.jsx             # React entry point
│       └── index.css            # Base styles
└── nginx/
    └── nginx.conf               # Reverse proxy config (routes /api/ to backend, / to frontend)
```

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

## 4. Architecture & Service Communication

```
Browser / Client
       │
       ▼ (Port 80)
┌──────────────────────────────────────┐
│            Nginx Proxy               │
└──────────────┬───────────────────────┘
               │
      ┌────────┴────────┐
      ▼ (/api/, /admin/) ▼ (/)
┌──────────────┐ ┌──────────────┐
│   Backend    │ │   Frontend   │
│ (Django:8000)│ │ (Vite:5173)  │
└──────┬───────┘ └──────────────┘
       │
       ▼ (Port 5432)
┌──────────────┐
│  PostgreSQL  │
│  (Database)  │
└──────────────┘
```

- **Reverse Proxy (`nginx`)**: Routes incoming port 80 traffic to either `backend:8000` (for `/api/`, `/admin/`, `/static/`) or `frontend:5173` (for web UI and Vite HMR).
- **Backend (`backend`)**: Communicates with `db` via Docker internal network using standard PostgreSQL credentials.
- **Frontend (`frontend`)**: Serves the single-page application and handles client-side rendering.

---

## 5. Database Persistence Mechanism

Database data is persisted using a named Docker volume `ahoum_postgres_data` mapped to `/var/lib/postgresql/data` inside the PostgreSQL container:

```yaml
volumes:
  - postgres_data:/var/lib/postgresql/data
```

This ensures that:
1. Stopping, restarting, or rebuilding application containers (`backend`, `frontend`, `nginx`) does **not** erase database tables or data.
2. Even if the backend container is destroyed and recreated (`docker compose restart backend` or `docker compose up -d --no-deps --build backend`), PostgreSQL maintains active connections and disk state across lifecycle events.

---

## 6. Proving Booking Correctness Under Concurrency (Coming in Phase 3)

The concurrency test suite will be executed via:
```bash
docker compose exec backend python manage.py test core.tests.test_booking_concurrency
```
