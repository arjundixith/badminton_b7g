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

## Backend Setup

```bash
cd /Users/arjundixithts/Downloads/badminton-app/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
python3 seed.py
uvicorn app.main:app --reload
```

Backend URL: `http://localhost:8000`
Swagger docs: `http://localhost:8000/docs`

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
- Database: Neon Postgres (free tier) or fallback SQLite

### 1. Deploy backend to Render

1. Push this repo to GitHub.
2. In Render, create a new **Blueprint** and select your repo.
3. Render uses `/Users/arjundixithts/Downloads/badminton-app/render.yaml` automatically.
4. Set backend environment variables in Render:
   - `DATABASE_URL` = your Neon connection string (`postgresql://...`)
   - `CORS_ORIGINS` = your Vercel frontend URL (for example `https://your-app.vercel.app`)
   - `AUTO_SEED_ON_EMPTY=true` (already defaulted in `render.yaml`)

Notes:

- On first boot, if DB is empty, backend auto-seeds a **fresh tournament start** (same team names and player names, all ties fresh/pending).
- If `DATABASE_URL` is not set, backend falls back to SQLite (not persistent on free cloud restarts).

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

## Quality Commands

```bash
cd /Users/arjundixithts/Downloads/badminton-app/backend
python3 -m compileall app tests

cd /Users/arjundixithts/Downloads/badminton-app/frontend
npm run build
```
