"""Compatibility router kept for older imports.

This module intentionally mirrors `/matches` list behavior so existing references
continue to work, but the primary implementation lives in `routes/matches.py`.
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
