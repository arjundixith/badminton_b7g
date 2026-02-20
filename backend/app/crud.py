from collections import Counter
import re
from typing import Literal

from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from . import models, schemas, serializers

MatchStage = Literal["tie"]
MatchStatus = Literal["pending", "live", "completed"]

CATEGORY_ORDER: list[str] = [
    "Men Advance",
    "Men Set-1",
    "Men Set-2",
    "Men Set-3",
    "Men Set-4",
    "Men Set-5",
    "Women Advance",
    "Women Intermediate",
    "Women Beginner",
]

SET_LEVEL_TO_CATEGORY = {
    "Set-1": "Men Set-1",
    "Set-2": "Men Set-2",
    "Set-3": "Men Set-3",
    "Set-4": "Men Set-4",
    "Set-5": "Men Set-5",
}


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


def _discipline_slot_tokens(discipline: str) -> list[str]:
    clean = _normalize_text(discipline or "")
    if not clean:
        return []

    parts = [_normalize_text(item) for item in clean.split("/")]
    parts = [item for item in parts if item]
    if parts:
        return parts
    return [clean]


def _category_from_discipline_token(token: str) -> str | None:
    text = (token or "").lower()
    if not text:
        return None

    if "women" in text and "advance" in text:
        return "Women Advance"
    if "women" in text and "intermediate" in text:
        return "Women Intermediate"
    if "women" in text and "beginner" in text:
        return "Women Beginner"
    if "advance" in text:
        return "Men Advance"

    if "set-1" in text or "set 1" in text or "set1" in text:
        return "Men Set-1"
    if "set-2" in text or "set 2" in text or "set2" in text:
        return "Men Set-2"
    if "set-3" in text or "set 3" in text or "set3" in text:
        return "Men Set-3"
    if "set-4" in text or "set 4" in text or "set4" in text:
        return "Men Set-4"
    if "set-5" in text or "set 5" in text or "set5" in text:
        return "Men Set-5"

    return None


def _winner_lineup_players(lineup: str, excluded_names: set[str]) -> list[str]:
    players: list[str] = []
    seen: set[str] = set()
    for name in _lineup_parts(lineup):
        key = name.casefold()
        if key in excluded_names or key in seen:
            continue
        seen.add(key)
        players.append(name)
    return players


def _set_option_categories_from_token(token: str) -> list[str]:
    text = (token or "").lower()
    if " or " not in text:
        return []

    parts = re.split(r"\bor\b", text)
    seen: set[str] = set()
    categories: list[str] = []
    for part in parts:
        number = None
        match_with_set = re.search(r"set[\s-]*(\d)", part)
        if match_with_set:
            number = match_with_set.group(1)
        else:
            # Supports tokens like "Set 1 OR 2" where second option is a bare number.
            bare_match = re.search(r"\b([1-5])\b", part)
            if bare_match:
                number = bare_match.group(1)
        if not number:
            continue
        category = f"Men Set-{number}"
        if category in CATEGORY_ORDER and category not in seen:
            seen.add(category)
            categories.append(category)
    return categories


def _category_options_from_token(token: str) -> list[str]:
    token_category = _category_from_discipline_token(token)
    lower_token = (token or "").lower()

    if token_category and token_category.startswith("Women"):
        return [token_category]
    if "advance" in lower_token:
        return ["Men Advance"]

    set_options = _set_option_categories_from_token(token)
    if set_options:
        return set_options
    if token_category:
        return [token_category]
    return []


def _category_for_slot_assignment(
    token: str,
    player_name: str,
    slot_index: int,
    set_level_by_name: dict[str, str],
) -> str | None:
    options = _category_options_from_token(token)
    if not options:
        level = set_level_by_name.get(player_name.casefold())
        return SET_LEVEL_TO_CATEGORY.get(level) if level else None

    if len(options) == 1:
        return options[0]

    # When OR options are present, prefer player's registered set-level.
    level = set_level_by_name.get(player_name.casefold())
    if level:
        level_category = SET_LEVEL_TO_CATEGORY.get(level)
        if level_category in options:
            return level_category

    # Fallback to slot ordering (first lineup name => first option, etc).
    if 0 <= slot_index < len(options):
        return options[slot_index]
    return options[0]


