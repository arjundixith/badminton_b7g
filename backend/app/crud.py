from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from . import models, schemas


def _normalize_text(value: str) -> str:
    return " ".join(value.split())


def get_teams(db: Session) -> list[models.Team]:
    return db.query(models.Team).order_by(models.Team.name.asc()).all()


def create_team(db: Session, payload: schemas.TeamCreate) -> models.Team:
    name = _normalize_text(payload.name)
    if not name:
        raise ValueError("Team name cannot be empty.")

    existing = (
        db.query(models.Team)
        .filter(func.lower(models.Team.name) == name.lower())
        .first()
    )
    if existing:
        raise ValueError("A team with this name already exists.")

    team = models.Team(name=name)
    db.add(team)
    db.commit()
    db.refresh(team)
    return team


def get_players(db: Session) -> list[models.Player]:
    return db.query(models.Player).order_by(models.Player.id.asc()).all()


def create_player(db: Session, payload: schemas.PlayerCreate) -> models.Player:
    name = _normalize_text(payload.name)
    category = _normalize_text(payload.category)

    if not name:
        raise ValueError("Player name cannot be empty.")
    if not category:
        raise ValueError("Player category cannot be empty.")

    team = db.get(models.Team, payload.team_id)
    if not team:
        raise LookupError("Team not found.")

    player = models.Player(name=name, category=category, team_id=payload.team_id)
    db.add(player)
    db.commit()
    db.refresh(player)
    return player


def get_tie_or_raise(db: Session, tie_id: int) -> models.Tie:
    tie = (
        db.query(models.Tie)
        .options(
            selectinload(models.Tie.team1),
            selectinload(models.Tie.team2),
            selectinload(models.Tie.matches),
        )
        .filter(models.Tie.id == tie_id)
        .first()
    )
    if not tie:
        raise LookupError("Tie not found.")
    return tie


def get_ties(db: Session) -> list[models.Tie]:
    return (
        db.query(models.Tie)
        .options(selectinload(models.Tie.team1), selectinload(models.Tie.team2))
        .order_by(models.Tie.id.asc())
        .all()
    )


def create_tie(db: Session, team1_id: int, team2_id: int) -> models.Tie:
    if team1_id == team2_id:
        raise ValueError("A tie requires two distinct teams.")

    team1 = db.get(models.Team, team1_id)
    team2 = db.get(models.Team, team2_id)
    if not team1 or not team2:
        raise LookupError("Both teams must exist before creating a tie.")

    tie = models.Tie(team1_id=team1_id, team2_id=team2_id)
    db.add(tie)
    db.commit()
    db.refresh(tie)
    return get_tie_or_raise(db, tie.id)


def create_match(
    db: Session,
    tie_id: int,
    match_no: int,
    day: int | None = None,
    session: str | None = None,
    court: int | None = None,
    time: str | None = None,
) -> models.Match:
    _ = get_tie_or_raise(db, tie_id)

    match = models.Match(
        tie_id=tie_id,
        match_no=match_no,
        day=day,
        session=session,
        court=court,
        time=time,
    )
    db.add(match)
    db.commit()
    db.refresh(match)
    return get_match_or_raise(db, match.id)


def get_match_or_raise(db: Session, match_id: int) -> models.Match:
    match = (
        db.query(models.Match)
        .options(
            selectinload(models.Match.tie).selectinload(models.Tie.team1),
            selectinload(models.Match.tie).selectinload(models.Tie.team2),
            selectinload(models.Match.referee),
        )
        .filter(models.Match.id == match_id)
        .first()
    )
    if not match:
        raise LookupError("Match not found.")
    return match


def list_matches(db: Session) -> list[models.Match]:
    return (
        db.query(models.Match)
        .options(
            selectinload(models.Match.tie).selectinload(models.Tie.team1),
            selectinload(models.Match.tie).selectinload(models.Tie.team2),
        )
        .order_by(
            models.Match.day.asc(),
            models.Match.time.asc(),
            models.Match.match_no.asc(),
            models.Match.id.asc(),
        )
        .all()
    )


def list_matches_by_tie(db: Session, tie_id: int) -> list[models.Match]:
    _ = get_tie_or_raise(db, tie_id)

    return (
        db.query(models.Match)
        .options(
            selectinload(models.Match.tie).selectinload(models.Tie.team1),
            selectinload(models.Match.tie).selectinload(models.Tie.team2),
        )
        .filter(models.Match.tie_id == tie_id)
        .order_by(models.Match.match_no.asc())
        .all()
    )


def _is_finished(score1: int, score2: int) -> bool:
    high = max(score1, score2)
    low = min(score1, score2)

    return (high >= 21 and (high - low) >= 2) or high == 30


def _calculate_winner_side(score1: int, score2: int) -> int | None:
    if not _is_finished(score1, score2) or score1 == score2:
        return None
    return 1 if score1 > score2 else 2


def _recalculate_tie_totals(db: Session, tie_id: int) -> None:
    tie = db.get(models.Tie, tie_id)
    if not tie:
        return

    winner_sides = (
        db.query(models.Match.winner_side)
        .filter(models.Match.tie_id == tie_id)
        .all()
    )

    score1 = sum(1 for (winner_side,) in winner_sides if winner_side == 1)
    score2 = sum(1 for (winner_side,) in winner_sides if winner_side == 2)

    tie.score1 = score1
    tie.score2 = score2

    total_matches = len(winner_sides)
    wins_needed = (total_matches // 2) + 1 if total_matches else 0
    if wins_needed and score1 >= wins_needed:
        tie.winner_team_id = tie.team1_id
    elif wins_needed and score2 >= wins_needed:
        tie.winner_team_id = tie.team2_id
    else:
        tie.winner_team_id = None


def update_score(db: Session, match_id: int, score1: int, score2: int) -> models.Match:
    if score1 < 0 or score2 < 0:
        raise ValueError("Scores cannot be negative.")
    if score1 > 30 or score2 > 30:
        raise ValueError("Scores cannot exceed 30 in badminton scoring.")

    match = db.get(models.Match, match_id)
    if not match:
        raise LookupError("Match not found.")

    match.team1_score = score1
    match.team2_score = score2
    match.winner_side = _calculate_winner_side(score1, score2)

    _recalculate_tie_totals(db, match.tie_id)

    db.commit()
    return get_match_or_raise(db, match_id)


def get_or_create_referee(db: Session, name: str) -> models.Referee:
    clean_name = _normalize_text(name)
    if not clean_name:
        raise ValueError("Referee name cannot be empty.")

    referee = (
        db.query(models.Referee)
        .filter(func.lower(models.Referee.name) == clean_name.lower())
        .first()
    )
    if referee:
        return referee

    referee = models.Referee(name=clean_name)
    db.add(referee)
    db.commit()
    db.refresh(referee)
    return referee


def assign_referee(db: Session, match_id: int, name: str) -> tuple[models.Referee, models.Match]:
    referee = get_or_create_referee(db, name)
    match = db.get(models.Match, match_id)
    if not match:
        raise LookupError("Match not found.")

    match.referee_id = referee.id
    db.commit()

    return referee, get_match_or_raise(db, match_id)
