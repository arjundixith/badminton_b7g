from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from .. import crud, schemas, serializers
from ..database import get_db

router = APIRouter(tags=["referees"])


@router.post("/assign", response_model=schemas.RefereeAssignmentResponse)
def assign_referee(
    match_id: int = Query(gt=0),
    name: str = Query(min_length=1, max_length=100),
    db: Session = Depends(get_db),
) -> schemas.RefereeAssignmentResponse:
    try:
        referee, match = crud.assign_referee(db, match_id=match_id, name=name)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return schemas.RefereeAssignmentResponse(
        referee=schemas.RefereeRead(id=referee.id, name=referee.name),
        match=serializers.match_to_read(match),
    )
