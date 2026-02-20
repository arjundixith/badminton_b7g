from . import models, schemas


def model_dump_compat(value: object) -> dict[str, object]:
    if hasattr(value, "model_dump"):
        return value.model_dump()  # type: ignore[attr-defined]
    return value.dict()  # type: ignore[union-attr]


def _lineup_needs_referee_input(match: models.Match) -> bool:
    if match.stage != "tie":
        return False

    discipline = (match.discipline or "").lower()
    if "set 3 / womens advance" in discipline:
        return False
    if "womens advance / women intermediate" in discipline:
        return False

    return " or " in discipline or "set-4" in discipline or "set 4" in discipline or "set-5" in discipline or "set 5" in discipline


def match_to_read(match: models.Match) -> schemas.MatchRead:
    team1_name = match.team1.name if match.team1 else "TBD"
    team2_name = match.team2.name if match.team2 else "TBD"

    tie_no = match.tie.tie_no if match.tie else None
    referee_name = match.referee.name if match.referee else None

    return schemas.MatchRead(
        id=match.id,
        stage=match.stage,
        status=match.status,
        tie_id=match.tie_id,
        tie_no=tie_no,
        match_no=match.match_no,
        discipline=match.discipline,
        team1_id=match.team1_id,
        team1=team1_name,
        team1_lineup=match.team1_lineup,
        team2_id=match.team2_id,
        team2=team2_name,
        team2_lineup=match.team2_lineup,
        lineup_confirmed=match.lineup_confirmed,
        lineup_needs_referee_input=_lineup_needs_referee_input(match),
        day=match.day,
        session=match.session,
        court=match.court,
        time=match.time,
        team1_score=match.team1_score,
        team2_score=match.team2_score,
        referee_id=match.referee_id,
        referee_name=referee_name,
        winner_side=match.winner_side,
    )


def tie_to_read(tie: models.Tie, matches: list[models.Match]) -> schemas.TieRead:
    team1_name = tie.team1.name if tie.team1 else "TBD"
    team2_name = tie.team2.name if tie.team2 else "TBD"
    winner_team = tie.winner_team.name if tie.winner_team else None

    return schemas.TieRead(
        id=tie.id,
        tie_no=tie.tie_no,
        day=tie.day,
        session=tie.session,
        court=tie.court,
        team1_id=tie.team1_id,
        team1=team1_name,
        team2_id=tie.team2_id,
        team2=team2_name,
        score1=tie.score1,
        score2=tie.score2,
        status=tie.status,
        winner_team_id=tie.winner_team_id,
        winner_team=winner_team,
        matches=[match_to_read(match) for match in matches],
    )


def final_match_to_read(final_match: models.FinalMatch) -> schemas.FinalMatchRead:
    team1_name = final_match.team1.name if final_match.team1 else "TBD"
    team2_name = final_match.team2.name if final_match.team2 else "TBD"
    winner_team = final_match.winner_team.name if final_match.winner_team else None
    sorted_games = sorted(final_match.matches, key=lambda game: game.match_no)

    return schemas.FinalMatchRead(
        id=final_match.id,
        status=final_match.status,
        team1_id=final_match.team1_id,
        team1=team1_name,
        team2_id=final_match.team2_id,
        team2=team2_name,
        team1_score=final_match.team1_score,
        team2_score=final_match.team2_score,
        winner_team_id=final_match.winner_team_id,
        winner_team=winner_team,
        matches=[
            schemas.FinalGameRead(
                id=game.id,
                match_no=game.match_no,
                discipline=game.discipline,
                status=game.status,
                team1_lineup=game.team1_lineup,
                team2_lineup=game.team2_lineup,
                lineup_confirmed=game.lineup_confirmed,
                team1_score=game.team1_score,
                team2_score=game.team2_score,
                winner_side=game.winner_side,
                referee_id=game.referee_id,
                referee_name=game.referee.name if game.referee else None,
            )
            for game in sorted_games
        ],
    )
