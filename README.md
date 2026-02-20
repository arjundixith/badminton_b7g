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
- mixed match states (`pending`, `live`, `completed`) for viewer demos

## Quality Commands

```bash
cd /Users/arjundixithts/Downloads/badminton-app/backend
python3 -m compileall app tests

cd /Users/arjundixithts/Downloads/badminton-app/frontend
npm run build
```
