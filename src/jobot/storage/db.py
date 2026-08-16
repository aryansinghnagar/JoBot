from datetime import datetime
import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional
from jobot.models.domain import Application, ApplicationStatus, Goal, JobPosting, Task, TaskStatus, TrustLevel


class DuplicateApplicationError(Exception):
    """Raised when an application with the same idempotency_key already exists."""
    pass


class DatabaseManager:
    """
    SQLite Control Plane Database Manager (Layer A).
    Configures WAL mode and 0600 file permissions for security.
    """

    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            home_dir = Path.home() / ".jobot" / "db"
            home_dir.mkdir(parents=True, exist_ok=True)
            db_path = home_dir / "jobot.db"
        self.db_path = db_path
        self._init_db()

    @contextmanager
    def _get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        # Enable WAL mode and foreign keys
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_db(self) -> None:
        # Enforce 0600 file permissions on POSIX systems
        if os.name == "posix" and self.db_path.exists():
            os.chmod(self.db_path, 0o600)

        with self._get_connection() as conn:
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS goals (
                goal_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY,
                goal_id TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                dependencies TEXT, -- JSON array
                status TEXT NOT NULL,
                assigned_worker TEXT,
                created_at TEXT NOT NULL,
                completed_at TEXT,
                FOREIGN KEY (goal_id) REFERENCES goals (goal_id)
            );

            CREATE TABLE IF NOT EXISTS job_postings (
                job_id TEXT PRIMARY KEY,
                site TEXT NOT NULL,
                url TEXT NOT NULL,
                title TEXT NOT NULL,
                company TEXT NOT NULL,
                location TEXT,
                description TEXT,
                parsed_skills TEXT, -- JSON array
                discovered_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS applications (
                application_id TEXT PRIMARY KEY,
                job_id TEXT NOT NULL,
                site TEXT NOT NULL,
                profile_id TEXT NOT NULL,
                status TEXT NOT NULL,
                idempotency_key TEXT UNIQUE NOT NULL,
                trust_level TEXT NOT NULL,
                form_values TEXT, -- JSON object
                error_message TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (job_id) REFERENCES job_postings (job_id)
            );
            """)

    # -------------------------------------------------------------------
    # JobPosting Operations
    # -------------------------------------------------------------------

    def save_job_posting(self, job: JobPosting) -> None:
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO job_postings
                (job_id, site, url, title, company, location, description, parsed_skills, discovered_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job.job_id,
                    job.site,
                    job.url,
                    job.title,
                    job.company,
                    job.location,
                    job.description,
                    json.dumps(job.parsed_skills),
                    job.discovered_at.isoformat(),
                ),
            )

    def get_job_posting(self, job_id: str) -> Optional[JobPosting]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM job_postings WHERE job_id = ?", (job_id,)).fetchone()
            if not row:
                return None
            return JobPosting(
                job_id=row["job_id"],
                site=row["site"],
                url=row["url"],
                title=row["title"],
                company=row["company"],
                location=row["location"] or "",
                description=row["description"] or "",
                parsed_skills=json.loads(row["parsed_skills"] or "[]"),
                discovered_at=row["discovered_at"],
            )

    # -------------------------------------------------------------------
    # Application Operations
    # -------------------------------------------------------------------

    def get_application_by_idempotency_key(self, idempotency_key: str) -> Optional[Application]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM applications WHERE idempotency_key = ?", (idempotency_key,)).fetchone()
            if not row:
                return None
            return Application(
                application_id=row["application_id"],
                job_id=row["job_id"],
                site=row["site"],
                profile_id=row["profile_id"],
                status=ApplicationStatus(row["status"]),
                idempotency_key=row["idempotency_key"],
                trust_level=TrustLevel(row["trust_level"]),
                form_values=json.loads(row["form_values"]) if row["form_values"] else {},
                error_message=row["error_message"],
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
            )

    def application_exists(self, idempotency_key: str) -> bool:
        return self.get_application_by_idempotency_key(idempotency_key) is not None

    def save_application(self, app: Application) -> None:
        existing = self.get_application(app.application_id)
        with self._get_connection() as conn:
            if existing:
                conn.execute(
                    """
                    UPDATE applications
                    SET job_id = ?, site = ?, profile_id = ?, status = ?, trust_level = ?, form_values = ?, error_message = ?, updated_at = ?
                    WHERE application_id = ?
                    """,
                    (
                        app.job_id,
                        app.site,
                        app.profile_id,
                        app.status.value,
                        app.trust_level.value,
                        json.dumps(app.form_values),
                        app.error_message,
                        app.updated_at.isoformat(),
                        app.application_id,
                    ),
                )
            else:
                try:
                    conn.execute(
                        """
                        INSERT INTO applications
                        (application_id, job_id, site, profile_id, status, idempotency_key, trust_level, form_values, error_message, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            app.application_id,
                            app.job_id,
                            app.site,
                            app.profile_id,
                            app.status.value,
                            app.idempotency_key,
                            app.trust_level.value,
                            json.dumps(app.form_values),
                            app.error_message,
                            app.created_at.isoformat(),
                            app.updated_at.isoformat(),
                        ),
                    )
                except sqlite3.IntegrityError as err:
                    if "idempotency_key" in str(err):
                        raise DuplicateApplicationError(
                            f"Application already exists for idempotency_key={app.idempotency_key}"
                        ) from err
                    raise

    def get_application(self, application_id: str) -> Optional[Application]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM applications WHERE application_id = ?", (application_id,)).fetchone()
            if not row:
                return None
            return Application(
                application_id=row["application_id"],
                job_id=row["job_id"],
                site=row["site"],
                profile_id=row["profile_id"],
                status=ApplicationStatus(row["status"]),
                idempotency_key=row["idempotency_key"],
                trust_level=row["trust_level"],
                form_values=json.loads(row["form_values"] or "{}"),
                error_message=row["error_message"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )

    def list_applications(self, limit: int = 50) -> List[Application]:
        with self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM applications ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
            apps = []
            for row in rows:
                apps.append(
                    Application(
                        application_id=row["application_id"],
                        job_id=row["job_id"],
                        site=row["site"],
                        profile_id=row["profile_id"],
                        status=ApplicationStatus(row["status"]),
                        idempotency_key=row["idempotency_key"],
                        trust_level=row["trust_level"],
                        form_values=json.loads(row["form_values"] or "{}"),
                        error_message=row["error_message"],
                        created_at=row["created_at"],
                        updated_at=row["updated_at"],
                    )
                )
            return apps
