from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.models.change_log import ChangeLog


def log_change(
    db: Session,
    entity_type: str,
    entity_id: str,
    action: str,
    operator: str,
    field_name: Optional[str] = None,
    old_value: Optional[str] = None,
    new_value: Optional[str] = None,
    comment: Optional[str] = None,
) -> ChangeLog:
    entry = ChangeLog(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        field_name=field_name,
        old_value=old_value,
        new_value=new_value,
        operator=operator or "system",
        comment=comment,
    )
    db.add(entry)
    db.flush()
    return entry
