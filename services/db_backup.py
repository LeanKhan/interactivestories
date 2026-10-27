"""
SQLite Backups to Azure Blob Storage

Restores the database from the newest backup when the local file is missing,
and uploads a fresh backup after every commit that changes data.
"""

import os
import sqlite3
import tempfile
import threading
from datetime import datetime, timezone

from sqlalchemy import event
from sqlalchemy.orm import Session


class DatabaseBackup:
    """Back up and restore a SQLite file using an AzureBlobStorage service"""

    def __init__(self, storage, db_path, folder='backups', keep=10, logger=None):
        """
        Args:
            storage: AzureBlobStorage instance (should use a private container)
            db_path: Local path of the SQLite file
            folder: Blob folder/prefix for backups
            keep: Number of most recent backups to keep
            logger: Optional logger for errors
        """
        self.storage = storage
        self.db_path = db_path
        self.folder = folder
        self.keep = keep
        self.logger = logger

        self._lock = threading.Lock()
        self._running = False
        self._pending = False

    def restore_latest(self):
        """
        Download the newest backup if there is no local database

        Returns:
            str: Name of the restored blob, or None if nothing was restored
        """
        if os.path.exists(self.db_path):
            return None

        backups = self._list_backups()
        if not backups:
            return None

        latest = backups[-1]
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        # Download beside the target and swap in, so a failed download never leaves a partial file
        tmp_path = self.db_path + '.download'
        self.storage.download_file(latest, tmp_path)
        os.replace(tmp_path, self.db_path)
        return latest

    def backup(self):
        """
        Upload a consistent snapshot of the database, then prune old backups

        Returns:
            str: Name of the new blob, or None if there is no database yet
        """
        if not os.path.exists(self.db_path):
            return None

        fd, snapshot_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)

        try:
            # sqlite3's backup API copies safely even while other connections are writing
            source = sqlite3.connect(self.db_path)
            snapshot = sqlite3.connect(snapshot_path)
            with snapshot:
                source.backup(snapshot)
            source.close()
            snapshot.close()

            # Timestamped names sort oldest -> newest
            filename = f"stories-{datetime.now(timezone.utc):%Y%m%dT%H%M%S%fZ}.db"
            with open(snapshot_path, 'rb') as f:
                result = self.storage.upload_file(f, folder=self.folder, filename=filename)
        finally:
            os.remove(snapshot_path)

        self.prune()
        return result['blob_name']

    def prune(self):
        """Delete all but the newest `keep` backups"""
        for blob_name in self._list_backups()[:-self.keep]:
            self.storage.delete_blob(blob_name)

    def watch_commits(self):
        """Back up in the background after any session commit that changed data"""

        @event.listens_for(Session, 'after_flush')
        def _mark_dirty(session, flush_context):
            session.info['needs_backup'] = True

        @event.listens_for(Session, 'after_rollback')
        def _clear_dirty(session):
            session.info.pop('needs_backup', None)

        @event.listens_for(Session, 'after_commit')
        def _backup_if_dirty(session):
            if session.info.pop('needs_backup', False):
                self._schedule()

    def _schedule(self):
        # Coalesce: while a backup is running, further commits just request one more run
        with self._lock:
            if self._running:
                self._pending = True
                return
            self._running = True

        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        while True:
            try:
                self.backup()
            except Exception:
                if self.logger:
                    self.logger.exception('Database backup failed')

            with self._lock:
                if not self._pending:
                    self._running = False
                    return
                self._pending = False

    def _list_backups(self):
        return sorted(self.storage.list_blobs(prefix=f"{self.folder}/"))
