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


def seed_match_data(session_factory):
    with session_factory() as db:
        team_a = models.Team(name="Alpha")
        team_b = models.Team(name="Bravo")
        team_c = models.Team(name="Charlie")
        db.add_all([team_a, team_b, team_c])
        db.flush()

        db.add_all(
            [
                models.Player(name="A1", set_level="Set-1", team_id=team_a.id),
                models.Player(name="A2", set_level="Set-1", team_id=team_a.id),
                models.Player(name="B1", set_level="Set-1", team_id=team_b.id),
                models.Player(name="B2", set_level="Set-1", team_id=team_b.id),
            ]
        )

        tie = models.Tie(
            tie_no=1,
            day=1,
            session="morning",
            court=1,
            team1_id=team_a.id,
            team2_id=team_b.id,
            status="pending",
        )
        db.add(tie)
        db.flush()

        tie_match = models.Match(
            stage="tie",
            status="pending",
            tie_id=tie.id,
            match_no=1,
            discipline="Set-1 Singles",
            team1_id=team_a.id,
            team2_id=team_b.id,
            team1_lineup="A1",
            team2_lineup="B1",
            day=1,
            session="morning",
            court=1,
            time="09:00",
        )

        db.add(tie_match)
        db.commit()

        return tie_match.id


def seed_completed_league_for_tiebreak(session_factory):
    with session_factory() as db:
        alpha = models.Team(name="Alpha")
        bravo = models.Team(name="Bravo")
        charlie = models.Team(name="Charlie")
        delta = models.Team(name="Delta")
        echo = models.Team(name="Echo")
        teams = {
            "Alpha": alpha,
            "Bravo": bravo,
            "Charlie": charlie,
            "Delta": delta,
            "Echo": echo,
        }
        db.add_all(list(teams.values()))
        db.flush()

        def add_tie(
            tie_no: int,
            team1: models.Team,
            team2: models.Team,
            winner: models.Team,
            match_scores: list[tuple[int, int]],
        ) -> None:
            tie = models.Tie(
                tie_no=tie_no,
                day=1 if tie_no <= 5 else 2,
                session="morning" if tie_no % 2 else "after lunch",
                court=2 if tie_no % 2 else 4,
                team1_id=team1.id,
                team2_id=team2.id,
                status="completed",
                winner_team_id=winner.id,
            )
            db.add(tie)
            db.flush()

            team1_games = 0
            team2_games = 0
            for match_no, (score1, score2) in enumerate(match_scores, start=1):
                winner_side = 1 if score1 > score2 else 2
                if winner_side == 1:
                    team1_games += 1
                else:
                    team2_games += 1

                db.add(
                    models.Match(
                        stage="tie",
                        status="completed",
                        tie_id=tie.id,
                        match_no=match_no,
                        discipline=f"Set-{match_no} Singles",
                        team1_id=team1.id,
                        team2_id=team2.id,
                        team1_lineup=f"{team1.name} P1",
                        team2_lineup=f"{team2.name} P1",
                        lineup_confirmed=True,
                        day=tie.day,
                        session=tie.session,
                        court=tie.court,
                        time="09:00",
                        team1_score=score1,
                        team2_score=score2,
                        winner_side=winner_side,
                    )
                )

            tie.score1 = team1_games
            tie.score2 = team2_games

        # 5 teams => 10 ties. Top-3 all finish with 3 tie wins.
        # Tiebreak should use games won, then average lead per game.
        add_tie(1, teams["Alpha"], teams["Bravo"], teams["Alpha"], [(21, 19), (19, 21), (21, 19)])
        add_tie(2, teams["Alpha"], teams["Charlie"], teams["Charlie"], [(19, 21), (21, 5), (19, 21)])
        add_tie(3, teams["Alpha"], teams["Delta"], teams["Alpha"], [(21, 10), (21, 11), (21, 9)])
        add_tie(4, teams["Alpha"], teams["Echo"], teams["Alpha"], [(21, 17), (18, 21), (21, 19)])
        add_tie(5, teams["Bravo"], teams["Charlie"], teams["Bravo"], [(21, 11), (21, 13), (20, 22)])
        add_tie(6, teams["Bravo"], teams["Delta"], teams["Bravo"], [(21, 12), (19, 21), (21, 14)])
        add_tie(7, teams["Bravo"], teams["Echo"], teams["Bravo"], [(21, 10), (18, 21), (21, 13)])
        add_tie(8, teams["Charlie"], teams["Delta"], teams["Charlie"], [(21, 19), (18, 21), (21, 19)])
        add_tie(9, teams["Charlie"], teams["Echo"], teams["Charlie"], [(21, 18), (17, 21), (21, 19)])
        add_tie(10, teams["Delta"], teams["Echo"], teams["Delta"], [(21, 19), (18, 21), (21, 19)])

        db.commit()


