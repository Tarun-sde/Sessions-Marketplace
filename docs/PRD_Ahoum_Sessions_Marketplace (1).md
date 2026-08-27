# PRD: Sessions Marketplace
**Ahoum — Full-Stack Developer Intern Candidate Assignment**

| | |
|---|---|
| Deadline | 24 hours from assignment receipt |
| Status | Draft for build |

---

## 1. Objective

Build a compact marketplace where **Users** discover and book **Sessions**, and **Creators** create and manage the sessions they offer. The assignment is evaluated as end-to-end product engineering — architecture, correctness under concurrency, and engineering judgment — not visual polish.

**Primary success condition:** two users racing to book the last seat on a session can never both succeed.

---

## 2. Roles

| Role | Can do |
|---|---|
| **User** | Sign in via OAuth, edit own profile, browse catalog, view session detail, book a session, view own active/past bookings |
| **Creator** | Everything a User can do, **plus**: create sessions, update/delete *only their own* sessions, view booking counts on their sessions |

Role enforcement must happen **server-side**. Hiding a "Create Session" button in the UI is not a control — the backend must independently reject a User calling a Creator-only endpoint.

---

## 3. Functional Requirements

### 3.1 Authentication
- OAuth sign-in via Google **or** GitHub (one is sufficient).
- Backend verifies the OAuth token/code and is the *only* party that issues tokens.
- Backend issues an access JWT + refresh JWT to the frontend.
- User can update basic profile fields (name, bio, avatar, etc.).
- OAuth cancellation or failure must surface a clean, non-broken UI state — not a blank screen or unhandled promise rejection.

### 3.2 Sessions
- Catalog (list) + session detail page — visible to **any authenticated user, regardless of role** (User and Creator both see the same catalog; "public" here means "not restricted to owners," not "unauthenticated"). See §13 — this is a locked decision, not open.
- Creator can create / update / delete sessions **they created**.
- A Creator cannot edit or delete another Creator's session (must 403, not just fail silently in UI).
- Session fields (minimum): title, description, start time, capacity, location.
- Validation: `capacity` is a positive integer with a sensible upper bound; `starts_at` must be a valid future datetime at creation time (a session cannot be created already in the past).

### 3.3 Booking
- User can book an open session.
- User can view their own bookings split into **active** (upcoming) and **past**.
- Creator can view booking counts per session they own.
- **Capacity must never be oversold**, including under concurrent requests.
- A user cannot hold two simultaneous active bookings for the same session.
- A session cannot be booked once its start time has passed.

---

## 4. The Core Engineering Requirement: Correct Concurrent Booking

