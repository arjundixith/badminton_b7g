from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import crud, schemas, serializers
from ..database import get_db

router = APIRouter(tags=["ties"])


@router.get("/", response_model=list[schemas.TieRead])
def list_ties(db: Session = Depends(get_db)) -> list[schemas.TieRead]:
    ties = crud.get_ties(db)
    return [serializers.tie_to_read(tie) for tie in ties]


@router.get("/{tie_id}/matches", response_model=list[schemas.MatchRead])
def list_tie_matches(tie_id: int, db: Session = Depends(get_db)) -> list[schemas.MatchRead]:
    try:
        matches = crud.list_matches_by_tie(db, tie_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return [serializers.match_to_read(match) for match in matches]