def _is_decider_match(match: models.Match) -> bool:
    if match.match_no == 13:
        return True
    return "decider" in (match.discipline or "").lower()


def _is_decider_unlocked(tie: models.Tie | None) -> bool:
    if tie is None:
        return False
    return tie.score1 == 6 and tie.score2 == 6


def _is_decider_result_state(tie: models.Tie | None) -> bool:
    if tie is None:
        return False
    total = tie.score1 + tie.score2
    high = max(tie.score1, tie.score2)
    return total == 13 and high == 7


def _is_decider_allowed_in_views(tie: models.Tie | None) -> bool:
    return _is_decider_unlocked(tie) or _is_decider_result_state(tie)


def _assert_decider_unlocked(match: models.Match) -> None:
    if not _is_decider_match(match):
        return
    if not _is_decider_unlocked(match.tie):
        raise ValueError("Game 13 can start only when the tie score is 6-6.")


def _should_include_match_in_views(match: models.Match) -> bool:
    if not _is_decider_match(match):
        return True

    tie = match.tie
    if match.status == "pending":
        return _is_decider_unlocked(tie)
    return _is_decider_allowed_in_views(tie)


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

    regular_matches = [match for match in matches if not _is_decider_match(match)]
    decider_match = next((match for match in matches if _is_decider_match(match)), None)
    regular_completed = sum(1 for match in regular_matches if match.winner_side in (1, 2))
    all_regular_completed = bool(regular_matches) and regular_completed == len(regular_matches)
    decider_completed = decider_match is not None and decider_match.winner_side in (1, 2)

    winner_team_id = None
    tie_completed = False

    # Tie result becomes final only after all 12 regular matches are complete.
    # If regular matches end 6-6, result is final only after decider (Game 13) completes.
    if all_regular_completed:
        if score1 != score2:
            winner_team_id = tie.team1_id if score1 > score2 else tie.team2_id
            tie_completed = True
        elif decider_completed:
            winner_team_id = tie.team1_id if score1 > score2 else tie.team2_id
            tie_completed = True

    tie.winner_team_id = winner_team_id

    if tie_completed:
        tie.status = "completed"
    elif any(match.status == "live" for match in matches) or any(
        match.team1_score > 0 or match.team2_score > 0 for match in matches
    ):
        tie.status = "live"
    else:
        tie.status = "pending"

    db.commit()


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
        visible_matches = [match for match in tie.matches if _should_include_match_in_views(match)]
        visible_matches.sort(key=lambda match: match.match_no)
        tie.matches = visible_matches

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

    matches = [match for match in query.all() if _should_include_match_in_views(match)]
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

    if _is_decider_match(match) and match.winner_side not in (1, 2):
        _assert_decider_unlocked(match)

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

    if _is_decider_match(match):
        # Decider is always singles: keep one player per team.
        team1_parts = _lineup_parts(clean_team1_lineup)
        team2_parts = _lineup_parts(clean_team2_lineup)
        if len(team1_parts) < 1:
            raise ValueError("Team 1 lineup must have exactly one advance player for Game 13.")
        if len(team2_parts) < 1:
            raise ValueError("Team 2 lineup must have exactly one advance player for Game 13.")
        clean_team1_lineup = team1_parts[0]
        clean_team2_lineup = team2_parts[0]
        match.lineup_confirmed = True
    elif _requires_referee_lineup_entry(match):
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
        if _is_decider_match(match):
            _assert_decider_unlocked(match)
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

    _assert_decider_unlocked(match)

    match.referee_id = referee.id

    clean_team1_lineup = _normalize_lineup_text(match.team1_lineup or "")
    clean_team2_lineup = _normalize_lineup_text(match.team2_lineup or "")
    match.team1_lineup = clean_team1_lineup
    match.team2_lineup = clean_team2_lineup

    if _is_decider_match(match):
        team1_parts = _lineup_parts(clean_team1_lineup)
        team2_parts = _lineup_parts(clean_team2_lineup)
        if len(team1_parts) >= 1 and len(team2_parts) >= 1:
            match.team1_lineup = team1_parts[0]
            match.team2_lineup = team2_parts[0]
            match.lineup_confirmed = True
        else:
            match.lineup_confirmed = False
    elif _requires_referee_lineup_entry(match):
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
    ties = get_ties(db)

    table: dict[int, dict[str, int | str]] = {
        team.id: {
            "team": team.name,
            "ties_played": 0,
            "ties_won": 0,
            "ties_lost": 0,
            "tie_points": 0,
            "games_played": 0,
            "games_won": 0,
            "games_lost": 0,
            "points_for": 0,
            "points_against": 0,
        }
        for team in teams
    }

    for tie in ties:
        team1_id = tie.team1_id
        team2_id = tie.team2_id

        if team1_id not in table or team2_id not in table:
            continue

        if tie.status == "completed" and tie.winner_team_id in (team1_id, team2_id):
            table[team1_id]["ties_played"] += 1
            table[team2_id]["ties_played"] += 1

            if tie.winner_team_id == team1_id:
                table[team1_id]["ties_won"] += 1
                table[team2_id]["ties_lost"] += 1
                table[team1_id]["tie_points"] += 2
            else:
                table[team2_id]["ties_won"] += 1
                table[team1_id]["ties_lost"] += 1
                table[team2_id]["tie_points"] += 2

        for match in tie.matches:
            if match.stage != "tie" or match.winner_side not in (1, 2):
                continue
            if _is_decider_match(match) and not _is_decider_allowed_in_views(tie):
                continue

            table[team1_id]["games_played"] += 1
            table[team2_id]["games_played"] += 1

            table[team1_id]["points_for"] += match.team1_score
            table[team1_id]["points_against"] += match.team2_score
            table[team2_id]["points_for"] += match.team2_score
            table[team2_id]["points_against"] += match.team1_score

            if match.winner_side == 1:
                table[team1_id]["games_won"] += 1
                table[team2_id]["games_lost"] += 1
            else:
                table[team2_id]["games_won"] += 1
                table[team1_id]["games_lost"] += 1

    ranked = sorted(
        table.items(),
        key=lambda item: (
            -int(item[1]["ties_won"]),
            -int(item[1]["games_won"]),
            -(
                (
                    int(item[1]["points_for"]) - int(item[1]["points_against"])
                )
                / max(1, int(item[1]["games_played"]))
            ),
            -(int(item[1]["points_for"]) - int(item[1]["points_against"])),
            -(int(item[1]["games_won"]) - int(item[1]["games_lost"])),
            str(item[1]["team"]),
        ),
    )

    total_ties = len(ties)
    completed_ties = sum(1 for tie in ties if tie.status == "completed" and tie.winner_team_id is not None)
    league_complete = total_ties > 0 and completed_ties == total_ties

    standings: list[schemas.StandingRow] = []
    for rank, (team_id, row) in enumerate(ranked, start=1):
        games_played = int(row["games_played"])
        games_won = int(row["games_won"])
        games_lost = int(row["games_lost"])
        points_for = int(row["points_for"])
        points_against = int(row["points_against"])
        point_difference = points_for - points_against
        average_match_lead = point_difference / games_played if games_played > 0 else 0.0

        qualification = "none"
        if league_complete:
            if rank <= 2:
                qualification = "finalist"
            elif rank == 3:
                qualification = "bronze"

        standings.append(
            schemas.StandingRow(
                rank=rank,
                team_id=team_id,
                team=str(row["team"]),
                ties_played=int(row["ties_played"]),
                ties_won=int(row["ties_won"]),
                ties_lost=int(row["ties_lost"]),
                tie_points=int(row["tie_points"]),
                game_difference=games_won - games_lost,
                games_played=games_played,
                games_won=games_won,
                games_lost=games_lost,
                points_for=points_for,
                points_against=points_against,
                point_difference=point_difference,
                average_match_lead=average_match_lead,
                qualification=qualification,
            )
        )

    return standings


