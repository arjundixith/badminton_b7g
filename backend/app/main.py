import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import Base, SessionLocal, engine
from .models import Team
from .routes import finals, matches, players, referee, schedule, teams, ties, viewer

app = FastAPI(
    title="Badminton Tournament API",
    version="2.0.0",
    description=(
        "Round-robin badminton tournament APIs with referee-scored matches "
        "and viewer dashboards."
    ),
)

cors_origins = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173",
)
allow_origins = [origin.strip() for origin in cors_origins.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)


def should_auto_seed() -> bool:
    value = os.getenv("AUTO_SEED_ON_EMPTY", "true").strip().lower()
    return value in {"1", "true", "yes", "on"}


def seed_if_empty() -> None:
    if not should_auto_seed():
        return

    db = SessionLocal()
    try:
        has_teams = db.query(Team.id).first() is not None
    finally:
        db.close()

    if has_teams:
        return

    from seed import seed

    seed(demo_progress=False)


seed_if_empty()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(teams.router, prefix="/teams")
app.include_router(players.router, prefix="/players")
app.include_router(ties.router, prefix="/ties")
app.include_router(matches.router, prefix="/matches")
app.include_router(referee.router, prefix="/referee")
app.include_router(schedule.router, prefix="/schedule")
app.include_router(viewer.router, prefix="/viewer")
app.include_router(finals.router, prefix="/finals")
