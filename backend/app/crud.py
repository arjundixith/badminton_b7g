from typing import Literal

from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from . import models, schemas, serializers

MatchStage = Literal["tie"]
MatchStatus = Literal["pending", "live", "completed"]


def _normalize_text(value: str) -> str:
    return " ".join(value.split())


def _match_sort_key(match: models.Match) -> tuple[int, int, int, str, int, int, int]:
    day = match.day if match.day is not None else 99
    if match.time and ":" in match.time:
        hour_str, minute_str = match.time.split(":", maxsplit=1)
        try:
            time_as_int = int(hour_str) * 100 + int(minute_str)
        except ValueError:
            time_as_int = 9999
    else:
        time_as_int = 9999
    session = match.session or "zzz"

    return (
        day,
        match.court or 99,
        session,
        time_as_int,
        match.match_no,
        match.id,
    )


def _is_finished(score1: int, score2: int) -> bool:
    high = max(score1, score2)
    low = min(score1, score2)

    return (high >= 21 and (high - low) >= 2) or high == 30


def _calculate_winner_side(score1: int, score2: int) -> int | None:
    if score1 == score2:
        return None
    if not _is_finished(score1, score2):
        return None
    return 1 if score1 > score2 else 2


def _validate_score_input(score1: int, score2: int) -> None:
    if score1 < 0 or score2 < 0:
        raise ValueError("Scores cannot be negative.")
    if score1 > 30 or score2 > 30:
        raise ValueError("Scores cannot exceed 30 (golden point cap).")

    high = max(score1, score2)
    low = min(score1, score2)
    if high > 21 and low < 20:
        raise ValueError("Score cannot go beyond 21 unless both sides have reached 20 (deuce/advantage).")


def _requires_referee_lineup_entry(match: models.Match) -> bool:
    if match.stage != "tie":
        return False

    discipline = (match.discipline or "").lower()
    if "set 3 / womens advance" in discipline:
        return False
    if "womens advance / women intermediate" in discipline:
        return False

    return " or " in discipline or "set-4" in discipline or "set 4" in discipline or "set-5" in discipline or "set 5" in discipline


def _normalize_lineup_text(value: str) -> str:
    parts = [_normalize_text(item) for item in value.split("/")]
    parts = [item for item in parts if item]
    if not parts:
        return ""
    return " / ".join(parts)


def _is_confirmed_doubles_lineup(value: str) -> bool:
    parts = [_normalize_text(item) for item in value.split("/")]
    parts = [item for item in parts if item]
    return len(parts) == 2


def _lineup_parts(value: str) -> list[str]:
    return [_normalize_text(item) for item in value.split("/") if _normalize_text(item)]