def test_healthcheck(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}



def test_score_update_requires_referee_assignment(client, session_factory):
    tie_match_id = seed_match_data(session_factory)

    blocked = client.post(
        f"/matches/score/{tie_match_id}",
        json={"score1": 21, "score2": 19},
    )
    assert blocked.status_code == 400
    assert "Assign referee" in blocked.json()["detail"]

    assigned = client.post(f"/referee/assign?match_id={tie_match_id}&name=Main Umpire")
    assert assigned.status_code == 200

    updated = client.post(
        f"/matches/score/{tie_match_id}",
        json={"score1": 21, "score2": 19},
    )
    assert updated.status_code == 200
    payload = updated.json()

    assert payload["status"] == "completed"
    assert payload["winner_side"] == 1

    ties_response = client.get("/ties/")
    assert ties_response.status_code == 200
    tie = ties_response.json()[0]
    assert tie["score1"] == 1
    assert tie["score2"] == 0



def test_viewer_dashboard_returns_ties_only(client, session_factory):
    tie_match_id = seed_match_data(session_factory)

    client.post(f"/referee/assign?match_id={tie_match_id}&name=Main Umpire")
    client.post(f"/matches/score/{tie_match_id}", json={"score1": 21, "score2": 17})

    dashboard = client.get("/viewer/dashboard")
    assert dashboard.status_code == 200
    data = dashboard.json()

    assert "ties" in data
    assert data["ties"][0]["matches"][0]["stage"] == "tie"
    assert "finals" not in data
    assert data["summary"]["completed_games"] >= 1


def test_viewer_standings_finalists_and_bronze_tiebreak(client, session_factory):
    seed_completed_league_for_tiebreak(session_factory)

    standings_response = client.get("/viewer/standings")
    assert standings_response.status_code == 200
    rows = standings_response.json()

    assert len(rows) == 5
    assert [rows[0]["team"], rows[1]["team"], rows[2]["team"]] == ["Alpha", "Bravo", "Charlie"]

    assert rows[0]["qualification"] == "finalist"
    assert rows[1]["qualification"] == "finalist"
    assert rows[2]["qualification"] == "bronze"

    # Bravo and Charlie are tied on tie wins and games won,
    # so average lead per game decides finalist #2.
    assert rows[1]["ties_won"] == rows[2]["ties_won"] == 3
    assert rows[1]["games_won"] == rows[2]["games_won"] == 7
    assert rows[1]["average_match_lead"] > rows[2]["average_match_lead"]


def test_final_tie_creation_and_medals(client, session_factory):
    seed_completed_league_for_tiebreak(session_factory)

    dashboard = client.get("/viewer/dashboard")
    assert dashboard.status_code == 200
    payload = dashboard.json()

    assert payload["summary"]["completed_ties"] == payload["summary"]["total_ties"] == 10
    assert payload["final_match"] is not None
    assert payload["medals"]["finalist1"] is not None
    assert payload["medals"]["finalist2"] is not None
    assert payload["medals"]["bronze_team"] is not None
    assert payload["medals"]["gold_team"] is None
    assert payload["medals"]["silver_team"] is None

    final_match = payload["final_match"]
    assert len(final_match["matches"]) == 12

    # Complete all 12 final games so medals can lock (team1 wins 7-5).
    for game in final_match["matches"]:
        assigned = client.post(f"/finals/games/{game['id']}/assign?name=Chief Umpire")
        assert assigned.status_code == 200

    for index, game in enumerate(final_match["matches"], start=1):
        team1_wins = index <= 7
        score1, score2 = (21, 18) if team1_wins else (18, 21)
        scored = client.post(f"/finals/games/{game['id']}/score", json={"score1": score1, "score2": score2})
        assert scored.status_code == 200

    final_payload = client.get("/finals/").json()
    assert final_payload is not None
    assert final_payload["status"] == "completed"
    assert final_payload["winner_team"] is not None
    assert final_payload["team1_score"] == 7
    assert final_payload["team2_score"] == 5

    refreshed = client.get("/viewer/dashboard")
    assert refreshed.status_code == 200
    refreshed_payload = refreshed.json()
    assert refreshed_payload["medals"]["gold_team"] == final_payload["winner_team"]
    assert refreshed_payload["medals"]["silver_team"] is not None


