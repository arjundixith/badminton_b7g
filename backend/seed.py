from __future__ import annotations

import argparse
from datetime import datetime, timedelta

from app import models
from app.database import Base, SessionLocal, engine

TEAM_ROSTERS = {
    "Golden Monks": {
        "Set-1": ["Swaroop", "Ashutosh", "Avinash"],
        "Set-2": [],
        "Set-3": ["Karan", "Lavanya Avinash"],
        "Set-4": ["Aravind", "Saurabh", "Sudipto", "Pallavi Pradhan"],
        "Set-5": ["Harish", "Prashanth SP", "Subramanya", "Harshitha"],
    },
    "Spartans": {
        "Set-1": ["Nagakiran", "Nitesh", "Sriraman"],
        "Set-2": [],
        "Set-3": ["Ramakrishna Reddy", "Himani"],
        "Set-4": ["Akshay", "Manohar", "Ramesh", "Lavanya Veeresh"],
        "Set-5": ["Ajay", "Srilakshman", "Subhankar", "Radhika"],
    },
    "Feather Fighters": {
        "Set-1": ["Suman", "Arjun Dixith", "Jeetu"],
        "Set-2": [],
        "Set-3": ["Ranjith", "Snigdha"],
        "Set-4": ["Akash", "Arjun Karnam", "Venkatesh", "Srishti"],
        "Set-5": ["Pradeep", "Jay Nair", "Prakash Tirumali", "Hetal"],
    },
    "Lightening Racquets": {
        "Set-1": ["Seema", "Aditya", "Ananth"],
        "Set-2": [],
        "Set-3": ["Prashanth Crasta", "Trupthi"],
        "Set-4": ["Ashwith", "Kanhu", "Umakanth", "Sohini"],
        "Set-5": ["Kumar Nayak", "Mohith", "Raghavendra", "Saroja"],
    },
    "Smash Hawks": {
        "Set-1": ["Pratham", "Darshan", "Abhishek"],
        "Set-2": [],
        "Set-3": ["Antony Avinash", "Ruchika"],
        "Set-4": ["Shrinivas", "Shripathi", "Shyam", "Preethi"],
        "Set-5": ["Ranganath", "Saiprasad", "Sanjeev", "Reshma Bhat"],
    },
}

TEAM_MATCH_LINEUPS = {
    "Golden Monks": {
        1: "Swaroop / Ashutosh",
        2: "Aravind / Saurabh / Sudipto / Pallavi Pradhan",
        3: "Harish / Prashanth SP / Subramanya",
        4: "Karan / Lavanya Avinash",
        5: "Avinash / Swaroop / Ashutosh",
        6: "Aravind / Saurabh / Sudipto",
        7: "Harish / Prashanth SP / Subramanya / Harshitha",
        8: "Lavanya Avinash / Pallavi Pradhan",
        9: "Avinash / Swaroop / Ashutosh",
        10: "Karan / Aravind / Saurabh / Sudipto",
        11: "Aravind / Saurabh / Sudipto",
        12: "Harish / Prashanth SP / Subramanya / Harshitha",
        13: "Avinash",
    },
    "Spartans": {
        1: "Nagakiran / Nitesh",
        2: "Akshay / Manohar / Ramesh / Lavanya Veeresh",
        3: "Ajay / Srilakshman / Subhankar",
        4: "Ramakrishna Reddy / Himani",
        5: "Sriraman / Nagakiran / Nitesh",
        6: "Akshay / Manohar / Ramesh",
        7: "Ajay / Srilakshman / Subhankar / Radhika",
        8: "Himani / Lavanya Veeresh",
        9: "Sriraman / Nagakiran / Nitesh",
        10: "Ramakrishna Reddy / Akshay / Manohar / Ramesh",
        11: "Akshay / Manohar / Ramesh",
        12: "Ajay / Srilakshman / Subhankar / Radhika",
        13: "Sriraman",
    },
    "Feather Fighters": {
        1: "Suman / Arjun Dixith",
        2: "Akash / Arjun Karnam / Venkatesh / Srishti",
        3: "Pradeep / Jay Nair / Prakash Tirumali",
        4: "Ranjith / Snigdha",
        5: "Jeetu / Suman / Arjun Dixith",
        6: "Akash / Arjun Karnam / Venkatesh",
        7: "Pradeep / Jay Nair / Prakash Tirumali / Hetal",
        8: "Snigdha / Srishti",
        9: "Jeetu / Suman / Arjun Dixith",
        10: "Ranjith / Akash / Arjun Karnam / Venkatesh",
        11: "Akash / Arjun Karnam / Venkatesh",
        12: "Pradeep / Jay Nair / Prakash Tirumali / Hetal",
        13: "Jeetu",
    },
    "Lightening Racquets": {
        1: "Seema / Aditya",
        2: "Ashwith / Kanhu / Umakanth / Sohini",
        3: "Kumar Nayak / Mohith / Raghavendra",
        4: "Prashanth Crasta / Trupthi",
        5: "Ananth / Seema / Aditya",
        6: "Ashwith / Kanhu / Umakanth",
        7: "Kumar Nayak / Mohith / Raghavendra / Saroja",
        8: "Trupthi / Sohini",
        9: "Ananth / Seema / Aditya",
        10: "Prashanth Crasta / Ashwith / Kanhu / Umakanth",
        11: "Ashwith / Kanhu / Umakanth",
        12: "Kumar Nayak / Mohith / Raghavendra / Saroja",
        13: "Ananth",
    },
    "Smash Hawks": {
        1: "Pratham / Darshan",
        2: "Shrinivas / Shripathi / Shyam / Preethi",
        3: "Ranganath / Saiprasad / Sanjeev",
        4: "Antony Avinash / Ruchika",
        5: "Abhishek / Pratham / Darshan",
        6: "Shrinivas / Shripathi / Shyam",
        7: "Ranganath / Saiprasad / Sanjeev / Reshma Bhat",
        8: "Ruchika / Preethi",
        9: "Abhishek / Pratham / Darshan",
        10: "Antony Avinash / Shrinivas / Shripathi / Shyam",
        11: "Shrinivas / Shripathi / Shyam",
        12: "Ranganath / Saiprasad / Sanjeev / Reshma Bhat",
        13: "Abhishek",
    },
}

