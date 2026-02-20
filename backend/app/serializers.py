from . import models, schemas


def match_to_read(match: models.Match) -> schemas.MatchRead:
    team1_name = match.tie.team1.name if match.tie and match.tie.team1 else "TBD"
    team2_name = match.tie.team2.name if match.tie and match.tie.team2 else "TBD"

    return schemas.MatchRead(
        id=match.id,
        tie_id=match.tie_id,
        match_no=match.match_no,
        day=match.day,
        session=match.session,
        court=match.court,
        time=match.time,
        team1=team1_name,
        team2=team2_name,
        team1_score=match.team1_score,
        team2_score=match.team2_score,
        referee_id=match.referee_id,
        winner_side=match.winner_side,
    )


def tie_to_read(tie: models.Tie) -> schemas.TieRead:
    team1_name = tie.team1.name if tie.team1 else "TBD"
    team2_name = tie.team2.name if tie.team2 else "TBD"

    return schemas.TieRead(
        id=tie.id,
        team1_id=tie.team1_id,
        team2_id=tie.team2_id,
        team1=team1_name,
        team2=team2_name,
        score1=tie.score1,
        score2=tie.score2,
        winner_team_id=tie.winner_team_id,
    )


def match_to_schedule_item(match: models.Match) -> schemas.ScheduleMatch:
    read_model = match_to_read(match)
    return schemas.ScheduleMatch(
        id=read_model.id,
        match_no=read_model.match_no,
        court=read_model.court,
        time=read_model.time,
        team1=read_model.team1,
        team2=read_model.team2,
        score1=read_model.team1_score,
        score2=read_model.team2_score,
    )
