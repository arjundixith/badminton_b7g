"""Legacy compatibility endpoint.

Older frontend versions expected `GET /matches` via this module. We keep it to
avoid import errors if stale references exist, while the primary route lives in
`routes/matches.py`.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import crud, schemas, serializers
from ..database import get_db

router = APIRouter(tags=["matches"])


@router.get("/", response_model=list[schemas.MatchRead])
def list_matches(db: Session = Depends(get_db)) -> list[schemas.MatchRead]:
    matches = crud.list_matches(db)
    return [serializers.match_to_read(match) for match in matches]
