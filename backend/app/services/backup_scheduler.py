from __future__ import annotations

import logging
import threading
from types import TracebackType

from app.config import settings
from app.database import SessionLocal
from app.services.backup import run_due_backup

logger = logging.getLogger(__name__)


class BackupScheduler:
    """轻量级备份调度器。

    使用后台线程定期检查全局备份配置是否到期。当前项目是单进程
    SQLite MVP，避免引入额外调度依赖可以让部署保持简单。
    """

    def __init__(self, interval_seconds: int) -> None:
        self.interval_seconds = interval_seconds
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        """启动后台调度线程。"""
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, name="backup-scheduler", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """停止后台调度线程。"""
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)

    def _run_loop(self) -> None:
        while not self._stop_event.wait(self.interval_seconds):
            db = SessionLocal()
            try:
                record = run_due_backup(db)
                if record:
                    db.commit()
            except Exception:
                db.rollback()
                logger.exception("Scheduled backup check failed")
            finally:
                db.close()

    def __enter__(self) -> "BackupScheduler":
        self.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.stop()


backup_scheduler = BackupScheduler(settings.BACKUP_SCHEDULER_INTERVAL_SECONDS)