def _recalculate_tie(db: Session, tie_id: int) -> None:
    tie = db.get(models.Tie, tie_id)
    if not tie:
        return

    matches = (
        db.query(models.Match)
        .filter(models.Match.tie_id == tie_id, models.Match.stage == "tie")
        .order_by(models.Match.match_no.asc())
        .all()
    )

    score1 = sum(1 for match in matches if match.winner_side == 1)
    score2 = sum(1 for match in matches if match.winner_side == 2)

    tie.score1 = score1
    tie.score2 = score2

    wins_needed = (len(matches) // 2) + 1 if matches else 0
    winner_team_id = None
    if wins_needed and score1 >= wins_needed:
        winner_team_id = tie.team1_id
    elif wins_needed and score2 >= wins_needed:
        winner_team_id = tie.team2_id

    tie.winner_team_id = winner_team_id

    if winner_team_id is not None:
        tie.status = "completed"
    elif any(match.status == "live" for match in matches) or any(
        match.team1_score > 0 or match.team2_score > 0 for match in matches
    ):
        tie.status = "live"
    else:
        tie.status = "pending"


# ---------------------------------------------------------------------------
# Teams and players
# ---------------------------------------------------------------------------


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
    return (
        db.query(models.Player)
        .options(selectinload(models.Player.team))
        .order_by(models.Player.team_id.asc(), models.Player.set_level.asc(), models.Player.name.asc())
        .all()
    )


def create_player(db: Session, payload: schemas.PlayerCreate) -> models.Player:
    name = _normalize_text(payload.name)
    if not name:
        raise ValueError("Player name cannot be empty.")

    team = db.get(models.Team, payload.team_id)
    if not team:
        raise LookupError("Team not found.")

    existing = (
        db.query(models.Player)
        .filter(
            models.Player.team_id == payload.team_id,
            func.lower(models.Player.name) == name.lower(),
        )
        .first()
    )
    if existing:
        raise ValueError("A player with this name already exists for this team.")

    player = models.Player(name=name, set_level=payload.set_level, team_id=payload.team_id)
    db.add(player)
    db.commit()
    db.refresh(player)
    return player


# ---------------------------------------------------------------------------
# Ties and matches
# ---------------------------------------------------------------------------


def get_ties(db: Session) -> list[models.Tie]:
    ties = (
        db.query(models.Tie)
        .options(
            selectinload(models.Tie.team1),
            selectinload(models.Tie.team2),
            selectinload(models.Tie.winner_team),
            selectinload(models.Tie.matches)
            .selectinload(models.Match.team1),
            selectinload(models.Tie.matches)
            .selectinload(models.Match.team2),
            selectinload(models.Tie.matches)
            .selectinload(models.Match.referee),
        )
        .order_by(models.Tie.tie_no.asc())
        .all()
    )

    for tie in ties:
        tie.matches.sort(key=lambda match: match.match_no)

    return ties


def get_tie_or_raise(db: Session, tie_id: int) -> models.Tie:
    tie = (
        db.query(models.Tie)
        .options(
            selectinload(models.Tie.team1),
            selectinload(models.Tie.team2),
            selectinload(models.Tie.winner_team),
            selectinload(models.Tie.matches),
        )
        .filter(models.Tie.id == tie_id)
        .first()
    )
    if not tie:
        raise LookupError("Tie not found.")

    return tie


def list_matches(
    db: Session,
    stage: MatchStage | None = None,
    status: MatchStatus | None = None,
    tie_id: int | None = None,
) -> list[models.Match]:
    query = (
        db.query(models.Match)
        .options(
            selectinload(models.Match.team1),
            selectinload(models.Match.team2),
            selectinload(models.Match.referee),
            selectinload(models.Match.tie),
        )
    )

    query = query.filter(models.Match.stage == "tie")
    if stage:
        query = query.filter(models.Match.stage == stage)
    if status:
        query = query.filter(models.Match.status == status)
    if tie_id is not None:
        query = query.filter(models.Match.tie_id == tie_id)

    matches = query.all()
    matches.sort(key=_match_sort_key)
    return matches


def list_matches_by_tie(db: Session, tie_id: int) -> list[models.Match]:
    _ = get_tie_or_raise(db, tie_id)
    return list_matches(db, stage="tie", tie_id=tie_id)


def get_match_or_raise(db: Session, match_id: int) -> models.Match:
    match = (
        db.query(models.Match)
        .options(
            selectinload(models.Match.team1),
            selectinload(models.Match.team2),
            selectinload(models.Match.referee),
            selectinload(models.Match.tie),
        )
        .filter(models.Match.id == match_id)
        .first()
    )
    if not match:
        raise LookupError("Match not found.")

    return match


def update_score(db: Session, match_id: int, score1: int, score2: int) -> models.Match:
    _validate_score_input(score1, score2)

    match = db.get(models.Match, match_id)
    if not match:
        raise LookupError("Match not found.")

    if match.referee_id is None:
        raise ValueError("Assign referee before updating score.")

    if not match.lineup_confirmed:
        raise ValueError("Player names must be confirmed before scoring.")

    if _requires_referee_lineup_entry(match):
        team1_ready = _is_confirmed_doubles_lineup(match.team1_lineup)
        team2_ready = _is_confirmed_doubles_lineup(match.team2_lineup)
        if not team1_ready or not team2_ready:
            raise ValueError(
                "Referee must confirm two player names per side for this match before scoring."
            )

    winner_side = _calculate_winner_side(score1, score2)

    match.team1_score = score1
    match.team2_score = score2
    match.winner_side = winner_side
    match.status = "completed" if winner_side else "live"

    if match.stage == "tie" and match.tie_id is not None:
        _recalculate_tie(db, match.tie_id)

    db.commit()

    return get_match_or_raise(db, match_id)


def update_lineups(db: Session, match_id: int, team1_lineup: str, team2_lineup: str) -> models.Match:
    match = db.get(models.Match, match_id)
    if not match:
        raise LookupError("Match not found.")

    clean_team1_lineup = _normalize_lineup_text(team1_lineup)
    clean_team2_lineup = _normalize_lineup_text(team2_lineup)
    if not clean_team1_lineup or not clean_team2_lineup:
        raise ValueError("Both lineups are required.")

    if _requires_referee_lineup_entry(match):
        team1_parts = _lineup_parts(clean_team1_lineup)
        team2_parts = _lineup_parts(clean_team2_lineup)

        if len(team1_parts) < 2:
            raise ValueError("Team 1 lineup must have exactly two players separated by '/'.")
        if len(team2_parts) < 2:
            raise ValueError("Team 2 lineup must have exactly two players separated by '/'.")

        # Keep first two confirmed names when broader seed lineups are submitted.
        clean_team1_lineup = f"{team1_parts[0]} / {team1_parts[1]}"
        clean_team2_lineup = f"{team2_parts[0]} / {team2_parts[1]}"
        match.lineup_confirmed = True
    else:
        match.lineup_confirmed = True

    match.team1_lineup = clean_team1_lineup
    match.team2_lineup = clean_team2_lineup

    db.commit()
    return get_match_or_raise(db, match_id)


def update_match_status(db: Session, match_id: int, status: MatchStatus) -> models.Match:
    match = db.get(models.Match, match_id)
    if not match:
        raise LookupError("Match not found.")

    if match.status == "completed":
        raise ValueError("Completed match cannot be changed.")

    if status == "live":
        if match.referee_id is None:
            raise ValueError("Assign referee before setting match live.")
        if match.winner_side in (1, 2):
            raise ValueError("Completed match cannot be set live.")
    elif status == "pending":
        # Keep existing score to allow resuming interrupted games later.
        match.winner_side = None

    match.status = status

    if match.stage == "tie" and match.tie_id is not None:
        _recalculate_tie(db, match.tie_id)

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

    clean_team1_lineup = _normalize_lineup_text(match.team1_lineup or "")
    clean_team2_lineup = _normalize_lineup_text(match.team2_lineup or "")
    match.team1_lineup = clean_team1_lineup
    match.team2_lineup = clean_team2_lineup

    if _requires_referee_lineup_entry(match):
        team1_parts = _lineup_parts(clean_team1_lineup)
        team2_parts = _lineup_parts(clean_team2_lineup)

        if len(team1_parts) >= 2 and len(team2_parts) >= 2:
            # Auto-select first two names so scoring can start immediately.
            match.team1_lineup = f"{team1_parts[0]} / {team1_parts[1]}"
            match.team2_lineup = f"{team2_parts[0]} / {team2_parts[1]}"
            match.lineup_confirmed = True
        else:
            match.lineup_confirmed = False
    else:
        match.lineup_confirmed = bool(clean_team1_lineup and clean_team2_lineup)

    if match.status == "pending":
        match.status = "live"

    if match.stage == "tie" and match.tie_id is not None:
        _recalculate_tie(db, match.tie_id)

    db.commit()

    return referee, get_match_or_raise(db, match_id)


# ---------------------------------------------------------------------------
# Standings and dashboard views
# ---------------------------------------------------------------------------


def build_standings(db: Session) -> list[schemas.StandingRow]:
    teams = get_teams(db)

    table: dict[int, dict[str, int | str]] = {
        team.id: {
            "team": team.name,
            "played": 0,
            "won": 0,
            "lost": 0,
            "tie_points": 0,
            "match_difference": 0,
        }
        for team in teams
    }

    completed_tie_matches = (
        db.query(models.Match)
        .filter(models.Match.stage == "tie", models.Match.winner_side.in_([1, 2]))
        .all()
    )

    for match in completed_tie_matches:
        team1_id = match.team1_id
        team2_id = match.team2_id

        if team1_id not in table or team2_id not in table:
            continue

        table[team1_id]["played"] += 1
        table[team2_id]["played"] += 1

        if match.winner_side == 1:
            table[team1_id]["won"] += 1
            table[team2_id]["lost"] += 1
            table[team1_id]["tie_points"] += 1
            table[team1_id]["match_difference"] += 1
            table[team2_id]["match_difference"] -= 1
        elif match.winner_side == 2:
            table[team2_id]["won"] += 1
            table[team1_id]["lost"] += 1
            table[team2_id]["tie_points"] += 1
            table[team2_id]["match_difference"] += 1
            table[team1_id]["match_difference"] -= 1

    ranked = sorted(
        table.items(),
        key=lambda item: (
            -int(item[1]["tie_points"]),
            -int(item[1]["won"]),
            -int(item[1]["match_difference"]),
            str(item[1]["team"]),
        ),
    )

    standings: list[schemas.StandingRow] = []
    for rank, (team_id, row) in enumerate(ranked, start=1):
        standings.append(
            schemas.StandingRow(
                rank=rank,
                team_id=team_id,
                team=str(row["team"]),
                played=int(row["played"]),
                won=int(row["won"]),
                lost=int(row["lost"]),
                tie_points=int(row["tie_points"]),
                match_difference=int(row["match_difference"]),
            )
        )

    return standings


def build_viewer_dashboard(db: Session) -> schemas.ViewerDashboard:
    ties = get_ties(db)
    all_matches = list_matches(db)
    standings = build_standings(db)

    tie_payload = [
        serializers.tie_to_read(tie, sorted(tie.matches, key=lambda match: match.match_no))
        for tie in sorted(ties, key=lambda tie: tie.tie_no)
    ]

    pending_games = sum(1 for match in all_matches if match.status == "pending")
    live_games = sum(1 for match in all_matches if match.status == "live")
    completed_games = sum(1 for match in all_matches if match.status == "completed")

    return schemas.ViewerDashboard(
        summary=schemas.DashboardSummary(
            total_games=len(all_matches),
            pending_games=pending_games,
            live_games=live_games,
            completed_games=completed_games,
        ),
        standings=standings,
        ties=tie_payload,
        rule_highlights=[
            "Round-robin league: every team plays every other team once.",
            "Standings update after each completed tie match (game-level W/L).",
            "League table uses tie matches only.",
            "Each match is played to 21; at 20-all continue to a 2-point lead, capped at 30.",
            "Referee assignment is mandatory before score updates.",
        ],
    )