This is the section the evaluation weights most heavily (correctness/edge cases = 25%, and it's called out explicitly as "the engineering challenge").

**Scenario to defend against:** a session has 1 seat left. Two authenticated users hit "Book" within milliseconds of each other. Exactly one booking must succeed; the other must receive a clear, correct rejection (e.g. `409 Conflict` / `SESSION_FULL`), not a 500 or a silent double-confirm.

**Requirements:**
1. Capacity enforcement must live in the **backend**, not the frontend. A `remainingSeats` number shown in the UI is a read for display only — it is stale the instant it's rendered and provides zero protection against a race.
2. The mechanism must be provable, not just plausible. Acceptable approaches include (not prescriptive — candidate chooses and justifies):
   - Row-level locking (e.g. `SELECT ... FOR UPDATE` on the session row) around the "count active bookings, then insert" transaction.
   - A database constraint that makes an oversell physically impossible to commit (e.g. a trigger, or a counter column updated atomically with a `CHECK` guarding it).
3. Double-booking (same user, same session, twice) must be prevented — ideally enforced at the DB layer (e.g. a partial unique constraint on `(user, session)` where status = active), not only checked in application code, so it holds even if application logic has a bug.
4. Booking a session whose `starts_at` is in the past must be rejected.
5. **Deliverable:** one automated test, or a small standalone script, that actually creates concurrent requests (threads / async tasks / multiple processes) against a session with 1 remaining seat and asserts the final confirmed-booking count is exactly 1 — not a test that merely calls the endpoint once and asserts a 200.
6. **Deliverable:** in `DECISIONS.md`, explicitly state which invariant is protected in the database vs. in application logic, and explain concretely why a frontend-side remaining-seats check is insufficient (this is a reasoning deliverable, not just a code comment).

---

## 5. Error Handling Requirements

The following must return correct, distinguishable API errors (not generic 500s):

| Case | Expected behavior |
|---|---|
| Expired or invalid access token | Correct 401 with a clear error body |
| User calls a Creator-only endpoint | 403 |
| Creator edits another Creator's session | 403 |
| OAuth flow cancelled/fails | Frontend shows a graceful state, not a crash |
| Booking a full session | 409 (or equivalent), not 500 |
| Double-booking attempt | Clear rejection, not a duplicate row |
| Booking a started session | Clear rejection |

At least **two** of the authorization/error cases above must have automated tests.

---

## 6. Technical Requirements (fixed by the brief)

| Layer | Requirement |
|---|---|
| Frontend | React or Next.js; client-side app is sufficient (no SSR requirement) |
| Backend | Django + Django REST Framework |
| Database | PostgreSQL |
| Auth | Google or GitHub OAuth; backend issues JWTs (access + refresh) |
| Infra | Docker Compose: frontend, backend, PostgreSQL, and an Nginx/reverse-proxy container |
| Startup | Single documented command, e.g. `docker compose up --build` |
| Config | `.env.example` provided; no secrets committed |
| Persistence | DB data must survive an app-container restart; briefly explain the persistence mechanism (volume) in `README.md` |

---

## 7. Suggested Data Model (candidate may adjust and justify changes)

**User**
`id, email, name, role/is_creator flag, oauth_provider, oauth_subject, created_at`

**Session**
`id, creator_id (FK → User), title, description, starts_at, capacity, location, created_at, updated_at`

**Booking**
`id, user_id (FK → User), session_id (FK → Session), status (active/cancelled), created_at`
— constraint: unique `(user_id, session_id)` where `status = active`.

---

## 8. Suggested API Surface (candidate may adjust and justify changes)

```
POST   /api/auth/{provider}/          exchange OAuth token/code → {access, refresh, user}
POST   /api/auth/refresh/             refresh access token
GET    /api/me/                       current user profile
PATCH  /api/me/                       update profile

GET    /api/sessions/                 public catalog
GET    /api/sessions/{id}/            session detail
POST   /api/sessions/                 [Creator only] create session
PATCH  /api/sessions/{id}/            [Creator, owner only] update
DELETE /api/sessions/{id}/            [Creator, owner only] delete
GET    /api/sessions/{id}/bookings/   [Creator, owner only] booking count/list

POST   /api/bookings/                 book a session (body: session_id)
GET    /api/bookings/mine/            current user's bookings (active + past)
DELETE /api/bookings/{id}/            cancel own booking
```

---

## 9. Required Repository Artifacts

| File | Must contain |
|---|---|
| `README.md` | Setup/run instructions, architecture summary, known limitations, "what I'd improve with another day" |
| `DECISIONS.md` | ≥3 **non-trivial** decisions (ambiguity → options considered → choice → trade-off). Decisions forced by the brief don't count. |
| `DEBUGGING.md` | ≥2 real issues actually hit (symptom → diagnosis → root cause → fix → verification) |
| `PROMPT_LOG.md` | Every material AI prompt used: tool/model, prompt, what was used vs. changed/rejected, how it was verified. Plus a "what AI got wrong / what I corrected" section with ≥2 concrete examples. |
| `.env.example` | All required env vars, no real secrets |
| Commit history | Meaningful incremental commits — a single dump commit hurts the score |

---

## 10. Out of Scope (explicitly, to avoid over-building)

- Visual design polish
- Payment processing
- Email notifications
- Multi-tenant / org-level features
- Server-rendered frontend (SSR not required)
- Anything not needed to prove the concurrency/auth correctness requirements above

---

## 11. Evaluation Weighting (from the brief — use to prioritize effort)

| Area | Weight |
|---|---|
| Core functionality and architecture | 40% |
| Correctness, authorization, edge cases and tests | 25% |
| Engineering decisions and debugging | 15% |
| AI supervision and prompt log | 10% |
| Documentation, Docker and code hygiene | 10% |

**Implication for time allocation:** the booking-concurrency mechanism and its test are worth more than frontend polish. If time runs short, cut UI styling before cutting the race-condition test or the DECISIONS.md reasoning.

---

## 12. Suggested 24-Hour Time Budget

| Hours | Focus |
|---|---|
| 0–3 | Repo scaffold, Docker Compose skeleton, models, migrations |
| 3–7 | Auth (OAuth → JWT), role enforcement, session CRUD |
| 7–12 | Booking endpoint + concurrency-safe logic + concurrency test |
| 12–16 | Frontend: auth flow, catalog, detail, booking, creator dashboard |
| 16–19 | Error-case tests, edge cases (started session, double-book) |
| 19–22 | README, DECISIONS, DEBUGGING, PROMPT_LOG |
| 22–24 | Buffer, final Docker Compose smoke test, incremental commit cleanup |

---

## 13. Decisions Locked (resolved in Implementation_Plan.md §0 and below — listed here so the PRD and plan don't drift)

- **Catalog visibility:** authenticated-only, open to both roles. No anonymous/unauthenticated browsing story exists in the brief, and the whole app is OAuth-gated, so "public" is scoped to "not owner-restricted."
- "Creator" is a togglable boolean flag on `User`, not a fixed role at signup — a user can also book sessions after becoming a creator.
- OAuth provider: Google only (one is sufficient per the brief).
- Cancelled bookings immediately free the seat; the same user may re-book the same session if it hasn't started yet.
- "Past" vs. "active" bookings are computed at read time from `session.starts_at`, not a stored/cron-updated field.
- `is_creator` transitions: any authenticated user may set their own `is_creator → true` via `PATCH /api/me/`. Reverting `is_creator → false` does not strip ownership of sessions already created — it only blocks creating *new* ones going forward.