def test_final_games_counted_only_after_all_ties_completed(client, session_factory):
    seed_completed_league_for_tiebreak(session_factory)

    complete_dashboard = client.get("/viewer/dashboard")
    assert complete_dashboard.status_code == 200
    complete_payload = complete_dashboard.json()

    league_games = sum(len(tie["matches"]) for tie in complete_payload["ties"])
    assert league_games > 0
    assert complete_payload["summary"]["completed_ties"] == complete_payload["summary"]["total_ties"] == 10
    assert complete_payload["final_match"] is not None
    assert len(complete_payload["final_match"]["matches"]) == 12
    assert complete_payload["summary"]["total_games"] == league_games + 12

    with session_factory() as db:
        tie = db.query(models.Tie).filter(models.Tie.tie_no == 1).first()
        assert tie is not None
        tie.status = "pending"
        tie.winner_team_id = None
        db.commit()

    incomplete_dashboard = client.get("/viewer/dashboard")
    assert incomplete_dashboard.status_code == 200
    incomplete_payload = incomplete_dashboard.json()

    assert incomplete_payload["summary"]["completed_ties"] == 9
    assert incomplete_payload["summary"]["total_ties"] == 10
    assert incomplete_payload["final_match"] is None
    assert incomplete_payload["summary"]["total_games"] == league_games


def test_post_finals_category_summary_endpoint(client, session_factory):
    seed_completed_league_for_tiebreak(session_factory)

    response = client.get("/viewer/post-finals")
    assert response.status_code == 200
    payload = response.json()

    assert "categories" in payload
    assert len(payload["categories"]) == 9
    assert payload["total_matches_considered"] >= 30
    assert payload["medals"]["bronze_team"] is not None

    categories = {item["category"] for item in payload["categories"]}
    assert "Men Advance" in categories
    assert "Women Intermediate" in categories


def test_post_finals_mixed_pair_counts_by_individual_set_level(client, session_factory):
    with session_factory() as db:
        team_a = models.Team(name="Alpha")
        team_b = models.Team(name="Bravo")
        db.add_all([team_a, team_b])
        db.flush()

        db.add_all(
            [
                models.Player(name="A Set1", set_level="Set-1", team_id=team_a.id),
                models.Player(name="A Set2", set_level="Set-2", team_id=team_a.id),
                models.Player(name="B Set1", set_level="Set-1", team_id=team_b.id),
                models.Player(name="B Set2", set_level="Set-2", team_id=team_b.id),
            ]
        )

        tie = models.Tie(
            tie_no=1,
            day=1,
            session="morning",
            court=1,
            team1_id=team_a.id,
            team2_id=team_b.id,
            score1=1,
            score2=0,
            status="completed",
            winner_team_id=team_a.id,
        )
        db.add(tie)
        db.flush()

        db.add(
            models.Match(
                stage="tie",
                status="completed",
                tie_id=tie.id,
                match_no=1,
                discipline="Set 1 OR 2 / Set 1 OR 2",
                team1_id=team_a.id,
                team2_id=team_b.id,
                team1_lineup="A Set1 / A Set2",
                team2_lineup="B Set1 / B Set2",
                lineup_confirmed=True,
                day=1,
                session="morning",
                court=1,
                time="09:00",
                team1_score=21,
                team2_score=14,
                winner_side=1,
            )
        )
        db.commit()

    response = client.get("/viewer/post-finals")
    assert response.status_code == 200
    payload = response.json()

    category_rows = {item["category"]: item for item in payload["categories"]}
    set1_rows = {item["player_name"]: item["wins"] for item in category_rows["Men Set-1"]["rankings"]}
    set2_rows = {item["player_name"]: item["wins"] for item in category_rows["Men Set-2"]["rankings"]}

    assert set1_rows.get("A Set1") == 1
    assert set2_rows.get("A Set2") == 1