def _league_completion_info(db: Session) -> tuple[int, int, bool]:
    ties = db.query(models.Tie).all()
    total_ties = len(ties)
    completed_ties = sum(1 for tie in ties if tie.status == "completed" and tie.winner_team_id is not None)
    league_complete = total_ties > 0 and completed_ties == total_ties
    return total_ties, completed_ties, league_complete


def _get_final_match_query(db: Session):
    return (
        db.query(models.FinalMatch)
        .options(
            selectinload(models.FinalMatch.team1),
            selectinload(models.FinalMatch.team2),
            selectinload(models.FinalMatch.winner_team),
            selectinload(models.FinalMatch.matches).selectinload(models.FinalGame.referee),
        )
    )


def _final_game_templates(db: Session) -> list[tuple[int, str]]:
    rows = (
        db.query(models.Match)
        .filter(models.Match.stage == "tie", models.Match.match_no <= 12)
        .order_by(models.Match.tie_id.asc(), models.Match.match_no.asc())
        .all()
    )
    by_match_no: dict[int, str] = {}
    for row in rows:
        if row.match_no not in by_match_no:
            by_match_no[row.match_no] = row.discipline

    return [(match_no, by_match_no.get(match_no, f"Game {match_no}")) for match_no in range(1, 13)]


def _ensure_final_games(db: Session, final_match: models.FinalMatch, reset_state: bool = False) -> None:
    templates = _final_game_templates(db)
    existing = {game.match_no: game for game in final_match.matches}

    for match_no, discipline in templates:
        game = existing.get(match_no)
        if game is None:
            game = models.FinalGame(
                final_match_id=final_match.id,
                match_no=match_no,
                discipline=discipline,
                status="pending",
                team1_lineup=final_match.team1.name if final_match.team1 else "TBD",
                team2_lineup=final_match.team2.name if final_match.team2 else "TBD",
                lineup_confirmed=True,
                team1_score=0,
                team2_score=0,
                winner_side=None,
                referee_id=None,
            )
            db.add(game)
            continue

        game.discipline = discipline
        if reset_state:
            game.status = "pending"
            game.team1_score = 0
            game.team2_score = 0
            game.winner_side = None
            game.referee_id = None
            game.lineup_confirmed = True
            game.team1_lineup = final_match.team1.name if final_match.team1 else "TBD"
            game.team2_lineup = final_match.team2.name if final_match.team2 else "TBD"


