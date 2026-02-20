from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from .. import crud, schemas, serializers
from ..database import get_db

router = APIRouter(tags=["matches"])


@router.get("/", response_model=list[schemas.MatchRead])
def list_matches(
    stage: Literal["tie"] | None = Query(default=None),
    status_filter: Literal["pending", "live", "completed"] | None = Query(default=None, alias="status"),
    tie_id: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
) -> list[schemas.MatchRead]:
    matches = crud.list_matches(db, stage=stage, status=status_filter, tie_id=tie_id)
    return [serializers.match_to_read(match) for match in matches]


@router.patch("/{match_id}/score", response_model=schemas.MatchRead)
def update_score_patch(
    match_id: int,
    payload: schemas.ScoreUpdate,
    db: Session = Depends(get_db),
) -> schemas.MatchRead:
    try:
        match = crud.update_score(db, match_id, payload.score1, payload.score2)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return serializers.match_to_read(match)


@router.post("/score/{match_id}", response_model=schemas.MatchRead)
def update_score_legacy(
    match_id: int,
    payload: schemas.ScoreUpdate,
    db: Session = Depends(get_db),
) -> schemas.MatchRead:
    return update_score_patch(match_id=match_id, payload=payload, db=db)


@router.post("/{match_id}", response_model=schemas.MatchRead)
def update_score_query(
    match_id: int,
    s1: int = Query(ge=0, le=30),
    s2: int = Query(ge=0, le=30),
    db: Session = Depends(get_db),
) -> schemas.MatchRead:
    payload = schemas.ScoreUpdate(score1=s1, score2=s2)
    return update_score_patch(match_id=match_id, payload=payload, db=db)


@router.patch("/{match_id}/lineup", response_model=schemas.MatchRead)
def update_lineup_patch(
    match_id: int,
    payload: schemas.LineupUpdate,
    db: Session = Depends(get_db),
) -> schemas.MatchRead:
    try:
        match = crud.update_lineups(
            db,
            match_id=match_id,
            team1_lineup=payload.team1_lineup,
            team2_lineup=payload.team2_lineup,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return serializers.match_to_read(match)


@router.patch("/{match_id}/status", response_model=schemas.MatchRead)
def update_status_patch(
    match_id: int,
    payload: schemas.MatchStatusUpdate,
    db: Session = Depends(get_db),
) -> schemas.MatchRead:
    try:
        match = crud.update_match_status(db, match_id=match_id, status=payload.status)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return serializers.match_to_read(match)
