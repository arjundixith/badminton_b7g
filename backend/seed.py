from app import models
from app.database import Base, SessionLocal, engine


def reset_database() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def seed() -> None:
    reset_database()

    db = SessionLocal()
    try:
        team_names = [
            "Golden Monks",
            "Spartans",
            "Feather Fighters",
            "Lightning Racquets",
            "Smash Hawks",
        ]

        teams = {}
        for team_name in team_names:
            team = models.Team(name=team_name)
            db.add(team)
            db.flush()
            teams[team_name] = team

        tie1 = models.Tie(
            team1_id=teams["Golden Monks"].id,
            team2_id=teams["Spartans"].id,
        )
        tie2 = models.Tie(
            team1_id=teams["Feather Fighters"].id,
            team2_id=teams["Smash Hawks"].id,
        )
        db.add_all([tie1, tie2])
        db.flush()

        db.add_all(
            [
                models.Match(
                    tie_id=tie1.id,
                    match_no=1,
                    day=1,
                    session="morning",
                    court=2,
                    time="09:30",
                ),
                models.Match(
                    tie_id=tie1.id,
                    match_no=2,
                    day=1,
                    session="morning",
                    court=2,
                    time="09:50",
                ),
                models.Match(
                    tie_id=tie1.id,
                    match_no=3,
                    day=1,
                    session="morning",
                    court=2,
                    time="10:10",
                ),
                models.Match(
                    tie_id=tie2.id,
                    match_no=1,
                    day=1,
                    session="evening",
                    court=1,
                    time="18:00",
                ),
            ]
        )

        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    seed()
    print("Seed completed")
