from datetime import datetime, timezone
import json
import logging
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Generator, Iterator, List, Optional
from jobot.models.domain import (
    AnswerBankRecord,
    Application,
    ApplicationStatus,
    CandidateFact,
    FormFieldMemoryRecord,
    JobPosting,
    TrustLevel,
)

logger = logging.getLogger(__name__)


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
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        # Enable WAL mode, normal synchronous, foreign keys, and high-performance memory pragmas
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        conn.execute("PRAGMA busy_timeout=5000;")
        conn.execute("PRAGMA cache_size=-64000;")
        conn.execute("PRAGMA temp_store=MEMORY;")
        conn.execute("PRAGMA mmap_size=268435456;")
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
            CREATE INDEX IF NOT EXISTS idx_job_postings_site_discovered ON job_postings(site, discovered_at);

            CREATE TABLE IF NOT EXISTS applications (
                application_id TEXT PRIMARY KEY,
                job_id TEXT NOT NULL,
                site TEXT NOT NULL,
                profile_id TEXT NOT NULL DEFAULT 'default',
                status TEXT NOT NULL,
                idempotency_key TEXT UNIQUE NOT NULL,
                trust_level TEXT NOT NULL DEFAULT 'SUPERVISED',
                form_values TEXT,
                unanswered_questions TEXT,
                evidence TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                error_message TEXT,
                responded_at TEXT,
                outcome TEXT,
                FOREIGN KEY (job_id) REFERENCES job_postings (job_id)
            );
            CREATE INDEX IF NOT EXISTS idx_applications_site_status ON applications(site, status);
            CREATE INDEX IF NOT EXISTS idx_applications_job_id ON applications(job_id);

            CREATE TABLE IF NOT EXISTS job_dedup_cache (
                dedup_hash TEXT PRIMARY KEY,
                job_id TEXT NOT NULL,
                title TEXT NOT NULL,
                company TEXT NOT NULL,
                location TEXT NOT NULL,
                embedding TEXT NOT NULL,
                added_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS saga_instances (
                saga_id TEXT PRIMARY KEY,
                job_id TEXT NOT NULL,
                profile_id TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS saga_steps (
                saga_id TEXT NOT NULL,
                step_name TEXT NOT NULL,
                status TEXT NOT NULL,
                detail TEXT,
                created_at TEXT NOT NULL,
                PRIMARY KEY (saga_id, step_name)
             );
            """)
        # Versioned migrations (UC-07) own everything after the base tables:
        # WS2 durable-execution schema, checksummed and replay-safe.
        from jobot.storage.migrations import run_migrations

        with self._get_connection() as conn:
            applied = run_migrations(conn)
            if applied:
                logger.info("applied migrations: %s", applied)

    @contextmanager
    def _migrate_conn(self) -> Iterator[sqlite3.Connection]:
        with self._get_connection() as conn:
            yield conn

    # -------------------------------------------------------------------
    # JobPosting Operations
    # -------------------------------------------------------------------

    def save_job_posting(self, job: JobPosting) -> None:
        self.save_job_postings_batch([job])

    def save_job_postings_batch(self, jobs: List[JobPosting]) -> None:
        if not jobs:
            return
        params = [
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
            )
            for job in jobs
        ]
        with self._get_connection() as conn:
            conn.executemany(
                """
                INSERT OR REPLACE INTO job_postings
                (job_id, site, url, title, company, location, description, parsed_skills, discovered_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                params,
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

    def list_job_postings(self, limit: int = 500) -> List[JobPosting]:
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM job_postings ORDER BY discovered_at DESC LIMIT ?", (limit,)
            ).fetchall()
        postings = []
        for row in rows:
            postings.append(
                JobPosting(
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
            )
        return postings

    # -------------------------------------------------------------------
    # Application Operations
    # -------------------------------------------------------------------

    # Statuses that represent a (terminal) employer response. Applications
    # reaching one of these for the first time are stamped `responded_at`.
    _RESPONSE_STATUSES = {
        ApplicationStatus.SUBMITTED,
        ApplicationStatus.VERIFIED,
        ApplicationStatus.REJECTED,
        ApplicationStatus.FAILED,
        ApplicationStatus.CANCELLED,
        ApplicationStatus.CIRCUIT_OPEN,
        ApplicationStatus.BLOCKED,
    }

    def _row_to_application(self, row: sqlite3.Row) -> Application:
        def _dt(value: Optional[str]) -> Optional[datetime]:
            return datetime.fromisoformat(value) if value else None

        keys = row.keys()
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
            created_at=_dt(row["created_at"]) or datetime.now(timezone.utc),
            updated_at=_dt(row["updated_at"]) or datetime.now(timezone.utc),
            responded_at=_dt(row["responded_at"]) if "responded_at" in keys else None,
            outcome=row["outcome"] if "outcome" in keys else None,
            submitted_at=_dt(row["submitted_at"]) if "submitted_at" in keys else None,
            submission_verified_at=(
                _dt(row["submission_verified_at"]) if "submission_verified_at" in keys else None
            ),
            first_employer_response_at=(
                _dt(row["first_employer_response_at"])
                if "first_employer_response_at" in keys
                else None
            ),
            current_outcome=row["current_outcome"] if "current_outcome" in keys else None,
        )

    def get_application_by_idempotency_key(self, idempotency_key: str) -> Optional[Application]:
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM applications WHERE idempotency_key = ?", (idempotency_key,)
            ).fetchone()
            return self._row_to_application(row) if row else None

    def application_exists(self, idempotency_key: str) -> bool:
        return self.get_application_by_idempotency_key(idempotency_key) is not None

    def save_application(self, app: Application) -> None:
        existing = self.get_application(app.application_id)
        responded_at = getattr(app, "responded_at", None)
        outcome = getattr(app, "outcome", None)
        now = datetime.now(timezone.utc).isoformat()
        # Stamp the first response time when crossing into a response status.
        if app.status in self._RESPONSE_STATUSES and responded_at is None:
            responded_at = app.updated_at if app.updated_at else datetime.now(timezone.utc)
            outcome = app.status.value
        if existing and existing.status != app.status and app.status in self._RESPONSE_STATUSES:
            if existing.responded_at is None:
                responded_at = app.updated_at if app.updated_at else datetime.now(timezone.utc)
                outcome = app.status.value
        with self._get_connection() as conn:
            if existing:
                conn.execute(
                    """
                    UPDATE applications
                    SET job_id = ?, site = ?, profile_id = ?, status = ?, trust_level = ?,
                        form_values = ?, error_message = ?, updated_at = ?,
                        responded_at = ?, outcome = ?,
                        submitted_at = ?, submission_verified_at = ?,
                        first_employer_response_at = ?, current_outcome = ?
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
                        now,
                        responded_at.isoformat() if responded_at else None,
                        outcome,
                        app.submitted_at.isoformat() if app.submitted_at else None,
                        (
                            app.submission_verified_at.isoformat()
                            if app.submission_verified_at
                            else None
                        ),
                        (
                            app.first_employer_response_at.isoformat()
                            if app.first_employer_response_at
                            else None
                        ),
                        app.current_outcome,
                        app.application_id,
                    ),
                )
            else:
                try:
                    conn.execute(
                        """
                        INSERT INTO applications
                        (application_id, job_id, site, profile_id, status, idempotency_key,
                         trust_level, form_values, error_message, created_at, updated_at,
                         responded_at, outcome, submitted_at, submission_verified_at,
                         first_employer_response_at, current_outcome)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                            now,
                            responded_at.isoformat() if responded_at else None,
                            outcome,
                            app.submitted_at.isoformat() if app.submitted_at else None,
                            (
                                app.submission_verified_at.isoformat()
                                if app.submission_verified_at
                                else None
                            ),
                            (
                                app.first_employer_response_at.isoformat()
                                if app.first_employer_response_at
                                else None
                            ),
                            app.current_outcome,
                        ),
                    )
                except sqlite3.IntegrityError as err:
                    if "idempotency_key" in str(err):
                        raise DuplicateApplicationError(
                            f"Application already exists for idempotency_key={app.idempotency_key}"
                        ) from err
                    raise

    def set_application_status(self, application_id: str, status: ApplicationStatus) -> bool:
        """Transition an application to a new status (stamps response time on terminal)."""
        app = self.get_application(application_id)
        if app is None:
            return False
        if app.status == status:
            return True
        app.status = status
        app.updated_at = datetime.now(timezone.utc)
        self.save_application(app)
        return True

    def get_application(self, application_id: str) -> Optional[Application]:
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM applications WHERE application_id = ?", (application_id,)
            ).fetchone()
            return self._row_to_application(row) if row else None

    def list_applications(self, limit: int = 50) -> List[Application]:
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM applications ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
            return [self._row_to_application(row) for row in rows]

    def get_applications_with_jobs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Applications joined with their job posting (for dashboards/analytics)."""
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT a.*, j.title as job_title, j.company as job_company,
                       j.location as job_location, j.url as job_url
                FROM applications a
                LEFT JOIN job_postings j ON a.job_id = j.job_id
                ORDER BY a.created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            results: List[Dict[str, Any]] = []
            for row in rows:
                app = self._row_to_application(row)
                results.append(
                    {
                        "application_id": app.application_id,
                        "job_id": app.job_id,
                        "site": app.site,
                        "company": row["job_company"] or app.site,
                        "title": row["job_title"] or "(unknown)",
                        "location": row["job_location"] or "",
                        "url": row["job_url"] or "",
                        "status": app.status.value,
                        "outcome": app.outcome,
                        "created_at": app.created_at.isoformat(),
                        "updated_at": app.updated_at.isoformat(),
                        "responded_at": app.responded_at.isoformat() if app.responded_at else None,
                    }
                )
            return results

    def get_daily_application_count(self, site: str) -> int:
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT COUNT(*) as count FROM applications WHERE site = ? AND created_at LIKE ?",
                (site, f"{today_str}%"),
            ).fetchone()
            return row["count"] if row else 0

    def clear_all_applications(self) -> int:
        """Clear all applications from SQLite database."""
        with self._get_connection() as conn:
            cursor = conn.execute("DELETE FROM applications")
            return cursor.rowcount

    # -------------------------------------------------------------------
    # Saga Operations (Phase 3: ApplyOrchestrator checkpoint/compensation)
    # -------------------------------------------------------------------

    def create_saga(self, job_id: str, profile_id: str) -> str:
        """Create a saga instance; returns its saga_id."""
        import uuid

        saga_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO saga_instances
                (saga_id, job_id, profile_id, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (saga_id, job_id, profile_id, "RUNNING", now, now),
            )
        return saga_id

    def update_saga_status(self, saga_id: str, status: str) -> None:
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE saga_instances SET status = ?, updated_at = ? WHERE saga_id = ?",
                (status, datetime.now(timezone.utc).isoformat(), saga_id),
            )

    def save_saga_step(self, saga_id: str, step_name: str, status: str, detail: str = "") -> None:
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO saga_steps
                (saga_id, step_name, status, detail, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (saga_id, step_name, status, detail, datetime.now(timezone.utc).isoformat()),
            )

    def get_saga(self, saga_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM saga_instances WHERE saga_id = ?", (saga_id,)
            ).fetchone()
            return dict(row) if row else None

    def list_saga_steps(self, saga_id: str) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM saga_steps WHERE saga_id = ? ORDER BY created_at", (saga_id,)
            ).fetchall()
            return [dict(r) for r in rows]

    def list_sagas(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM saga_instances ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(r) for r in rows]

    # -------------------------------------------------------------------
    # Job Dedup Cache Operations (scraper two-tier dedup)
    # -------------------------------------------------------------------

    def save_dedup_entry(
        self,
        dedup_hash: str,
        job_id: str,
        title: str,
        company: str,
        location: str,
        embedding: List[float],
    ) -> None:
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO job_dedup_cache
                (dedup_hash, job_id, title, company, location, embedding, added_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    dedup_hash,
                    job_id,
                    title,
                    company,
                    location,
                    json.dumps(embedding),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )

    def dedup_hash_exists(self, dedup_hash: str) -> bool:
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT 1 FROM job_dedup_cache WHERE dedup_hash = ?", (dedup_hash,)
            ).fetchone()
            return row is not None

    def list_dedup_entries(self) -> List[Dict[str, Any]]:
        """Return (dedup_hash, title, company, location, embedding) rows as dicts."""
        entries: List[Dict[str, Any]] = []
        with self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM job_dedup_cache").fetchall()
            for row in rows:
                entries.append(
                    {
                        "dedup_hash": row["dedup_hash"],
                        "job_id": row["job_id"],
                        "title": row["title"],
                        "company": row["company"],
                        "location": row["location"],
                        "embedding": json.loads(row["embedding"] or "[]"),
                    }
                )
        return entries

    # -------------------------------------------------------------------
    # Candidate Facts (UC-21 — Grounding & Truth System)
    # -------------------------------------------------------------------

    def save_candidate_fact(self, fact: CandidateFact) -> int:
        with self._get_connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO candidate_facts
                (profile_id, fact_type, fact_value, source, source_path,
                 confidence, verified, verified_at, verified_by, created_at, superseded_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    fact.profile_id,
                    fact.fact_type,
                    fact.fact_value,
                    fact.source,
                    fact.source_path,
                    fact.confidence,
                    1 if fact.verified else 0,
                    fact.verified_at.isoformat() if fact.verified_at else None,
                    fact.verified_by,
                    fact.created_at.isoformat(),
                    fact.superseded_by,
                ),
            )
            return int(cur.lastrowid or 0)

    def list_candidate_facts(
        self,
        profile_id: str = "default",
        fact_type: Optional[str] = None,
        verified_only: bool = False,
    ) -> List[CandidateFact]:
        query = "SELECT * FROM candidate_facts WHERE profile_id = ? AND superseded_by IS NULL"
        params: List[Any] = [profile_id]
        if fact_type:
            query += " AND fact_type = ?"
            params.append(fact_type)
        if verified_only:
            query += " AND verified = 1"
        query += " ORDER BY id"
        with self._get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [
                CandidateFact(
                    id=r["id"],
                    profile_id=r["profile_id"],
                    fact_type=r["fact_type"],
                    fact_value=r["fact_value"],
                    source=r["source"],
                    source_path=r["source_path"],
                    confidence=r["confidence"],
                    verified=bool(r["verified"]),
                    verified_at=datetime.fromisoformat(r["verified_at"])
                    if r["verified_at"]
                    else None,
                    verified_by=r["verified_by"],
                    created_at=datetime.fromisoformat(r["created_at"])
                    if r["created_at"]
                    else datetime.now(timezone.utc),
                    superseded_by=r["superseded_by"],
                )
                for r in rows
            ]

    def verify_candidate_fact(self, fact_id: int, verified_by: str = "human") -> None:
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE candidate_facts SET verified = 1, verified_at = ?, verified_by = ? WHERE id = ?",
                (datetime.now(timezone.utc).isoformat(), verified_by, fact_id),
            )

    # -------------------------------------------------------------------
    # Answer Bank Operations (UC-26 — Persistent QA Memory)
    # -------------------------------------------------------------------

    def save_answer_bank_entry(self, entry: AnswerBankRecord) -> None:
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO answer_bank
                (profile_id, question_hash, question_text, answer, source, used_count, last_used_at, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry.profile_id,
                    entry.question_hash,
                    entry.question_text,
                    entry.answer,
                    entry.source,
                    entry.used_count,
                    entry.last_used_at.isoformat() if entry.last_used_at else None,
                    entry.created_at.isoformat(),
                ),
            )

    def get_answer_bank_entry(
        self, profile_id: str, question_hash: str
    ) -> Optional[AnswerBankRecord]:
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM answer_bank WHERE profile_id = ? AND question_hash = ?",
                (profile_id, question_hash),
            ).fetchone()
            if not row:
                return None
            return AnswerBankRecord(
                id=row["id"],
                profile_id=row["profile_id"],
                question_hash=row["question_hash"],
                question_text=row["question_text"],
                answer=row["answer"],
                source=row["source"],
                used_count=row["used_count"],
                last_used_at=datetime.fromisoformat(row["last_used_at"])
                if row["last_used_at"]
                else None,
                created_at=datetime.fromisoformat(row["created_at"])
                if row["created_at"]
                else datetime.now(timezone.utc),
            )

    def record_answer_bank_use(self, profile_id: str, question_hash: str) -> None:
        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE answer_bank
                SET used_count = used_count + 1, last_used_at = ?
                WHERE profile_id = ? AND question_hash = ?
                """,
                (datetime.now(timezone.utc).isoformat(), profile_id, question_hash),
            )

    def search_answer_bank(
        self, profile_id: str = "default", query: str = ""
    ) -> List[AnswerBankRecord]:
        with self._get_connection() as conn:
            if query:
                rows = conn.execute(
                    "SELECT * FROM answer_bank WHERE profile_id = ? AND question_text LIKE ? ORDER BY used_count DESC",
                    (profile_id, f"%{query}%"),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM answer_bank WHERE profile_id = ? ORDER BY used_count DESC",
                    (profile_id,),
                ).fetchall()
            return [
                AnswerBankRecord(
                    id=r["id"],
                    profile_id=r["profile_id"],
                    question_hash=r["question_hash"],
                    question_text=r["question_text"],
                    answer=r["answer"],
                    source=r["source"],
                    used_count=r["used_count"],
                    last_used_at=datetime.fromisoformat(r["last_used_at"])
                    if r["last_used_at"]
                    else None,
                    created_at=datetime.fromisoformat(r["created_at"])
                    if r["created_at"]
                    else datetime.now(timezone.utc),
                )
                for r in rows
            ]

    # -------------------------------------------------------------------
    # Form Field Memory Operations (UC-26 — Persistent Field Memory)
    # -------------------------------------------------------------------

    def save_form_field_memory(self, record: FormFieldMemoryRecord) -> None:
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO form_field_memory
                (profile_id, adapter_id, field_selector, field_label, field_type, value, confidence, last_used_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.profile_id,
                    record.adapter_id,
                    record.field_selector,
                    record.field_label,
                    record.field_type,
                    record.value,
                    record.confidence,
                    (record.last_used_at or datetime.now(timezone.utc)).isoformat(),
                ),
            )

    def get_form_field_memory(
        self, profile_id: str, adapter_id: str, field_selector: str
    ) -> Optional[FormFieldMemoryRecord]:
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM form_field_memory WHERE profile_id = ? AND adapter_id = ? AND field_selector = ?",
                (profile_id, adapter_id, field_selector),
            ).fetchone()
            if not row:
                return None
            return FormFieldMemoryRecord(
                id=row["id"],
                profile_id=row["profile_id"],
                adapter_id=row["adapter_id"],
                field_selector=row["field_selector"],
                field_label=row["field_label"],
                field_type=row["field_type"],
                value=row["value"],
                confidence=row["confidence"],
                last_used_at=datetime.fromisoformat(row["last_used_at"])
                if row["last_used_at"]
                else None,
            )

    def backup(self, target_path: Optional[Path] = None) -> Path:
        """Create an atomic hot backup of SQLite database via sqlite3 backup API (UC-44)."""
        if target_path is None:
            ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            target_path = self.db_path.parent / f"jobot_backup_{ts}.db"
        target_path = Path(target_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with self._get_connection() as src_conn:
            dst_conn = sqlite3.connect(target_path)
            try:
                src_conn.backup(dst_conn)
            finally:
                dst_conn.close()
        if os.name == "posix":
            os.chmod(target_path, 0o600)
        return target_path

    def restore(self, source_path: Path) -> None:
        """Restore SQLite database from backup file (UC-44)."""
        source_path = Path(source_path)
        if not source_path.exists():
            raise FileNotFoundError(f"Backup file not found: {source_path}")
        with sqlite3.connect(source_path) as src_conn:
            with self._get_connection() as dst_conn:
                src_conn.backup(dst_conn)
