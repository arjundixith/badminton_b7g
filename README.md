# Badminton App

A full-stack badminton tournament app for two user roles:

- **Referee Console**: assign referee per match and update score.
- **Viewer Console**: track round-robin ties, standings, and pending/live/completed matches.

## Tournament Logic Implemented

- Round-robin ties (league stage)
- Referee must be assigned before score update
- Badminton scoring: up to 21 with deuce, capped at 30

## Project Structure

- `/Users/arjundixithts/Downloads/badminton-app/backend`: FastAPI service, SQLAlchemy models, seed data, tests
- `/Users/arjundixithts/Downloads/badminton-app/frontend`: React + Vite web app

## Full Project Walkthrough

For a complete step-by-step explanation of architecture, data flow, rules, APIs, frontend behavior, finals logic, and deployment, read:

- `/Users/arjundixithts/Downloads/badminton-app/docs/PROJECT_STEP_BY_STEP.md`

## Backend Setup (Local Postgres Required)

```bash
cd /Users/arjundixithts/Downloads/badminton-app
docker compose up -d postgres

cd /Users/arjundixithts/Downloads/badminton-app/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
python3 seed.py
uvicorn app.main:app --reload
```

Backend URL: `http://localhost:8000`
Swagger docs: `http://localhost:8000/docs`

Local backend requires PostgreSQL. Set `DATABASE_URL` explicitly:

- Homebrew/Postgres local user: `postgresql://<your-macos-username>@localhost:5432/badminton_b7g`
- Docker compose postgres user: `postgresql://postgres:postgres@localhost:5432/badminton_b7g`

Reference env template:

- `/Users/arjundixithts/Downloads/badminton-app/backend/.env.example`

## pgAdmin (Recommended Local DB UI)

Install:

```bash
brew install --cask pgadmin4
```

Connection values for Homebrew Postgres:

- Server Name: `Badminton Local PG` (any label)
- Host: `localhost`
- Port: `5432`
- Maintenance DB: `postgres`
- Username: your macOS user (example: `arjundixithts`)
- Password: as configured in your local Postgres role

Connection values for Docker Postgres:

- Username: `postgres`
- Password: `postgres`

Key APIs:

- `GET /health`
- `GET /viewer/dashboard`
- `GET /viewer/standings`
- `GET /ties/`
- `GET /matches/?stage=tie&status=pending|live|completed`
- `POST /referee/assign?match_id=<id>&name=<referee>`
- `POST /matches/score/{match_id}`

## Frontend Setup

```bash
cd /Users/arjundixithts/Downloads/badminton-app/frontend
npm install
cp .env.example .env
npm run dev
```

Frontend URL: `http://localhost:5173`

Set backend URL in `/Users/arjundixithts/Downloads/badminton-app/frontend/.env`:

```bash
VITE_API_URL=http://localhost:8000
```

## Seed Data

`python3 seed.py` resets the DB and seeds:

- 5 teams
- full player rosters (Set-1 to Set-5)
- round-robin tie fixtures and tie matches
- all ties in fresh/pending state

For demo live/completed sample state, use:

```bash
python3 seed.py --demo-progress
```

## Free Deployment (Recommended)

Use:

- Frontend: Vercel (free)
- Backend: Render web service (free)
- Database: Neon Postgres (free tier)

### 1. Deploy backend to Render

1. Push this repo to GitHub.
2. In Render, create a new **Blueprint** and select your repo.
3. Render uses `/Users/arjundixithts/Downloads/badminton-app/render.yaml` automatically.
4. Set backend environment variables in Render:
   - `DATABASE_URL` = your Neon connection string (`postgresql://...`)
   - `CORS_ORIGINS` = your Vercel frontend URL (for example `https://your-app.vercel.app`)
   - `AUTO_SEED_ON_EMPTY=true` (already defaulted in `render.yaml`)
   - optional: `AUTO_SEED_FORCE_RESET=true` (force reset to fresh tournament on every startup; keep `false` for normal use)

Notes:

- On first boot, if DB is empty, backend auto-seeds a **fresh tournament start** (same team names and player names, all ties fresh/pending).
- `DATABASE_URL` must be set in cloud environments.

### 2. Deploy frontend to Vercel

1. Import the same repo in Vercel.
2. Vercel will use `/Users/arjundixithts/Downloads/badminton-app/vercel.json`.
3. Add environment variable in Vercel:
   - `VITE_API_URL=https://<your-render-service>.onrender.com`
4. Redeploy frontend.

### 3. Verify

1. Open frontend URL.
2. Check `/viewer`, `/referee_b7g/viewer`, and `/referee_b7g/referee`.
3. Confirm backend health at `https://<your-render-service>.onrender.com/health`.

## Single Deployment On Vercel (Free)

You can deploy frontend + backend in one Vercel project:

- Frontend static build from `frontend/`
- FastAPI backend from `/api/index.py`

Steps:

1. In Vercel, import this repo as one project.
2. Keep build settings from `/Users/arjundixithts/Downloads/badminton-app/vercel.json`.
3. Add environment variables in Vercel project:
   - `DATABASE_URL=postgresql://...` (Neon free DB URL)
   - `AUTO_SEED_ON_EMPTY=true`
   - `AUTO_SEED_FORCE_RESET=false`
   - `CORS_ORIGINS=https://<your-vercel-domain>`
   - `VITE_API_URL=/api`
4. Deploy.

URLs after deploy:

- Frontend: `https://<your-vercel-domain>/`
- Backend health: `https://<your-vercel-domain>/api/health`

Notes:

- Use Postgres (`DATABASE_URL`) for persistence.
- On first start with empty DB, app auto-seeds a fresh tournament (same teams/players, all ties pending).
- `AUTO_SEED_FORCE_RESET=true` can be used for a one-time full reset to your default tournament data, then set it back to `false`.

## Quality Commands

```bash
cd /Users/arjundixithts/Downloads/badminton-app/backend
python3 -m compileall app tests

cd /Users/arjundixithts/Downloads/badminton-app/frontend
npm run build
```