def _recalculate_final_match(db: Session, final_match_id: int) -> None:
    final_match = _get_final_match_query(db).filter(models.FinalMatch.id == final_match_id).first()
    if not final_match:
        return

    games = sorted(final_match.matches, key=lambda item: item.match_no)
    score1 = sum(1 for game in games if game.winner_side == 1)
    score2 = sum(1 for game in games if game.winner_side == 2)

    final_match.team1_score = score1
    final_match.team2_score = score2

    all_completed = len(games) >= 12 and all(game.winner_side in (1, 2) for game in games if game.match_no <= 12)
    all_completed = all_completed and len([game for game in games if game.match_no <= 12]) == 12

    if all_completed:
        if score1 > score2:
            final_match.winner_team_id = final_match.team1_id
        elif score2 > score1:
            final_match.winner_team_id = final_match.team2_id
        else:
            points1 = sum(game.team1_score for game in games if game.match_no <= 12)
            points2 = sum(game.team2_score for game in games if game.match_no <= 12)
            if points1 > points2:
                final_match.winner_team_id = final_match.team1_id
            elif points2 > points1:
                final_match.winner_team_id = final_match.team2_id
            else:
                last_winner_side = next(
                    (game.winner_side for game in sorted(games, key=lambda item: item.match_no, reverse=True) if game.winner_side in (1, 2)),
                    1,
                )
                final_match.winner_team_id = final_match.team1_id if last_winner_side == 1 else final_match.team2_id

        final_match.status = "completed"
        return

    final_match.winner_team_id = None
    if any(game.status == "live" for game in games) or any(game.team1_score > 0 or game.team2_score > 0 for game in games):
        final_match.status = "live"
    else:
        final_match.status = "pending"


def _first_open_final_game(final_match: models.FinalMatch) -> models.FinalGame | None:
    for game in sorted(final_match.matches, key=lambda item: item.match_no):
        if game.winner_side not in (1, 2):
            return game
    return None


