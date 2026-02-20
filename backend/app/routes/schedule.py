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
        day_key = str(match.day) if match.day is not None else "unscheduled"
        session_key = match.session or "unscheduled"

        schedule_item = serializers.match_to_schedule_item(match)
        payload = (
            schedule_item.model_dump()
            if hasattr(schedule_item, "model_dump")
            else schedule_item.dict()
        )

        schedule.setdefault(day_key, {}).setdefault(session_key, []).append(payload)

    return schedule
