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
    """记录一条变更日志。

    Args:
        db: 数据库会话。
        entity_type: 实体类型（如 region、region_network_plane）。
        entity_id: 实体 ID。
        action: 操作类型（create、update、delete、import）。
        operator: 操作者名称。
        field_name: 变更的字段名（update 操作时）。
        old_value: 变更前的值。
        new_value: 变更后的值。
        comment: 备注说明。

    Returns:
        新创建的 ChangeLog 记录。
    """
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