def get_or_sync_final_match(
    db: Session,
    standings: list[schemas.StandingRow] | None = None,
) -> models.FinalMatch | None:
    _, _, league_complete = _league_completion_info(db)
    if not league_complete:
        return None

    if standings is None:
        standings = build_standings(db)

    if len(standings) < 2:
        return None

    finalist1_id = standings[0].team_id
    finalist2_id = standings[1].team_id

    final_match = _get_final_match_query(db).first()
    created = False
    if final_match is None:
        final_match = models.FinalMatch(
            team1_id=finalist1_id,
            team2_id=finalist2_id,
            status="pending",
            team1_score=0,
            team2_score=0,
        )
        db.add(final_match)
        db.flush()
        final_match = _get_final_match_query(db).filter(models.FinalMatch.id == final_match.id).first()
        created = True

    finalists_changed = final_match.team1_id != finalist1_id or final_match.team2_id != finalist2_id
    if finalists_changed:
        final_match.team1_id = finalist1_id
        final_match.team2_id = finalist2_id
        db.flush()
        final_match = _get_final_match_query(db).filter(models.FinalMatch.id == final_match.id).first()

    _ensure_final_games(db, final_match, reset_state=created or finalists_changed)
    db.flush()
    _recalculate_final_match(db, final_match.id)
    db.commit()

    return _get_final_match_query(db).filter(models.FinalMatch.id == final_match.id).first()


def _get_final_or_raise(db: Session) -> models.FinalMatch:
    final_match = get_or_sync_final_match(db)
    if not final_match:
        raise ValueError("Final tie is available only after all round-robin ties are completed.")
    return final_match


def assign_final_referee(db: Session, name: str) -> models.FinalMatch:
    final_match = _get_final_or_raise(db)
    game = _first_open_final_game(final_match)
    if not game:
        raise ValueError("Final tie is already completed.")
    return assign_final_game_referee(db, game_id=game.id, name=name)


def update_final_score(db: Session, score1: int, score2: int) -> models.FinalMatch:
    final_match = _get_final_or_raise(db)
    game = _first_open_final_game(final_match)
    if not game:
        raise ValueError("Final tie is already completed.")
    return update_final_game_score(db, game_id=game.id, score1=score1, score2=score2)


def get_final_game_or_raise(db: Session, game_id: int) -> models.FinalGame:
    game = (
        db.query(models.FinalGame)
        .options(
            selectinload(models.FinalGame.final_match).selectinload(models.FinalMatch.team1),
            selectinload(models.FinalGame.final_match).selectinload(models.FinalMatch.team2),
            selectinload(models.FinalGame.referee),
        )
        .filter(models.FinalGame.id == game_id)
        .first()
    )
    if not game:
        raise LookupError("Final game not found.")
    return game


def assign_final_game_referee(db: Session, game_id: int, name: str) -> models.FinalMatch:
    game = get_final_game_or_raise(db, game_id)
    referee = get_or_create_referee(db, name)

    game.referee_id = referee.id
    if game.status == "pending":
        game.status = "live"
    _recalculate_final_match(db, game.final_match_id)
    db.commit()

    refreshed = _get_final_match_query(db).filter(models.FinalMatch.id == game.final_match_id).first()
    if not refreshed:
        raise LookupError("Final tie not found.")
    return refreshed


def update_final_game_score(db: Session, game_id: int, score1: int, score2: int) -> models.FinalMatch:
    game = get_final_game_or_raise(db, game_id)
    if game.referee_id is None:
        raise ValueError("Assign referee before updating final score.")

    _validate_score_input(score1, score2)
    winner_side = _calculate_winner_side(score1, score2)

    game.team1_score = score1
    game.team2_score = score2
    game.winner_side = winner_side
    game.status = "completed" if winner_side in (1, 2) else "live"

    _recalculate_final_match(db, game.final_match_id)
    db.commit()

    refreshed = _get_final_match_query(db).filter(models.FinalMatch.id == game.final_match_id).first()
    if not refreshed:
        raise LookupError("Final tie not found.")
    return refreshed


def build_medal_summary(
    db: Session,
    standings: list[schemas.StandingRow],
    final_match: models.FinalMatch | None,
) -> schemas.MedalSummary:
    _, _, league_complete = _league_completion_info(db)

    finalist1 = standings[0].team if league_complete and len(standings) >= 2 else None
    finalist2 = standings[1].team if league_complete and len(standings) >= 2 else None
    bronze_team = standings[2].team if league_complete and len(standings) >= 3 else None

    gold_team = None
    silver_team = None
    if final_match and final_match.status == "completed" and final_match.winner_team_id in (final_match.team1_id, final_match.team2_id):
        if final_match.winner_team_id == final_match.team1_id:
            gold_team = final_match.team1.name if final_match.team1 else finalist1
            silver_team = final_match.team2.name if final_match.team2 else finalist2
        else:
            gold_team = final_match.team2.name if final_match.team2 else finalist2
            silver_team = final_match.team1.name if final_match.team1 else finalist1

    return schemas.MedalSummary(
        finalist1=finalist1,
        finalist2=finalist2,
        gold_team=gold_team,
        silver_team=silver_team,
        bronze_team=bronze_team,
    )


