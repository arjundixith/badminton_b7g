from sqlalchemy import Boolean, CheckConstraint, Column, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from .database import Base


class Team(Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)

    players = relationship("Player", back_populates="team", cascade="all, delete-orphan")

    home_ties = relationship("Tie", foreign_keys="Tie.team1_id", back_populates="team1")
    away_ties = relationship("Tie", foreign_keys="Tie.team2_id", back_populates="team2")
    won_ties = relationship("Tie", foreign_keys="Tie.winner_team_id", back_populates="winner_team")

    matches_as_team1 = relationship(
        "Match",
        foreign_keys="Match.team1_id",
        back_populates="team1",
    )
    matches_as_team2 = relationship(
        "Match",
        foreign_keys="Match.team2_id",
        back_populates="team2",
    )


class Player(Base):
    __tablename__ = "players"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    set_level = Column(String(16), nullable=False, index=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False, index=True)

    team = relationship("Team", back_populates="players")

    __table_args__ = (
        UniqueConstraint("name", "team_id", name="uq_player_name_team"),
        CheckConstraint(
            "set_level in ('Set-1', 'Set-2', 'Set-3', 'Set-4', 'Set-5')",
            name="ck_player_set_level_valid",
        ),
    )


class Tie(Base):
    __tablename__ = "ties"

    id = Column(Integer, primary_key=True, index=True)
    tie_no = Column(Integer, unique=True, nullable=False, index=True)

    day = Column(Integer, nullable=False)
    session = Column(String(32), nullable=False)
    court = Column(Integer, nullable=False)

    team1_id = Column(Integer, ForeignKey("teams.id"), nullable=False, index=True)
    team2_id = Column(Integer, ForeignKey("teams.id"), nullable=False, index=True)

    score1 = Column(Integer, default=0, nullable=False)
    score2 = Column(Integer, default=0, nullable=False)
    status = Column(String(16), default="pending", nullable=False, index=True)

    winner_team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)

    team1 = relationship("Team", foreign_keys=[team1_id], back_populates="home_ties")
    team2 = relationship("Team", foreign_keys=[team2_id], back_populates="away_ties")
    winner_team = relationship("Team", foreign_keys=[winner_team_id], back_populates="won_ties")

    matches = relationship("Match", back_populates="tie", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("team1_id <> team2_id", name="ck_tie_distinct_teams"),
        CheckConstraint("score1 >= 0", name="ck_tie_score1_nonnegative"),
        CheckConstraint("score2 >= 0", name="ck_tie_score2_nonnegative"),
        CheckConstraint(
            "status in ('pending', 'live', 'completed')",
            name="ck_tie_status_valid",
        ),
    )


class Referee(Base):
    __tablename__ = "referees"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)

    matches = relationship("Match", back_populates="referee")


class Match(Base):
    __tablename__ = "matches"

    id = Column(Integer, primary_key=True, index=True)

    stage = Column(String(16), default="tie", nullable=False, index=True)
    status = Column(String(16), default="pending", nullable=False, index=True)

    tie_id = Column(Integer, ForeignKey("ties.id"), nullable=True, index=True)
    match_no = Column(Integer, nullable=False)

    discipline = Column(String(64), nullable=False)

    team1_id = Column(Integer, ForeignKey("teams.id"), nullable=False, index=True)
    team2_id = Column(Integer, ForeignKey("teams.id"), nullable=False, index=True)

    team1_lineup = Column(String(255), nullable=False)
    team2_lineup = Column(String(255), nullable=False)
    lineup_confirmed = Column(Boolean, default=False, nullable=False)

    day = Column(Integer, nullable=False)
    session = Column(String(32), nullable=False)
    court = Column(Integer, nullable=False)
    time = Column(String(16), nullable=False)

    team1_score = Column(Integer, default=0, nullable=False)
    team2_score = Column(Integer, default=0, nullable=False)

    referee_id = Column(Integer, ForeignKey("referees.id"), nullable=True, index=True)
    winner_side = Column(Integer, nullable=True)

    tie = relationship("Tie", back_populates="matches")
    team1 = relationship("Team", foreign_keys=[team1_id], back_populates="matches_as_team1")
    team2 = relationship("Team", foreign_keys=[team2_id], back_populates="matches_as_team2")
    referee = relationship("Referee", back_populates="matches")

    __table_args__ = (
        UniqueConstraint("tie_id", "match_no", name="uq_tie_match_no"),
        CheckConstraint("team1_score >= 0", name="ck_match_team1_score_nonnegative"),
        CheckConstraint("team2_score >= 0", name="ck_match_team2_score_nonnegative"),
        CheckConstraint("winner_side in (1, 2) or winner_side is null", name="ck_winner_side_valid"),
        CheckConstraint("stage = 'tie'", name="ck_stage_valid"),
        CheckConstraint("status in ('pending', 'live', 'completed')", name="ck_match_status_valid"),
        CheckConstraint("team1_id <> team2_id", name="ck_match_distinct_teams"),
        CheckConstraint("tie_id is not null", name="ck_stage_tie_link"),
    )


