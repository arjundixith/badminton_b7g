from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..database import get_db

router = APIRouter(tags=["viewer"])


@router.get("/dashboard", response_model=schemas.ViewerDashboard)
def viewer_dashboard(db: Session = Depends(get_db)) -> schemas.ViewerDashboard:
    return crud.build_viewer_dashboard(db)


@router.get("/standings", response_model=list[schemas.StandingRow])
def standings(db: Session = Depends(get_db)) -> list[schemas.StandingRow]:
    return crud.build_standings(db)