def build_viewer_dashboard(db: Session) -> schemas.ViewerDashboard:
    ties = get_ties(db)
    all_matches = list_matches(db)
    standings = build_standings(db)
    final_match = get_or_sync_final_match(db, standings)
    medals = build_medal_summary(db, standings, final_match)

    tie_payload = [
        serializers.tie_to_read(tie, sorted(tie.matches, key=lambda match: match.match_no))
        for tie in sorted(ties, key=lambda tie: tie.tie_no)
    ]

    pending_games = sum(1 for match in all_matches if match.status == "pending")
    live_games = sum(1 for match in all_matches if match.status == "live")
    completed_games = sum(1 for match in all_matches if match.status == "completed")
    total_games = len(all_matches)

    # Include the 12 final games only after league completion (i.e., when final match exists).
    if final_match is not None:
        final_games = final_match.matches
        total_games += len(final_games)
        pending_games += sum(1 for game in final_games if game.status == "pending")
        live_games += sum(1 for game in final_games if game.status == "live")
        completed_games += sum(1 for game in final_games if game.status == "completed")

    total_ties, completed_ties, _ = _league_completion_info(db)

    return schemas.ViewerDashboard(
        summary=schemas.DashboardSummary(
            total_games=total_games,
            pending_games=pending_games,
            live_games=live_games,
            completed_games=completed_games,
            total_ties=total_ties,
            completed_ties=completed_ties,
        ),
        standings=standings,
        ties=tie_payload,
        final_match=serializers.final_match_to_read(final_match) if final_match else None,
        medals=medals,
        rule_highlights=[
            "Round-robin league: every team plays every other team once.",
            "Finals qualification is locked only after all league ties are completed.",
            "Ranking order: tie wins, then games won, then average lead per game.",
            "Top 2 qualify as Finalist 1 and Finalist 2; 3rd place gets Bronze medal.",
            "Final tie winner gets Gold medal; other finalist gets Silver medal.",
            "Each match is played to 21; at 20-all continue to a 2-point lead, capped at 30.",
            "Referee assignment is mandatory before score updates.",
        ],
    )


