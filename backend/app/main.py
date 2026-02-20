import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import Base, engine
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
