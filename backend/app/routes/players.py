from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..database import get_db

router = APIRouter(tags=["players"])


@router.get("/", response_model=list[schemas.PlayerRead])
def list_players(db: Session = Depends(get_db)) -> list[schemas.PlayerRead]:
    return crud.get_players(db)


@router.post("/", response_model=schemas.PlayerRead, status_code=status.HTTP_201_CREATED)
def create_player(player: schemas.PlayerCreate, db: Session = Depends(get_db)) -> schemas.PlayerRead:
    try:
        return crud.create_player(db, player)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
