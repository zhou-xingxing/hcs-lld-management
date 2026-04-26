from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.backup import BackupConfig, BackupRecord
from app.models.region import Region
from app.services.backup import calculate_next_run, run_due_backup, utcnow


def test_get_backup_config_creates_default(client):
    response = client.get("/api/backup/config")

    assert response.status_code == 200
    data = response.json()
    assert data["enabled"] is False
    assert data["frequency"] == "daily"
    assert data["method"] == "local"
    assert data["secret_key_configured"] is False


def test_update_backup_config(client, tmp_path, operator):
    response = client.put(
        "/api/backup/config",
        headers={"X-Operator": operator},
        json={
            "enabled": True,
            "frequency": "weekly",
            "schedule_hour": 23,
            "schedule_minute": 15,
            "schedule_weekday": 5,
            "method": "local",
            "local_path": str(tmp_path),
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["enabled"] is True
    assert data["frequency"] == "weekly"
    assert data["schedule_hour"] == 23
    assert data["schedule_minute"] == 15
    assert data["schedule_weekday"] == 5
    assert data["local_path"] == str(tmp_path)
    assert data["next_run_at"] is not None


def test_update_backup_config_validates_local_path(client):
    response = client.put(
        "/api/backup/config",
        json={
            "enabled": True,
            "frequency": "daily",
            "method": "local",
            "local_path": "",
        },
    )

    assert response.status_code == 422


def test_run_backup_creates_sqlite_file(client, tmp_path, operator):
    config_response = client.put(
        "/api/backup/config",
        headers={"X-Operator": operator},
        json={
            "enabled": False,
            "frequency": "daily",
            "schedule_hour": 2,
            "schedule_minute": 30,
            "method": "local",
            "local_path": str(tmp_path),
        },
    )
    assert config_response.status_code == 200

    response = client.post("/api/backup/run", headers={"X-Operator": operator})

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "success"
    assert data["method"] == "local"
    assert data["file_size"] > 0
    target = Path(data["target"])
    assert target.exists()
    assert target.parent == tmp_path
    assert target.name.startswith("hcs_lld_data_backup_")
    assert target.suffix == ".sqlite"


def test_list_backup_records(client, tmp_path, operator):
    client.put(
        "/api/backup/config",
        headers={"X-Operator": operator},
        json={
            "enabled": False,
            "frequency": "daily",
            "schedule_hour": 2,
            "schedule_minute": 30,
            "method": "local",
            "local_path": str(tmp_path),
        },
    )
    client.post("/api/backup/run", headers={"X-Operator": operator})

    response = client.get("/api/backup/records")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["status"] == "success"


def test_run_due_backup_only_when_enabled_and_due(test_db, tmp_path):
    session = Session(test_db)
    try:
        session.add(Region(name="cn-north-1", description="北京"))
        session.add(
            BackupConfig(
                enabled=True,
                frequency="daily",
                schedule_hour=2,
                schedule_minute=30,
                method="local",
                local_path=str(tmp_path),
                next_run_at=utcnow() - timedelta(minutes=1),
            )
        )
        session.commit()

        record = run_due_backup(session)
        session.commit()

        assert record is not None
        assert record.status == "success"
        assert session.query(BackupRecord).count() == 1
    finally:
        session.close()


def test_calculate_next_run_daily_uses_configured_time():
    before_time = datetime(2026, 4, 25, 18, 10, tzinfo=timezone.utc)
    after_time = datetime(2026, 4, 25, 19, 10, tzinfo=timezone.utc)

    assert calculate_next_run(before_time, "daily", 2, 30) == datetime(2026, 4, 25, 18, 30, tzinfo=timezone.utc)
    assert calculate_next_run(after_time, "daily", 2, 30) == datetime(2026, 4, 26, 18, 30, tzinfo=timezone.utc)


def test_calculate_next_run_weekly_uses_weekday_and_time():
    sunday_before_time = datetime(2026, 4, 25, 18, 10, tzinfo=timezone.utc)
    sunday_after_time = datetime(2026, 4, 25, 19, 10, tzinfo=timezone.utc)

    assert calculate_next_run(sunday_before_time, "weekly", 2, 30, 7) == datetime(
        2026, 4, 25, 18, 30, tzinfo=timezone.utc
    )
    assert calculate_next_run(sunday_after_time, "weekly", 2, 30, 7) == datetime(
        2026, 5, 2, 18, 30, tzinfo=timezone.utc
    )
    assert calculate_next_run(sunday_after_time, "weekly", 2, 30, 1) == datetime(
        2026, 4, 26, 18, 30, tzinfo=timezone.utc
    )
