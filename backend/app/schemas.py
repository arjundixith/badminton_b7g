from typing import Literal

from pydantic import BaseModel, Field

try:
    from pydantic import ConfigDict

    class ORMBaseModel(BaseModel):
        model_config = ConfigDict(from_attributes=True)

except ImportError:

    class ORMBaseModel(BaseModel):
        class Config:
            orm_mode = True


MatchStage = Literal["tie"]
MatchStatus = Literal["pending", "live", "completed"]
TieStatus = Literal["pending", "live", "completed"]


class TeamCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)


class TeamRead(ORMBaseModel):
    id: int
    name: str


class PlayerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    set_level: Literal["Set-1", "Set-2", "Set-3", "Set-4", "Set-5"]
    team_id: int = Field(gt=0)


class PlayerRead(ORMBaseModel):
    id: int
    name: str
    set_level: str
    team_id: int


class ScoreUpdate(BaseModel):
    score1: int = Field(ge=0, le=30)
    score2: int = Field(ge=0, le=30)


class LineupUpdate(BaseModel):
    team1_lineup: str = Field(min_length=1, max_length=255)
    team2_lineup: str = Field(min_length=1, max_length=255)


class MatchStatusUpdate(BaseModel):
    status: Literal["pending", "live"]


class RefereeRead(ORMBaseModel):
    id: int
    name: str


class MatchRead(BaseModel):
    id: int
    stage: MatchStage
    status: MatchStatus

    tie_id: int | None = None
    tie_no: int | None = None

    match_no: int
    discipline: str

    team1_id: int
    team1: str
    team1_lineup: str

    team2_id: int
    team2: str
    team2_lineup: str
    lineup_confirmed: bool = True
    lineup_needs_referee_input: bool = False

    day: int
    session: str
    court: int
    time: str

    team1_score: int
    team2_score: int

    referee_id: int | None = None
    referee_name: str | None = None

    winner_side: int | None = None


class TieRead(BaseModel):
    id: int
    tie_no: int

    day: int
    session: str
    court: int

    team1_id: int
    team1: str

    team2_id: int
    team2: str

    score1: int
    score2: int

    status: TieStatus
    winner_team_id: int | None = None
    winner_team: str | None = None

    matches: list[MatchRead] = Field(default_factory=list)


class RefereeAssignmentResponse(BaseModel):
    referee: RefereeRead
    match: MatchRead


class FinalGameRead(BaseModel):
    id: int
    match_no: int
    discipline: str
    status: MatchStatus

    team1_lineup: str
    team2_lineup: str
    lineup_confirmed: bool

    team1_score: int
    team2_score: int
    winner_side: int | None = None

    referee_id: int | None = None
    referee_name: str | None = None


class FinalMatchRead(BaseModel):
    id: int
    status: MatchStatus

    team1_id: int
    team1: str
    team2_id: int
    team2: str

    team1_score: int
    team2_score: int

    winner_team_id: int | None = None
    winner_team: str | None = None
    matches: list[FinalGameRead] = Field(default_factory=list)


class StandingRow(BaseModel):
    rank: int
    team_id: int
    team: str

    ties_played: int
    ties_won: int
    ties_lost: int

    tie_points: int
    game_difference: int
    games_played: int
    games_won: int
    games_lost: int
    points_for: int
    points_against: int
    point_difference: int
    average_match_lead: float
    qualification: Literal["none", "finalist", "bronze"] = "none"


class DashboardSummary(BaseModel):
    total_games: int
    pending_games: int
    live_games: int
    completed_games: int
    total_ties: int
    completed_ties: int


class MedalSummary(BaseModel):
    finalist1: str | None = None
    finalist2: str | None = None
    gold_team: str | None = None
    silver_team: str | None = None
    bronze_team: str | None = None


class CategoryPlayerWin(BaseModel):
    player_name: str
    wins: int
    total_score: int = 0
    opponent_score: int = 0
    lead_score: int = 0


class CategoryWinnerSummary(BaseModel):
    category: str
    winner_names: list[str] = Field(default_factory=list)
    winner_wins: int = 0
    winner_score: int = 0
    winner_opponent_score: int = 0
    winner_lead_score: int = 0
    rankings: list[CategoryPlayerWin] = Field(default_factory=list)


class PostFinalsCategorySummary(BaseModel):
    final_completed: bool
    final_status: MatchStatus | None = None
    total_matches_considered: int
    medals: MedalSummary
    categories: list[CategoryWinnerSummary] = Field(default_factory=list)


class ViewerDashboard(BaseModel):
    summary: DashboardSummary
    standings: list[StandingRow]

    ties: list[TieRead]
    final_match: FinalMatchRead | None = None
    medals: MedalSummary

    rule_highlights: list[str]
