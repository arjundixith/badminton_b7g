from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from .. import crud, schemas, serializers
from ..database import get_db

router = APIRouter(tags=["finals"])


@router.get("/", response_model=schemas.FinalMatchRead | None)
def get_final_match(db: Session = Depends(get_db)) -> schemas.FinalMatchRead | None:
    final_match = crud.get_or_sync_final_match(db)
    if final_match is None:
        return None
    return serializers.final_match_to_read(final_match)


@router.post("/assign", response_model=schemas.FinalMatchRead)
def assign_final_referee(
    name: str = Query(min_length=1, max_length=100),
    db: Session = Depends(get_db),
) -> schemas.FinalMatchRead:
    try:
        final_match = crud.assign_final_referee(db, name=name)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return serializers.final_match_to_read(final_match)


@router.post("/score", response_model=schemas.FinalMatchRead)
def update_final_score(
    payload: schemas.ScoreUpdate,
    db: Session = Depends(get_db),
) -> schemas.FinalMatchRead:
    try:
        final_match = crud.update_final_score(db, payload.score1, payload.score2)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return serializers.final_match_to_read(final_match)


@router.post("/games/{game_id}/assign", response_model=schemas.FinalMatchRead)
def assign_final_game_referee(
    game_id: int,
    name: str = Query(min_length=1, max_length=100),
    db: Session = Depends(get_db),
) -> schemas.FinalMatchRead:
    try:
        final_match = crud.assign_final_game_referee(db, game_id=game_id, name=name)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return serializers.final_match_to_read(final_match)


@router.post("/games/{game_id}/score", response_model=schemas.FinalMatchRead)
def update_final_game_score(
    game_id: int,
    payload: schemas.ScoreUpdate,
    db: Session = Depends(get_db),
) -> schemas.FinalMatchRead:
    try:
        final_match = crud.update_final_game_score(db, game_id=game_id, score1=payload.score1, score2=payload.score2)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return serializers.final_match_to_read(final_match)
