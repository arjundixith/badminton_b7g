from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import crud, serializers
from ..database import get_db

router = APIRouter(tags=["schedule"])


@router.get("/")
def get_schedule(db: Session = Depends(get_db)) -> dict[str, dict[str, list[dict[str, object]]]]:
    matches = crud.list_matches(db)

    schedule: dict[str, dict[str, list[dict[str, object]]]] = {}
    for match in matches:
        day_key = str(match.day)
        session_key = match.session

        payload = serializers.model_dump_compat(serializers.match_to_read(match))

        schedule.setdefault(day_key, {}).setdefault(session_key, []).append(payload)

    return schedule