class FinalMatch(Base):
    __tablename__ = "final_matches"

    id = Column(Integer, primary_key=True, index=True)
    status = Column(String(16), default="pending", nullable=False, index=True)

    team1_id = Column(Integer, ForeignKey("teams.id"), nullable=False, index=True)
    team2_id = Column(Integer, ForeignKey("teams.id"), nullable=False, index=True)
    winner_team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)

    # Aggregate final-tie score at game level (e.g., 7-5 after 12 games).
    team1_score = Column(Integer, default=0, nullable=False)
    team2_score = Column(Integer, default=0, nullable=False)

    team1 = relationship("Team", foreign_keys=[team1_id])
    team2 = relationship("Team", foreign_keys=[team2_id])
    winner_team = relationship("Team", foreign_keys=[winner_team_id])
    matches = relationship("FinalGame", back_populates="final_match", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("status in ('pending', 'live', 'completed')", name="ck_final_status_valid"),
        CheckConstraint("team1_id <> team2_id", name="ck_final_distinct_teams"),
        CheckConstraint("team1_score >= 0", name="ck_final_team1_score_nonnegative"),
        CheckConstraint("team2_score >= 0", name="ck_final_team2_score_nonnegative"),
    )


class FinalGame(Base):
    __tablename__ = "final_games"

    id = Column(Integer, primary_key=True, index=True)
    final_match_id = Column(Integer, ForeignKey("final_matches.id"), nullable=False, index=True)

    match_no = Column(Integer, nullable=False)
    discipline = Column(String(64), nullable=False)
    status = Column(String(16), default="pending", nullable=False, index=True)

    team1_lineup = Column(String(255), nullable=False)
    team2_lineup = Column(String(255), nullable=False)
    lineup_confirmed = Column(Boolean, default=True, nullable=False)

    team1_score = Column(Integer, default=0, nullable=False)
    team2_score = Column(Integer, default=0, nullable=False)
    winner_side = Column(Integer, nullable=True)
    referee_id = Column(Integer, ForeignKey("referees.id"), nullable=True, index=True)

    final_match = relationship("FinalMatch", back_populates="matches")
    referee = relationship("Referee")

    __table_args__ = (
        UniqueConstraint("final_match_id", "match_no", name="uq_final_match_no"),
        CheckConstraint("match_no >= 1 and match_no <= 12", name="ck_final_match_no_range"),
        CheckConstraint("status in ('pending', 'live', 'completed')", name="ck_final_game_status_valid"),
        CheckConstraint("team1_score >= 0", name="ck_final_game_team1_score_nonnegative"),
        CheckConstraint("team2_score >= 0", name="ck_final_game_team2_score_nonnegative"),
        CheckConstraint("winner_side in (1, 2) or winner_side is null", name="ck_final_game_winner_side_valid"),
    )