ROUND_ROBIN_FIXTURES = [
    {"tie_no": 1, "day": 1, "session": "morning", "court": 2, "team1": "Golden Monks", "team2": "Spartans"},
    {"tie_no": 2, "day": 1, "session": "morning", "court": 4, "team1": "Feather Fighters", "team2": "Lightening Racquets"},
    {"tie_no": 3, "day": 1, "session": "after lunch", "court": 2, "team1": "Golden Monks", "team2": "Feather Fighters"},
    {"tie_no": 4, "day": 1, "session": "after lunch", "court": 4, "team1": "Spartans", "team2": "Smash Hawks"},
    {"tie_no": 5, "day": 1, "session": "after tea", "court": 4, "team1": "Golden Monks", "team2": "Lightening Racquets"},
    {"tie_no": 6, "day": 1, "session": "after tea", "court": 2, "team1": "Feather Fighters", "team2": "Smash Hawks"},
    {"tie_no": 7, "day": 2, "session": "morning", "court": 4, "team1": "Golden Monks", "team2": "Smash Hawks"},
    {"tie_no": 8, "day": 2, "session": "morning", "court": 2, "team1": "Spartans", "team2": "Lightening Racquets"},
    {"tie_no": 9, "day": 2, "session": "after lunch", "court": 4, "team1": "Spartans", "team2": "Feather Fighters"},
    {"tie_no": 10, "day": 2, "session": "after lunch", "court": 2, "team1": "Lightening Racquets", "team2": "Smash Hawks"},
]

TIE_MATCH_TEMPLATES = [
    {"match_no": 1, "discipline": "Set 1 OR 2 / Set 1 OR 2", "set_level": "Set-1", "doubles": True},
    {"match_no": 2, "discipline": "Set-4 / Women's Intermediate", "set_level": "Set-4", "doubles": True},
    {"match_no": 3, "discipline": "Set 5 / Set 5", "set_level": "Set-5", "doubles": True},
    {"match_no": 4, "discipline": "Set 3 / Womens Advance", "set_level": "Set-3", "doubles": True},
    {"match_no": 5, "discipline": "Advance / Set-1 OR Set 2", "set_level": "Set-1", "doubles": True},
    {"match_no": 6, "discipline": "Set 4 / Set 4", "set_level": "Set-4", "doubles": True},
    {"match_no": 7, "discipline": "Set 5 / Womens Beginner", "set_level": "Set-5", "doubles": True},
    {"match_no": 8, "discipline": "Womens Advance / Women Intermediate", "set_level": "Set-3", "doubles": True},
    {"match_no": 9, "discipline": "Advance / Set1 OR Set2", "set_level": "Set-1", "doubles": True},
    {"match_no": 10, "discipline": "Set 3 / Set 4", "set_level": "Set-3", "doubles": True},
    {"match_no": 11, "discipline": "Set-4 / Set-4", "set_level": "Set-4", "doubles": True},
    {"match_no": 12, "discipline": "Set-5 / Women's Beginner", "set_level": "Set-5", "doubles": True},
    {"match_no": 13, "discipline": "Advance (Decider if tie is 6-6)", "set_level": "Set-1", "doubles": False},
]

SESSION_START_TIME = {
    "morning": "09:30",
    "after lunch": "13:30",
    "after tea": "17:30",
}