def build_post_finals_category_summary(db: Session) -> schemas.PostFinalsCategorySummary:
    standings = build_standings(db)
    final_match = get_or_sync_final_match(db, standings)
    medals = build_medal_summary(db, standings, final_match)

    set_level_by_name: dict[str, str] = {}
    for player in db.query(models.Player).all():
        key = player.name.casefold()
        if key not in set_level_by_name:
            set_level_by_name[key] = player.set_level

    wins_by_category: dict[str, Counter[str]] = {category: Counter() for category in CATEGORY_ORDER}
    scores_for_by_category: dict[str, Counter[str]] = {category: Counter() for category in CATEGORY_ORDER}
    scores_against_by_category: dict[str, Counter[str]] = {category: Counter() for category in CATEGORY_ORDER}

    tie_matches = (
        db.query(models.Match)
        .options(
            selectinload(models.Match.team1),
            selectinload(models.Match.team2),
        )
        .filter(
            models.Match.stage == "tie",
            models.Match.winner_side.in_([1, 2]),
        )
        .all()
    )

    total_matches_considered = len(tie_matches)
    for match in tie_matches:
        side1_token, side2_token = _discipline_side_tokens(match.discipline)
        winner_side = match.winner_side or 0

        winner_token = side1_token if winner_side == 1 else side2_token
        winner_lineup = match.team1_lineup if winner_side == 1 else match.team2_lineup
        winner_score_points = match.team1_score if winner_side == 1 else match.team2_score
        opponent_score_points = match.team2_score if winner_side == 1 else match.team1_score

        excluded = {
            (match.team1.name if match.team1 else "").casefold(),
            (match.team2.name if match.team2 else "").casefold(),
            "",
        }
        winner_players = _winner_lineup_players(winner_lineup, excluded)
        if not winner_players:
            continue

        for player_index, player_name in enumerate(winner_players):
            category = _category_for_player_on_side(winner_token, f"{player_index}::{player_name}", set_level_by_name)
            if category not in wins_by_category:
                continue
            wins_by_category[category][player_name] += 1
            scores_for_by_category[category][player_name] += int(winner_score_points)
            scores_against_by_category[category][player_name] += int(opponent_score_points)

    final_games = (
        db.query(models.FinalGame)
        .options(
            selectinload(models.FinalGame.final_match).selectinload(models.FinalMatch.team1),
            selectinload(models.FinalGame.final_match).selectinload(models.FinalMatch.team2),
        )
        .filter(models.FinalGame.winner_side.in_([1, 2]))
        .all()
    )
    total_matches_considered += len(final_games)

    for game in final_games:
        final = game.final_match
        side1_token, side2_token = _discipline_side_tokens(game.discipline)
        winner_side = game.winner_side or 0

        winner_token = side1_token if winner_side == 1 else side2_token
        winner_lineup = game.team1_lineup if winner_side == 1 else game.team2_lineup
        winner_score_points = game.team1_score if winner_side == 1 else game.team2_score
        opponent_score_points = game.team2_score if winner_side == 1 else game.team1_score

        excluded = {
            (final.team1.name if final and final.team1 else "").casefold(),
            (final.team2.name if final and final.team2 else "").casefold(),
            "",
        }
        winner_players = _winner_lineup_players(winner_lineup, excluded)
        if not winner_players:
            continue

        for player_index, player_name in enumerate(winner_players):
            category = _category_for_player_on_side(winner_token, f"{player_index}::{player_name}", set_level_by_name)
            if category not in wins_by_category:
                continue
            wins_by_category[category][player_name] += 1
            scores_for_by_category[category][player_name] += int(winner_score_points)
            scores_against_by_category[category][player_name] += int(opponent_score_points)

    categories: list[schemas.CategoryWinnerSummary] = []
    for category in CATEGORY_ORDER:
        win_counter = wins_by_category[category]
        score_for_counter = scores_for_by_category[category]
        score_against_counter = scores_against_by_category[category]
        ranked_players = sorted(
            set(win_counter.keys()) | set(score_for_counter.keys()) | set(score_against_counter.keys()),
            key=lambda name: (
                -int(win_counter[name]),
                int(score_against_counter[name]),
                -(int(score_for_counter[name]) - int(score_against_counter[name])),
                -int(score_for_counter[name]),
                str(name).lower(),
            ),
        )
        winner_wins = int(win_counter[ranked_players[0]]) if ranked_players else 0
        winner_score = int(score_for_counter[ranked_players[0]]) if ranked_players else 0
        winner_opponent_score = int(score_against_counter[ranked_players[0]]) if ranked_players else 0
        winner_lead_score = winner_score - winner_opponent_score
        winner_names = [
            name
            for name in ranked_players
            if (
                int(win_counter[name]) == winner_wins
                and int(score_against_counter[name]) == winner_opponent_score
                and (int(score_for_counter[name]) - int(score_against_counter[name])) == winner_lead_score
                and winner_wins > 0
            )
        ]

        categories.append(
            schemas.CategoryWinnerSummary(
                category=category,
                winner_names=winner_names,
                winner_wins=winner_wins,
                winner_score=winner_score,
                winner_opponent_score=winner_opponent_score,
                winner_lead_score=winner_lead_score,
                rankings=[
                    schemas.CategoryPlayerWin(
                        player_name=name,
                        wins=int(win_counter[name]),
                        total_score=int(score_for_counter[name]),
                        opponent_score=int(score_against_counter[name]),
                        lead_score=int(score_for_counter[name]) - int(score_against_counter[name]),
                    )
                    for name in ranked_players
                ],
            )
        )

    return schemas.PostFinalsCategorySummary(
        final_completed=bool(final_match and final_match.status == "completed"),
        final_status=final_match.status if final_match else None,
        total_matches_considered=total_matches_considered,
        medals=medals,
        categories=categories,
    )
