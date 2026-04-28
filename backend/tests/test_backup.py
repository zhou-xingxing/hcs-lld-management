from __future__ import annotations

import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

from sqlalchemy.orm import Session

import app.services.backup as backup_service
from app.models.backup import BackupConfig, BackupRecord
from app.models.region import Region
from app.services.backup import calculate_next_run, run_due_backup, utcnow


def test_get_backup_config_creates_default(client, admin_headers):
    response = client.get("/api/backup/config", headers=admin_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["enabled"] is False
    assert data["cron_expression"] == "0 2 * * *"
    assert data["backup_file_prefix"] == "hcs_lld_data_backup_"
    assert data["method"] == "local"
    assert data["secret_key_configured"] is False


def test_update_backup_config(client, tmp_path, admin_headers):
    response = client.put(
        "/api/backup/config",
        headers=admin_headers,
        json={
            "enabled": True,
            "cron_expression": "15 23 * * 5",
            "backup_file_prefix": "lld_backup_",
            "method": "local",
            "local_path": str(tmp_path),
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["enabled"] is True
    assert data["cron_expression"] == "15 23 * * 5"
    assert data["backup_file_prefix"] == "lld_backup_"
    assert data["local_path"] == str(tmp_path)
    assert data["next_run_at"] is not None


def test_update_backup_config_validates_cron_expression(client, tmp_path, admin_headers):
    response = client.put(
        "/api/backup/config",
        headers=admin_headers,
        json={
            "enabled": True,
            "cron_expression": "60 2 * * *",
            "method": "local",
            "local_path": str(tmp_path),
        },
    )

    assert response.status_code == 409
    assert "分钟" in response.json()["detail"]


def test_update_backup_config_validates_backup_file_prefix(client, tmp_path, admin_headers):
    response = client.put(
        "/api/backup/config",
        headers=admin_headers,
        json={
            "enabled": True,
            "cron_expression": "0 2 * * *",
            "backup_file_prefix": "backup/",
            "method": "local",
            "local_path": str(tmp_path),
        },
    )

    assert response.status_code == 409
    assert "路径分隔符" in response.json()["detail"]


def test_update_backup_config_validates_local_path_is_writable(client, tmp_path, admin_headers):
    file_path = tmp_path / "not-a-directory"
    file_path.write_text("occupied")

    response = client.put(
        "/api/backup/config",
        headers=admin_headers,
        json={
            "enabled": True,
            "cron_expression": "0 2 * * *",
            "backup_file_prefix": "backup_",
            "method": "local",
            "local_path": str(file_path),
        },
    )

    assert response.status_code == 409
    assert "本地备份路径不可写" in response.json()["detail"]


def test_update_backup_config_validates_object_storage_target(client, monkeypatch, admin_headers):
    calls = []

    class FakeS3Client:
        def put_object(self, **kwargs):
            calls.append(("put", kwargs))

        def delete_object(self, **kwargs):
            calls.append(("delete", kwargs))

    def fake_client(*args, **kwargs):
        calls.append(("client", kwargs))
        return FakeS3Client()

    monkeypatch.setitem(sys.modules, "boto3", SimpleNamespace(client=fake_client))

    response = client.put(
        "/api/backup/config",
        headers=admin_headers,
        json={
            "enabled": True,
            "cron_expression": "0 2 * * *",
            "backup_file_prefix": "backup_",
            "method": "object_storage",
            "endpoint_url": "https://obs.example.com",
            "access_key": "ak",
            "secret_key": "sk",
            "bucket": "hcs-lld-backup",
            "object_prefix": "hcs-lld",
        },
    )

    assert response.status_code == 200
    assert calls[0] == (
        "client",
        {
            "endpoint_url": "https://obs.example.com",
            "aws_access_key_id": "ak",
            "aws_secret_access_key": "sk",
        },
    )
    assert calls[1][0] == "put"
    assert calls[1][1]["Bucket"] == "hcs-lld-backup"
    assert calls[1][1]["Key"].startswith("hcs-lld/.hcs_lld_backup_probe_")
    assert calls[2][0] == "delete"


def test_update_backup_config_rejects_invalid_object_storage_target(client, monkeypatch, admin_headers):
    class FakeS3Client:
        def put_object(self, **kwargs):
            raise RuntimeError("access denied")

    monkeypatch.setitem(sys.modules, "boto3", SimpleNamespace(client=lambda *args, **kwargs: FakeS3Client()))

    response = client.put(
        "/api/backup/config",
        headers=admin_headers,
        json={
            "enabled": True,
            "cron_expression": "0 2 * * *",
            "backup_file_prefix": "backup_",
            "method": "object_storage",
            "endpoint_url": "https://obs.example.com",
            "access_key": "ak",
            "secret_key": "sk",
            "bucket": "hcs-lld-backup",
        },
    )

    assert response.status_code == 409
    assert "对象存储备份目标校验失败" in response.json()["detail"]


def test_update_backup_config_validates_local_path(client, admin_headers):
    response = client.put(
        "/api/backup/config",
        headers=admin_headers,
        json={
            "enabled": True,
            "cron_expression": "0 2 * * *",
            "method": "local",
            "local_path": "",
        },
    )

    assert response.status_code == 422


def test_run_backup_creates_sqlite_file(client, tmp_path, admin_headers):
    config_response = client.put(
        "/api/backup/config",
        headers=admin_headers,
        json={
            "enabled": False,
            "cron_expression": "30 2 * * *",
            "backup_file_prefix": "lld_",
            "method": "local",
            "local_path": str(tmp_path),
        },
    )
    assert config_response.status_code == 200

    response = client.post("/api/backup/run", headers=admin_headers)

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "success"
    assert data["method"] == "local"
    assert data["file_size"] > 0
    target = Path(data["target"])
    assert target.exists()
    assert target.parent == tmp_path
    assert re.fullmatch(r"lld_\d{14}", target.name)


def test_run_backup_records_object_storage_full_target(client, monkeypatch, admin_headers):
    calls = []

    class FakeS3Client:
        def put_object(self, **kwargs):
            calls.append(("put", kwargs))

        def delete_object(self, **kwargs):
            calls.append(("delete", kwargs))

        def upload_file(self, filename, bucket, key):
            calls.append(("upload", filename, bucket, key))

    monkeypatch.setitem(sys.modules, "boto3", SimpleNamespace(client=lambda *args, **kwargs: FakeS3Client()))
    config_response = client.put(
        "/api/backup/config",
        headers=admin_headers,
        json={
            "enabled": False,
            "cron_expression": "30 2 * * *",
            "backup_file_prefix": "lld_",
            "method": "object_storage",
            "endpoint_url": "https://obs.example.com/",
            "access_key": "ak",
            "secret_key": "sk",
            "bucket": "hcs-lld-backup",
            "object_prefix": "hcs-lld",
        },
    )
    assert config_response.status_code == 200

    response = client.post("/api/backup/run", headers=admin_headers)

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "success"
    assert re.fullmatch(r"https://obs\.example\.com/hcs-lld-backup/hcs-lld/lld_\d{14}", data["target"])
    upload_call = [call for call in calls if call[0] == "upload"][0]
    assert upload_call[2] == "hcs-lld-backup"
    assert re.fullmatch(r"hcs-lld/lld_\d{14}", upload_call[3])


def test_run_backup_records_failed_status_when_backup_creation_fails(client, tmp_path, monkeypatch, admin_headers):
    config_response = client.put(
        "/api/backup/config",
        headers=admin_headers,
        json={
            "enabled": False,
            "cron_expression": "30 2 * * *",
            "backup_file_prefix": "lld_",
            "method": "local",
            "local_path": str(tmp_path),
        },
    )
    assert config_response.status_code == 200

    def fail_create_sqlite_backup(*args, **kwargs):
        raise RuntimeError("disk full")

    monkeypatch.setattr(backup_service, "_create_sqlite_backup", fail_create_sqlite_backup)

    response = client.post("/api/backup/run", headers=admin_headers)

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "failed"
    assert data["error_message"] == "disk full"
    assert data["finished_at"] is not None
    assert data["target"] is None
    assert data["file_size"] is None


def test_list_backup_records(client, tmp_path, admin_headers):
    client.put(
        "/api/backup/config",
        headers=admin_headers,
        json={
            "enabled": False,
            "cron_expression": "30 2 * * *",
            "method": "local",
            "local_path": str(tmp_path),
        },
    )
    client.post("/api/backup/run", headers=admin_headers)

    response = client.get("/api/backup/records", headers=admin_headers)

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
                cron_expression="30 2 * * *",
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

    assert calculate_next_run(before_time, "30 2 * * *") == datetime(2026, 4, 25, 18, 30, tzinfo=timezone.utc)
    assert calculate_next_run(after_time, "30 2 * * *") == datetime(2026, 4, 26, 18, 30, tzinfo=timezone.utc)


def test_calculate_next_run_weekly_uses_weekday_and_time():
    sunday_before_time = datetime(2026, 4, 25, 18, 10, tzinfo=timezone.utc)
    sunday_after_time = datetime(2026, 4, 25, 19, 10, tzinfo=timezone.utc)

    assert calculate_next_run(sunday_before_time, "30 2 * * 0") == datetime(2026, 4, 25, 18, 30, tzinfo=timezone.utc)
    assert calculate_next_run(sunday_after_time, "30 2 * * 7") == datetime(2026, 5, 2, 18, 30, tzinfo=timezone.utc)
    assert calculate_next_run(sunday_after_time, "30 2 * * 1") == datetime(2026, 4, 26, 18, 30, tzinfo=timezone.utc)


def test_calculate_next_run_supports_steps_ranges_and_lists():
    base_time = datetime(2026, 4, 25, 18, 10, tzinfo=timezone.utc)

    assert calculate_next_run(base_time, "*/15 2-4 * * 0,1") == datetime(
        2026, 4, 25, 18, 15, tzinfo=timezone.utc
    )


def test_calculate_next_run_uses_cron_day_or_weekday_semantics():
    base_time = datetime(2026, 4, 30, 18, 10, tzinfo=timezone.utc)

    assert calculate_next_run(base_time, "30 2 2 * 1") == datetime(2026, 5, 1, 18, 30, tzinfo=timezone.utc)
