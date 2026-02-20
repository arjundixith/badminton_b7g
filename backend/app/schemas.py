from pydantic import BaseModel, Field

try:
    from pydantic import ConfigDict

    class ORMBaseModel(BaseModel):
        model_config = ConfigDict(from_attributes=True)

except ImportError:

    class ORMBaseModel(BaseModel):
        class Config:
            orm_mode = True


class TeamCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)


class TeamRead(ORMBaseModel):
    id: int
    name: str


class PlayerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    category: str = Field(min_length=1, max_length=32)
    team_id: int = Field(gt=0)


class PlayerRead(ORMBaseModel):
    id: int
    name: str
    category: str
    team_id: int


class ScoreUpdate(BaseModel):
    score1: int = Field(ge=0, le=30)
    score2: int = Field(ge=0, le=30)


class RefereeRead(ORMBaseModel):
    id: int
    name: str


class MatchRead(ORMBaseModel):
    id: int
    tie_id: int
    match_no: int
    day: int | None = None
    session: str | None = None
    court: int | None = None
    time: str | None = None
    team1: str
    team2: str
    team1_score: int
    team2_score: int
    referee_id: int | None = None
    winner_side: int | None = None


class TieRead(ORMBaseModel):
    id: int
    team1_id: int
    team2_id: int
    team1: str
    team2: str
    score1: int
    score2: int
    winner_team_id: int | None = None


class RefereeAssignmentResponse(BaseModel):
    referee: RefereeRead
    match: MatchRead


class ScheduleMatch(BaseModel):
    id: int
    match_no: int
    court: int | None = None
    time: str | None = None
    team1: str
    team2: str
    score1: int
    score2: int
