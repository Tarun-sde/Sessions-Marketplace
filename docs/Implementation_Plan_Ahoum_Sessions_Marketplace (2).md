# Implementation Plan: Sessions Marketplace
**Companion to PRD_Ahoum_Sessions_Marketplace.md**

This plan makes concrete decisions where the PRD left options open, so it can be followed directly. Where a choice is made, the reasoning is stated briefly — most of these become entries in `DECISIONS.md` verbatim.

---

## 0. Locked-in Technical Decisions

| Question | Decision | Why |
|---|---|---|
| Role model | Single `is_creator` boolean on `User`, not a separate role table | A creator is very often also a booker of other sessions; a boolean avoids modeling two mutually exclusive personas that don't reflect reality |
| OAuth provider | Google only | Stateless `id_token` verification server-side, no code-exchange/client-secret handling needed on the frontend — fastest to get *actually working* in the time budget. Documented as a scoped decision, not a shortcut hidden from the evaluator |
| Capacity enforcement | Row-level lock (`SELECT ... FOR UPDATE`) on the `Session` row inside the booking transaction, re-count active bookings, then insert | Postgres has no declarative constraint for "count of related rows ≤ N"; locking the parent row serializes concurrent booking attempts without needing a separate counter column that can drift out of sync |
| Double-booking prevention | DB-level partial unique constraint: `UNIQUE(user_id, session_id) WHERE status='active'` | Enforced even if application logic has a bug or a request bypasses the normal code path — the strongest possible guarantee |
| "Session already started" check | Application-layer only (`starts_at <= now()` at request time) | Time-based business rule, best kept where a clear error message can be returned; not safety-critical the way overselling is, so DB-level duplication isn't worth the added complexity |
| Token storage on frontend | Access token in memory (React state/context), refresh token in `localStorage` | Simplest within the time budget; documented trade-off vs. httpOnly cookies (XSS exposure) in `DECISIONS.md` |
| "Past" vs "active" booking | Computed at read time from `session.starts_at`, not a stored/cron-updated field | Avoids a background job just to flip a status; one less moving part to get wrong in 24 hours |
| Catalog visibility | Authenticated-only, both roles see the same list | The brief's "public catalog" means "not owner-restricted," not "unauthenticated" — the whole app is OAuth-gated and no anonymous flow exists elsewhere in the spec. Fixes an internal inconsistency between the PRD's wording and this plan's `[auth required]` API contract |
| `is_creator` transitions | Any authenticated user may set their own flag to `true`; setting it back to `false` does not affect ownership of sessions already created, it only blocks creating new ones | Keeps the permission model simple (ownership check is always `creator_id == request.user.id`, independent of the current flag value) while still gating new-session creation on the flag |
| Cancellation semantics | Cancelling an active booking immediately frees the seat; the same user may re-book the same session afterward if it hasn't started | Falls directly out of the partial unique constraint being scoped to `status='active'` — a cancelled row no longer blocks a new active one for that `(user, session)` pair |

---

## 1. Repository Layout

```
ahoum-sessions-marketplace/
├── docker-compose.yml
├── .env.example
├── README.md
├── DECISIONS.md
├── DEBUGGING.md
├── PROMPT_LOG.md
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── manage.py
│   ├── config/
│   │   ├── settings.py
│   │   ├── urls.py
│   │   ├── wsgi.py
│   └── core/
│       ├── models.py            # User, Session, Booking
│       ├── serializers.py
│       ├── permissions.py       # IsCreator, IsSessionOwnerOrReadOnly
│       ├── oauth.py              # Google id_token verification
│       ├── exceptions.py        # consistent {"error": {...}} shape
│       ├── views.py
│       ├── urls.py
│       ├── admin.py
│       ├── migrations/
│       └── tests/
│           ├── test_booking_concurrency.py
│           └── test_auth_permissions.py
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── main.jsx
│       ├── App.jsx
│       ├── api.js                # fetch wrapper, attaches JWT, handles 401 refresh
│       ├── context/AuthContext.jsx
│       ├── pages/
│       │   ├── Login.jsx
│       │   ├── Catalog.jsx
│       │   ├── SessionDetail.jsx
│       │   ├── CreatorDashboard.jsx
│       │   └── Profile.jsx
│       └── components/
└── nginx/
    └── nginx.conf
```

---

## 2. Data Model — Exact Fields