def test_post_finals_or_token_uses_lineup_order_for_set_split(client, session_factory):
    with session_factory() as db:
        team_a = models.Team(name="Alpha")
        team_b = models.Team(name="Bravo")
        db.add_all([team_a, team_b])
        db.flush()

        # Intentionally set both winners to Set-1 in player master.
        # OR-token mapping should still count 2nd lineup name as Set-2.
        db.add_all(
            [
                models.Player(name="Suman", set_level="Set-1", team_id=team_a.id),
                models.Player(name="Arjun", set_level="Set-1", team_id=team_a.id),
                models.Player(name="B One", set_level="Set-1", team_id=team_b.id),
                models.Player(name="B Two", set_level="Set-1", team_id=team_b.id),
            ]
        )

        tie = models.Tie(
            tie_no=1,
            day=1,
            session="morning",
            court=1,
            team1_id=team_a.id,
            team2_id=team_b.id,
            score1=1,
            score2=0,
            status="completed",
            winner_team_id=team_a.id,
        )
        db.add(tie)
        db.flush()

        db.add(
            models.Match(
                stage="tie",
                status="completed",
                tie_id=tie.id,
                match_no=1,
                discipline="Set 1 OR 2 / Set 1 OR 2",
                team1_id=team_a.id,
                team2_id=team_b.id,
                team1_lineup="Suman / Arjun",
                team2_lineup="B One / B Two",
                lineup_confirmed=True,
                day=1,
                session="morning",
                court=1,
                time="09:00",
                team1_score=21,
                team2_score=18,
                winner_side=1,
            )
        )
        db.commit()

    response = client.get("/viewer/post-finals")
    assert response.status_code == 200
    payload = response.json()
    category_rows = {item["category"]: item for item in payload["categories"]}
    set1_rows = {item["player_name"]: item["wins"] for item in category_rows["Men Set-1"]["rankings"]}
    set2_rows = {item["player_name"]: item["wins"] for item in category_rows["Men Set-2"]["rankings"]}

    assert set1_rows.get("Suman") == 1
    assert set2_rows.get("Arjun") == 1


def test_post_finals_category_tiebreak_uses_opponent_score_then_lead(client, session_factory):
    with session_factory() as db:
        team_a = models.Team(name="Alpha")
        team_b = models.Team(name="Bravo")
        db.add_all([team_a, team_b])
        db.flush()

        db.add_all(
            [
                models.Player(name="A Set1", set_level="Set-1", team_id=team_a.id),
                models.Player(name="B Set1", set_level="Set-1", team_id=team_b.id),
            ]
        )

        tie = models.Tie(
            tie_no=1,
            day=1,
            session="morning",
            court=1,
            team1_id=team_a.id,
            team2_id=team_b.id,
            score1=1,
            score2=1,
            status="live",
            winner_team_id=None,
        )
        db.add(tie)
        db.flush()

        db.add_all(
            [
                models.Match(
                    stage="tie",
                    status="completed",
                    tie_id=tie.id,
                    match_no=1,
                    discipline="Set-1 / Set-1",
                    team1_id=team_a.id,
                    team2_id=team_b.id,
                    team1_lineup="A Set1",
                    team2_lineup="B Set1",
                    lineup_confirmed=True,
                    day=1,
                    session="morning",
                    court=1,
                    time="09:00",
                    team1_score=21,
                    team2_score=18,
                    winner_side=1,
                ),
                models.Match(
                    stage="tie",
                    status="completed",
                    tie_id=tie.id,
                    match_no=2,
                    discipline="Set-1 / Set-1",
                    team1_id=team_a.id,
                    team2_id=team_b.id,
                    team1_lineup="A Set1",
                    team2_lineup="B Set1",
                    lineup_confirmed=True,
                    day=1,
                    session="morning",
                    court=1,
                    time="09:30",
                    team1_score=23,
                    team2_score=25,
                    winner_side=2,
                ),
            ]
        )
        db.commit()

    response = client.get("/viewer/post-finals")
    assert response.status_code == 200
    payload = response.json()

    category_rows = {item["category"]: item for item in payload["categories"]}
    men_set1 = category_rows["Men Set-1"]
    assert men_set1["winner_names"] == ["A Set1"]
    assert men_set1["winner_wins"] == 1
    assert men_set1["winner_opponent_score"] == 18
    assert men_set1["winner_lead_score"] == 3
