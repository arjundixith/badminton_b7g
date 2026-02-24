# B7G Badminton App - Complete Project Walkthrough (Step by Step)

This document explains the entire project end-to-end so you can understand and maintain it without relying on Codex.

## 1. What This Project Does

This is a full-stack tournament management app for a badminton league with:

- `Referee Console`: manage match flow, assign referees, confirm lineups, update scores.
- `Viewer Console`: show live status, standings, team-wise tie breakdown, finals, medals.
- `Post Finals`: category-wise individual winners across all completed matches.

Core tournament flow:

1. Round-robin league stage (`10` ties total).
2. Each tie has `12` regular matches + optional `13th` decider.
3. Top `2` teams after league become finalists.
4. Rank `3` gets bronze automatically.
5. Final tie has `12` games to decide gold/silver.

## 2. Tech Stack

- Frontend: React + Vite
- Backend: FastAPI + SQLAlchemy
- Database: Postgres (local + cloud). SQLite is used only in backend tests.
- Deployment: single-project Vercel setup (frontend + backend API under `/api`)

## 3. Repository Structure

- `backend/app/main.py`: FastAPI app startup, CORS, auto-seed, router wiring
- `backend/app/models.py`: DB schema
- `backend/app/crud.py`: core tournament business rules
- `backend/app/routes/*.py`: API route handlers
- `backend/app/serializers.py`: model -> API response mapping
- `backend/seed.py`: master default tournament data
- `frontend/src/App.jsx`: routing + tabs
- `frontend/src/pages/Referee.jsx`: referee workflow UI
- `frontend/src/pages/Viewer.jsx`: viewer dashboard UI
- `frontend/src/pages/Home.jsx`: summary home
- `frontend/src/pages/PostFinals.jsx`: category winners page
- `frontend/src/api.js`: frontend API client
- `api/index.py`: Vercel Python serverless entrypoint
- `vercel.json`: frontend build + `/api` rewrite behavior

## 4. Database Model (How Data Is Stored)

Defined in `backend/app/models.py`.

- `teams`: team master
- `players`: player master with `set_level` (`Set-1` to `Set-5`)
- `ties`: one row per league tie (tie number, teams, current tie score, status, winner)
- `matches`: all league tie matches (`stage="tie"`)
- `referees`: reusable referee names
- `final_matches`: one final tie row after league completion
- `final_games`: 12 games inside the final tie

Important constraints:

- Score is non-negative.
- Match status is `pending | live | completed`.
- Tie teams must be different.
- Final game numbers are 1..12.

## 5. Default Tournament Data (Your Given Data)

Defined in `backend/seed.py`.

Contains:

- the exact 5 teams
- player rosters by set level
- fixed round-robin fixture list (10 ties)
- fixed lineups for all match numbers per team
- discipline templates (`match_no 1..13`)

`match_no 13` is the decider game:

- singles advance player
- only valid when tie is `6-6`

## 6. Startup and Auto-Seeding Behavior

Defined in `backend/app/main.py`.

On startup:

1. DB tables are created (`Base.metadata.create_all`).
2. If auto-seed is enabled and DB is empty, seed fresh tournament data.
3. If force-reset is enabled, DB resets and reseeds immediately.

Environment controls:

- `AUTO_SEED_ON_EMPTY=true|false`
- `AUTO_SEED_FORCE_RESET=true|false`

Recommended:

- keep `AUTO_SEED_ON_EMPTY=true`
- keep `AUTO_SEED_FORCE_RESET=false` (turn on only for one-time reset)

## 7. Core Match Rules (Backend)

Implemented in `backend/app/crud.py`.

### 7.1 Scoring rules

- up to 21, win by 2
- deuce allowed (20-20 onward)
- hard cap at 30
- cannot exceed 21 unless both sides reached 20

### 7.2 Before scoring is allowed

- referee must be assigned
- lineup must be confirmed
- for certain doubles disciplines, exactly two players per side are required

### 7.3 Decider match #13 rules

- hidden from views while pending unless tie is `6-6`
- cannot start or assign referee unless unlocked at `6-6`
- visible after completion in valid decider-result state (7-6 / 6-7 tie result)

### 7.4 Tie completion logic

A tie is completed only when:

- all 12 regular matches are completed, and
- if score is 6-6, decider also completed

Until then, tie remains `pending` or `live`.

## 8. Standings and Tie-Break Rules

`build_standings()` in `backend/app/crud.py` ranks teams by:

1. ties won
2. games won
3. average match lead (`(points_for - points_against) / games_played`)
4. point difference
5. game difference
6. team name

Qualification assigned only when league is fully complete:

- rank 1,2 -> `finalist`
- rank 3 -> `bronze`

## 9. Finals Logic

