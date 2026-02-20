from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..database import get_db

router = APIRouter(tags=["teams"])


@router.get("/", response_model=list[schemas.TeamRead])
def list_teams(db: Session = Depends(get_db)) -> list[schemas.TeamRead]:
    return crud.get_teams(db)


@router.post("/", response_model=schemas.TeamRead, status_code=status.HTTP_201_CREATED)
def create_team(team: schemas.TeamCreate, db: Session = Depends(get_db)) -> schemas.TeamRead:
    try:
        return crud.create_team(db, team)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
