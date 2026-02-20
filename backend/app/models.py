from sqlalchemy import CheckConstraint, Column, ForeignKey, Integer, String, UniqueConstraint
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


class Player(Base):
    __tablename__ = "players"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    category = Column(String(32), nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False, index=True)

    team = relationship("Team", back_populates="players")

    __table_args__ = (UniqueConstraint("name", "team_id", name="uq_player_name_team"),)


class Tie(Base):
    __tablename__ = "ties"

    id = Column(Integer, primary_key=True, index=True)
    team1_id = Column(Integer, ForeignKey("teams.id"), nullable=False, index=True)
    team2_id = Column(Integer, ForeignKey("teams.id"), nullable=False, index=True)
    score1 = Column(Integer, default=0, nullable=False)
    score2 = Column(Integer, default=0, nullable=False)
    winner_team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)

    team1 = relationship("Team", foreign_keys=[team1_id], back_populates="home_ties")
    team2 = relationship("Team", foreign_keys=[team2_id], back_populates="away_ties")
    winner_team = relationship("Team", foreign_keys=[winner_team_id], back_populates="won_ties")
    matches = relationship("Match", back_populates="tie", cascade="all, delete-orphan")

    __table_args__ = (CheckConstraint("team1_id <> team2_id", name="ck_tie_distinct_teams"),)


class Referee(Base):
    __tablename__ = "referees"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)

    matches = relationship("Match", back_populates="referee")


class Match(Base):
    __tablename__ = "matches"

    id = Column(Integer, primary_key=True, index=True)
    tie_id = Column(Integer, ForeignKey("ties.id"), nullable=False, index=True)
    match_no = Column(Integer, nullable=False)

    day = Column(Integer, nullable=True)
    session = Column(String(32), nullable=True)
    court = Column(Integer, nullable=True)
    time = Column(String(16), nullable=True)

    team1_score = Column(Integer, default=0, nullable=False)
    team2_score = Column(Integer, default=0, nullable=False)
    referee_id = Column(Integer, ForeignKey("referees.id"), nullable=True)
    winner_side = Column(Integer, nullable=True)

    tie = relationship("Tie", back_populates="matches")
    referee = relationship("Referee", back_populates="matches")

    __table_args__ = (
        UniqueConstraint("tie_id", "match_no", name="uq_tie_match_no"),
        CheckConstraint("team1_score >= 0", name="ck_match_team1_score_nonnegative"),
        CheckConstraint("team2_score >= 0", name="ck_match_team2_score_nonnegative"),
        CheckConstraint("winner_side in (1, 2) or winner_side is null", name="ck_winner_side_valid"),
    )
