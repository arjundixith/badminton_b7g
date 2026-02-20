import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models
from app.database import Base, get_db
from app.main import app


@pytest.fixture()
def session_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    Base.metadata.create_all(bind=engine)
    return session_factory


@pytest.fixture()
def client(session_factory):
    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def seed_one_match(session_factory):
    with session_factory() as db:
        team1 = models.Team(name="Alpha")
        team2 = models.Team(name="Bravo")
        db.add_all([team1, team2])
        db.flush()

        tie = models.Tie(team1_id=team1.id, team2_id=team2.id)
        db.add(tie)
        db.flush()

        match = models.Match(
            tie_id=tie.id,
            match_no=1,
            day=1,
            session="morning",
            court=1,
            time="09:00",
        )
        db.add(match)
        db.commit()

        return match.id


def test_healthcheck(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}



def test_create_and_list_teams(client):
    created = client.post("/teams/", json={"name": "Spartans"})
    assert created.status_code == 201
    assert created.json()["name"] == "Spartans"

    duplicate = client.post("/teams/", json={"name": "spartans"})
    assert duplicate.status_code == 409

    listed = client.get("/teams/")
    assert listed.status_code == 200
    assert len(listed.json()) == 1



def test_score_update_recalculates_tie_and_schedule(client, session_factory):
    match_id = seed_one_match(session_factory)

    score_response = client.post(
        f"/matches/score/{match_id}",
        json={"score1": 21, "score2": 18},
    )

    assert score_response.status_code == 200
    payload = score_response.json()
    assert payload["winner_side"] == 1
    assert payload["team1_score"] == 21
    assert payload["team2_score"] == 18

    ties_response = client.get("/ties/")
    assert ties_response.status_code == 200
    ties = ties_response.json()
    assert ties[0]["score1"] == 1
    assert ties[0]["score2"] == 0

    schedule_response = client.get("/schedule/")
    assert schedule_response.status_code == 200
    schedule = schedule_response.json()
    assert schedule["1"]["morning"][0]["score1"] == 21
    assert schedule["1"]["morning"][0]["score2"] == 18