**User** (extends Django's `AbstractUser`)
- `email` — unique, required
- `is_creator` — boolean, default `False`
- `oauth_provider` — charfield (`"google"`)
- `oauth_sub` — charfield (Google's `sub` claim), unique together with provider
- `bio`, `avatar_url` — optional profile fields

**Session**
- `creator` — FK → User
- `title`, `description`
- `starts_at` — datetime
- `capacity` — positive int, `CHECK (capacity >= 1)`
- `location`
- `created_at`, `updated_at`

**Validation rules (serializer-level, on create/update):**
- `starts_at` must parse as a valid datetime and must be in the future at creation time — a session cannot be created already-started or already-past. (Note: this is a *creation-time* check only; a session legitimately transitions from bookable to non-bookable as real time passes, which is a separate check enforced at booking time, not at session-edit time.)
- `capacity` must be a positive integer, with a sensible upper bound (e.g. 10,000) to reject obvious garbage input — not a business requirement from the brief, just basic input hygiene.
- Update/delete: enforced by `IsSessionOwnerOrReadOnly` — `obj.creator_id == request.user.id`, independent of the requester's *current* `is_creator` flag value (see §0).

**Booking**
- `user` — FK → User
- `session` — FK → Session
- `status` — `active` | `cancelled`
- `created_at`
- Constraint: `UNIQUE(user, session) WHERE status = 'active'`

Derived (not stored): `session.remaining_seats = capacity - count(active bookings)` — computed for display only, never trusted for enforcement.

---

## 3. Concurrency-Safe Booking — Exact Algorithm

```
POST /api/bookings/  { session_id }

with transaction.atomic():
    session = Session.objects.select_for_update().get(id=session_id)   # ① lock

    if session.starts_at <= now():
        raise Conflict("SESSION_ALREADY_STARTED")

    if Booking.objects.filter(user=request.user, session=session,
                               status="active").exists():
        raise Conflict("ALREADY_BOOKED")                               # ② fast pre-check

    if session.active_booking_count >= session.capacity:
        raise Conflict("SESSION_FULL")                                 # ③ re-check under lock

    Booking.objects.create(user=request.user, session=session,
                            status="active")                           # ④ DB unique
                                                                         #    constraint is
                                                                         #    the real backstop
                                                                         #    for ②
```

Why this is correct: step ① means any second concurrent request for the *same session* blocks at the database level until the first transaction commits or rolls back. By the time it acquires the lock, it re-reads `active_booking_count` fresh — so it sees the first request's booking if that one committed. Step ④'s unique constraint is what actually guarantees no duplicate active booking even if step ② had a bug or the code path were reached twice.

**Implementation guard:** `active_booking_count` must remain a plain property that issues a fresh `Booking.objects.filter(session=self, status="active").count()` on every access — never cache it on the instance or compute it once outside the locked block. The correctness of step ③ depends entirely on that count being read *after* the lock in step ① is held, not before.

**Alternative considered and rejected:** a denormalized `seats_remaining` counter on `Session`, decremented via `F('seats_remaining') - 1` inside the same locked transaction. Rejected because the counter can silently drift from the true count if a booking is ever cancelled, deleted, or modified outside this one code path (e.g. directly in `psql`, or a future admin action) — the counter has no way to self-correct, whereas counting active `Booking` rows live is always internally consistent by construction. This is a good `DECISIONS.md` entry: *ambiguity* = how to track remaining capacity efficiently; *options* = denormalized counter vs. live count under lock; *choice* = live count; *trade-off* = one extra `COUNT` query per booking attempt vs. a class of drift bugs that would be hard to detect in testing.

**Proof/test plan:**
- `TransactionTestCase` (not `TestCase` — need real commits across threads) creates one session with `capacity=1`.
- Spin up N (e.g. 10) threads, each with its own DB connection, all calling the booking service function for different users against the same session at roughly the same time (use a `threading.Barrier` to line them up).
- Assert: exactly 1 `Booking` row with `status="active"` exists afterward; the other 9 raised the expected `SESSION_FULL` conflict.
- Run this against **Postgres**, not SQLite — SQLite's coarse whole-database lock would make the test pass for the wrong reason (see `DEBUGGING.md` entry).

---

## 4. Auth Flow — Exact Sequence

1. Frontend loads Google Identity Services script, renders "Sign in with Google" button.
2. Google returns an `id_token` (JWT) to the frontend directly — no backend involvement yet.
3. Frontend `POST /api/auth/google/ { id_token }`.
4. Backend verifies the token's signature, issuer, and audience (`google-auth` library, `verify_oauth2_token`), extracts `sub`/`email`/`name`.
5. Backend `get_or_create`s a `User` keyed on `(oauth_provider="google", oauth_sub=claims["sub"])`.
6. Backend issues `{access, refresh}` via `djangorestframework-simplejwt`'s `RefreshToken.for_user(user)`.
7. Frontend stores `access` in memory, `refresh` in `localStorage`; attaches `Authorization: Bearer <access>` to subsequent requests.
8. On a 401 with `code=token_not_valid`, frontend silently calls `/api/auth/refresh/` once and retries the original request; if that also fails, it logs the user out and redirects to `/login`.
9. **Dev-mode escape hatch:** if `AUTH_DEV_MODE=true` and `DEBUG=true`, `/api/auth/google/` also accepts a synthetic token of the form `devtoken:<email>` and skips real Google verification — so the evaluator (or you) can exercise the whole flow without registering real OAuth credentials, if they choose to. Must default to `false` in any non-dev `.env`. This is disclosed explicitly in `README.md` and `DECISIONS.md`, not hidden.

---

## 5. API Contract

```
POST   /api/auth/google/
  → { id_token: string }
  ← 200 { access, refresh, user: {id, email, name, is_creator} }
  ← 401 { error: { code, message } }   # bad/expired Google token

POST   /api/auth/refresh/
  → { refresh: string }
  ← 200 { access: string }

GET    /api/me/                        [auth required]
PATCH  /api/me/                        [auth required]
  → { name?, bio?, avatar_url?, is_creator? }

GET    /api/sessions/                  [auth required] ?page=
GET    /api/sessions/{id}/             [auth required]
POST   /api/sessions/                  [Creator only]
  → { title, description, starts_at, capacity, location }
PATCH  /api/sessions/{id}/              [Creator, owner only]
DELETE /api/sessions/{id}/              [Creator, owner only]
GET    /api/sessions/{id}/bookings/     [Creator, owner only]
  ← [{ id, user: {id, name}, status, created_at }]

POST   /api/bookings/                  [auth required]
  → { session_id }
  ← 201 { id, session_id, status, created_at }
  ← 409 { error: { code: "SESSION_FULL" | "ALREADY_BOOKED" | "SESSION_STARTED", message } }

GET    /api/bookings/mine/             [auth required]
  ← { active: [...], past: [...] }

DELETE /api/bookings/{id}/             [auth required, owner only]
```

Error shape (all errors, from the custom DRF exception handler):
```json
{ "error": { "code": "session_full", "message": "This session has no remaining seats." } }
```

---

## 6. Build Order (24h, with checkpoints)

**Phase 1 — Foundation (hrs 0–3)**
- [ ] `django-admin startproject`, `core` app, custom `User` model set as `AUTH_USER_MODEL` *before* first migration (cannot be changed after)
- [ ] `docker-compose.yml` skeleton: `db` (postgres), `backend`, `frontend`, `nginx`
- [ ] `.env.example` with every var the compose file references
- [ ] Verify `docker compose up --build` boots all 4 containers and `db` volume persists across `docker compose restart backend`

**Phase 2 — Models + Auth (hrs 3–7)**
- [ ] `models.py`: User, Session, Booking + constraints
- [ ] `makemigrations` / `migrate`, confirm partial unique index appears in `\d+ booking` in psql
- [ ] `core/oauth.py` Google verification + dev-mode escape hatch
- [ ] `/api/auth/google/`, `/api/auth/refresh/`, `/api/me/` (GET/PATCH)
- [ ] Manual test: real Google OAuth end-to-end once, using a real Google Cloud OAuth client if available; otherwise dev-mode token, documented as such

**Phase 3 — Sessions + Booking core (hrs 7–12)**
- [ ] Session CRUD viewset with `IsCreator` (create) + `IsSessionOwnerOrReadOnly` (update/delete)
- [ ] Booking endpoint implementing the exact algorithm in §3
- [ ] `test_booking_concurrency.py` — the race-condition proof, run against Postgres
- [ ] `test_auth_permissions.py` — at minimum: expired token → 401, User → Creator endpoint → 403, Creator editing another's session → 403

**Phase 4 — Frontend (hrs 12–16)**
- [ ] `AuthContext` + Google sign-in button + token refresh interceptor in `api.js`
- [ ] Catalog (list + filters minimal), Session Detail (book button, remaining seats display, disabled state when full/started)
- [ ] Creator Dashboard: create/edit/delete session forms, booking counts
- [ ] Profile page: edit name/bio, toggle "become a creator"
- [ ] Graceful OAuth-failure UI state (not a blank screen)
- [ ] Google sign-in button degrades cleanly if `GOOGLE_CLIENT_ID` is unset/misconfigured client-side — render a disabled button with an inline message rather than letting the Google script's own error throw and crash the React tree

**Phase 5 — Edge cases + remaining tests (hrs 16–19)**
- [ ] Double-booking attempt → 409, verified with a test
- [ ] Booking a started session → 409, verified with a test
- [ ] Cancel booking → frees the seat for someone else (confirm via test)
- [ ] **Cancel/re-book race, explicitly tested:** session at capacity, user A cancels their active booking, user B (already waiting) books concurrently with A's cancel — assert exactly one of {A re-books, B books} succeeds if only one seat opens, and that the partial unique constraint on `(user, session) WHERE status='active'` is what allows A to legitimately re-book after their own row flips to `cancelled` (not a leftover row blocking them)
- [ ] Cancellation itself must go through the same `select_for_update` lock on the session before flipping `status → cancelled`, so a cancel and a concurrent booking attempt on the same session can't interleave unsafely

**Phase 6 — Docs (hrs 19–22)**
- [ ] `DECISIONS.md` — write up the §0 decisions with the ambiguity/options/trade-off framing (pick the 3–4 most substantive, not everything)
- [ ] `DEBUGGING.md` — capture real issues hit during Phases 2–5 (SQLite-vs-Postgres locking semantics is a strong candidate if it comes up; otherwise use whatever actually broke)
- [ ] `PROMPT_LOG.md` — fill in as you go, not reconstructed from memory at the end (see §7)
- [ ] `README.md` — setup, architecture diagram (text is fine), limitations, "next 24h" section
- [ ] `README.md` must give the concurrency test top billing, not bury it as one bullet in a test list — this is the single most heavily-weighted correctness requirement in the brief and should be trivial for an evaluator to find and run in isolation. Include, near the top of the README (e.g. right after setup instructions), something like:

  ```
  ## Proving booking correctness under concurrency

  docker compose exec backend python manage.py test core.tests.test_booking_concurrency

  This spins up 10 concurrent booking attempts against a session with
  exactly 1 remaining seat and asserts:
    - exactly 1 booking is created with status="active"
    - the other 9 requests receive SESSION_FULL (409), not errors or
      duplicate confirmations
  ```

**Phase 7 — Buffer (hrs 22–24)**
- [ ] Fresh clone + `docker compose up --build` on a clean checkout — this catches "works on my machine" `.env` drift
- [ ] Squash any "wip" commits that shouldn't ship as-is; confirm commit history tells a coherent story

---

## 7. PROMPT_LOG Discipline

Log each material prompt **as you send it**, not retroactively:
```markdown
### [Phase 3] Booking concurrency logic
**Tool:** Claude
**Prompt:** "..."
**Used:** the select_for_update + re-check pattern
**Changed:** removed a counter-column approach it suggested first — rejected
  because a counter can drift from the true count if a booking is ever
  deleted outside the ORM
**Verified:** ran test_booking_concurrency.py against Postgres, 10 threads,
  1 capacity, confirmed exactly 1 success
```
Keep 2 "what AI got wrong" entries honest and specific — e.g. an AI suggestion to enforce capacity purely with a `CheckConstraint` on a denormalized counter (doesn't work declaratively in Postgres for aggregate counts across rows) is a good real example if it comes up.

---

## 8. Things to Watch For, Not Pre-Write

`DEBUGGING.md` is only credible if the two entries are things that actually happened during this build. Do not pre-populate it with plausible-sounding bugs before hitting them. Two candidates worth watching for *while testing*, and writing up only if they really occur:
- **JWT clock skew:** if the backend container's clock and the machine issuing test requests drift, a freshly-issued token can appear expired or "issued in the future," causing an immediate 401. Worth a quick sanity check (`docker compose exec backend date` vs. host `date`) early in Phase 2, before it costs debugging time later.
- **SQLite vs. Postgres locking semantics:** if `TEST_WITH_SQLITE` is ever used for a quick local pass, the concurrency test can pass for the wrong reason (SQLite's single-writer lock, not real row-level locking). This is a legitimate `DEBUGGING.md` entry *if you actually run the test under SQLite first and see it pass, then confirm it's not meaningfully validating anything until run under Postgres* — that's a real "failed assumption exposed through testing," not a fabricated one.

## 9. Definition of Done (self-check before submitting)

- [ ] `docker compose up --build` works from a clean clone with only `.env.example` → `.env`
- [ ] Concurrency test passes against Postgres and is runnable with a single documented command
- [ ] A User cannot reach any Creator-only endpoint (verified by test, not just by UI hiding)
- [ ] All 4 required docs exist and each meets its minimum bar (3 decisions / 2 debug stories / prompt log with 2 "AI got it wrong" examples)
- [ ] Commit history shows incremental progress, not one dump commit