def reset_database() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def plus_minutes(time_value: str, minutes: int) -> str:
    parsed = datetime.strptime(time_value, "%H:%M")
    return (parsed + timedelta(minutes=minutes)).strftime("%H:%M")


def get_tie_match_time(session: str, match_no: int) -> str:
    start = SESSION_START_TIME.get(session, "09:30")
    return plus_minutes(start, (match_no - 1) * 15)


def apply_demo_progress(tie: models.Tie, matches: list[models.Match], referee: models.Referee) -> None:
    if tie.tie_no == 1:
        winners = [1, 2, 1, 1, 2, 1, 2]
        scores = [(21, 17), (16, 21), (21, 19), (22, 20), (19, 21), (21, 14), (18, 21)]

        for match, winner, score in zip(matches, winners, scores):
            match.team1_score, match.team2_score = score
            match.winner_side = winner
            match.status = "completed"
            match.referee_id = referee.id

        tie.score1 = 4
        tie.score2 = 3
        tie.status = "completed"
        tie.winner_team_id = tie.team1_id

    elif tie.tie_no == 2:
        winners = [2, 2, 1, 2, 2, 1, 2]
        scores = [(17, 21), (18, 21), (21, 16), (15, 21), (20, 22), (21, 19), (14, 21)]

        for match, winner, score in zip(matches, winners, scores):
            match.team1_score, match.team2_score = score
            match.winner_side = winner
            match.status = "completed"
            match.referee_id = referee.id

        tie.score1 = 2
        tie.score2 = 5
        tie.status = "completed"
        tie.winner_team_id = tie.team2_id

    elif tie.tie_no == 3:
        first = matches[0]
        first.team1_score = 21
        first.team2_score = 18
        first.winner_side = 1
        first.status = "completed"
        first.referee_id = referee.id

        second = matches[1]
        second.team1_score = 15
        second.team2_score = 14
        second.winner_side = None
        second.status = "live"
        second.referee_id = referee.id

        tie.score1 = 1
        tie.score2 = 0
        tie.status = "live"
        tie.winner_team_id = None

    else:
        tie.score1 = 0
        tie.score2 = 0
        tie.status = "pending"
        tie.winner_team_id = None


def seed(*, demo_progress: bool = False) -> None:
    reset_database()

    db = SessionLocal()
    try:
        teams: dict[str, models.Team] = {}

        for team_name, players in TEAM_ROSTERS.items():
            team = models.Team(name=team_name)
            db.add(team)
            db.flush()
            teams[team_name] = team

            for set_level, names in players.items():
                for name in names:
                    db.add(models.Player(name=name, set_level=set_level, team_id=team.id))

        db.flush()

        for fixture in ROUND_ROBIN_FIXTURES:
            team1 = teams[fixture["team1"]]
            team2 = teams[fixture["team2"]]

            tie = models.Tie(
                tie_no=fixture["tie_no"],
                day=fixture["day"],
                session=fixture["session"],
                court=fixture["court"],
                team1_id=team1.id,
                team2_id=team2.id,
                status="pending",
            )
            db.add(tie)
            db.flush()

            tie_matches: list[models.Match] = []
            for template in TIE_MATCH_TEMPLATES:
                offset = fixture["tie_no"] + template["match_no"]

                team1_lineup = TEAM_MATCH_LINEUPS[fixture["team1"]][template["match_no"]]
                team2_lineup = TEAM_MATCH_LINEUPS[fixture["team2"]][template["match_no"]]

                match = models.Match(
                    stage="tie",
                    tie_id=tie.id,
                    match_no=template["match_no"],
                    discipline=template["discipline"],
                    team1_id=team1.id,
                    team2_id=team2.id,
                    team1_lineup=team1_lineup,
                    team2_lineup=team2_lineup,
                    day=fixture["day"],
                    session=fixture["session"],
                    court=fixture["court"],
                    time=get_tie_match_time(fixture["session"], template["match_no"]),
                    lineup_confirmed=False,
                    status="pending",
                )
                db.add(match)
                tie_matches.append(match)

            if demo_progress:
                referee = (
                    db.query(models.Referee)
                    .filter(models.Referee.name == "Neutral Umpire")
                    .first()
                )
                if referee is None:
                    referee = models.Referee(name="Neutral Umpire")
                    db.add(referee)
                    db.flush()
                apply_demo_progress(tie, tie_matches, referee)

        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed tournament data.")
    parser.add_argument(
        "--demo-progress",
        action="store_true",
        help="Seed with sample completed/live matches for demo screens.",
    )
    args = parser.parse_args()

    seed(demo_progress=args.demo_progress)
    mode = "demo" if args.demo_progress else "fresh"
    print(f"Seed completed ({mode})")