When all 10 ties are complete:

1. final match is auto-created with top 2 teams.
2. 12 final games are ensured from discipline templates.
3. final games are scored like normal badminton.
4. final winner is by game count.
5. if final games tie (rare), tie-break uses total points, then last completed game winner.

Medals:

- `gold_team`: final winner
- `silver_team`: other finalist
- `bronze_team`: league rank 3

## 10. Post-Finals Category Winners

`build_post_finals_category_summary()` computes winners for:

- Men Advance
- Men Set-1..Set-5
- Women Advance
- Women Intermediate
- Women Beginner

Data sources:

- all completed league matches
- all completed final games

For each category, ranking order is:

1. more wins
2. lower opponent score
3. higher lead score (`for - against`)
4. higher total score
5. player name

This reflects your requested tie-break preference (opponent score and lead).

## 11. API Endpoints You Use Most

Main viewer/referee APIs:

- `GET /health`
- `GET /viewer/dashboard`
- `GET /viewer/standings`
- `GET /viewer/post-finals`
- `GET /ties/`
- `GET /matches/?status=pending|live|completed&tie_id=...`
- `POST /referee/assign?match_id=<id>&name=<referee>`
- `PATCH /matches/{match_id}/lineup`
- `PATCH /matches/{match_id}/status`
- `POST /matches/score/{match_id}`

Finals APIs:

- `GET /finals/`
- `POST /finals/games/{game_id}/assign?name=...`
- `POST /finals/games/{game_id}/score`

## 12. Frontend Architecture and Page Behavior

### 12.1 Routing

`frontend/src/App.jsx` supports two route modes:

- normal: `/`, `/viewer`, `/referee`, `/post-finals`
- prefixed: `/referee_b7g/...`

When URL starts with `/referee_b7g`, tabs switch to that mode.

### 12.2 Polling/Live updates

- Home: refresh every 4s
- Viewer: refresh every 1.5s + on tab focus/visibility
- Referee: refresh every 4s
- Post Finals: refresh every 2.5s

This keeps viewer and referee in near real-time without manual refresh.

### 12.3 Referee flow

Typical flow on one match:

1. pick pending/live/completed tab and court
2. expand tie accordion
3. update lineup if required
4. assign referee and start match
5. increment/decrement score
6. save score -> backend recalculates winner and tie state
7. completed match appears under completed tab

## 13. Request Flow (End-to-End Example)

When referee clicks `Save Score`:

1. `frontend/src/pages/Referee.jsx` calls `updateScore(...)` in `frontend/src/api.js`
2. API hits `POST /matches/score/{id}`
3. route `backend/app/routes/matches.py` calls `crud.update_score(...)`
4. score is validated, winner computed, match status updated
5. tie scores/status recalculated in `_recalculate_tie(...)`
6. viewer polling fetches updated dashboard and renders new live/completed state

## 14. Local vs Production Differences

Code is the same, but config differs.

Local:

- `VITE_API_URL=http://localhost:8000`
- `DATABASE_URL=postgresql://postgres:postgres@localhost:5432/badminton_b7g`

Production (Vercel single project):

- `VITE_API_URL=/api`
- API served by `api/index.py`
- rewrite in `vercel.json`: `/api/(.*)` -> `/api?__path=/$1`
- use Postgres (`DATABASE_URL`) for persistence

## 15. Environment Variables

Backend:

- `DATABASE_URL`
- `CORS_ORIGINS`
- `AUTO_SEED_ON_EMPTY`
- `AUTO_SEED_FORCE_RESET`

Frontend:

- `VITE_API_URL`

## 16. Local Run Commands

Backend:

```bash
docker compose up -d postgres

cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
python3 seed.py
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
cp .env.example .env
# set VITE_API_URL=http://localhost:8000
npm run dev
```

## 17. Validation and Tests

Current tests are in `backend/tests/test_api.py` and cover:

- health check
- score update requiring referee assignment
- viewer dashboard basics
- standings tie-break and finalist/bronze assignment
- final creation and medal lock
- total games including/excluding finals based on league completion
- post-finals category summary and category tie-break behavior

## 18. Fast Troubleshooting

If viewer shows JSON parse error with `<!DOCTYPE`:

- frontend is hitting HTML, not API.
- check `VITE_API_URL` and Vercel rewrites.

If `/api/viewer/dashboard` is 404 in Vercel:

- ensure latest `vercel.json` and `api/index.py` are deployed.
- ensure project root is repo root (not `frontend` subdir).

If data reset happened unexpectedly:

- check `AUTO_SEED_FORCE_RESET` is not `true`.

---

If you want, next I can also generate a second document focused only on:

- `Referee user manual` (button-by-button)
- `Admin operations` (reset, reseed, deploy, backup)
