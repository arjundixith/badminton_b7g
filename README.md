# Badminton App

A full-stack badminton tournament manager with a FastAPI backend and a React (Vite) frontend.

## Stack

- Backend: FastAPI + SQLAlchemy + SQLite
- Frontend: React + Vite
- Tests: pytest + FastAPI TestClient

## Project Structure

- `/backend` API service, domain models, seed script, and tests
- `/frontend` React application and API client

## Backend Setup

```bash
cd /Users/arjundixithts/Downloads/badminton-app/backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
python seed.py
uvicorn app.main:app --reload
```

Backend URL: `http://localhost:8000`

Useful endpoints:

- `GET /health`
- `GET /teams/`
- `GET /matches/`
- `POST /matches/score/{match_id}`
- `GET /schedule/`

## Frontend Setup

```bash
cd /Users/arjundixithts/Downloads/badminton-app/frontend
npm install
cp .env.example .env
npm run dev
```

Frontend URL: `http://localhost:5173`

Set `VITE_API_URL` in `.env` when your backend is not on `http://localhost:8000`.

## Quality Commands

```bash
cd /Users/arjundixithts/Downloads/badminton-app/backend
pytest

cd /Users/arjundixithts/Downloads/badminton-app/frontend
npm run build
```
