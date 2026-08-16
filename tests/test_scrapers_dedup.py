"""DedupService tests (plan.md Phase 2: two-tier dedup + exit criterion ≥80% repost reduction)."""

import tempfile
from pathlib import Path

import pytest

from jobot.memory.vector import simple_embedding
from jobot.models.domain import JobPosting
from jobot.scrapers.dedup import DedupService
from jobot.storage.db import DatabaseManager


def make_posting(
    title: str, company: str = "Acme", location: str = "Remote", job_id: str = ""
) -> JobPosting:
    return JobPosting(
        job_id=job_id or f"{title}|{company}",
        site="linkedin",
        url=f"https://linkedin.com/jobs/{job_id or title}",
        title=title,
        company=company,
        location=location,
        description="Senior role description with skills.",
        parsed_skills=[],
    )


@pytest.fixture
def dedup(tmp_path: Path) -> DedupService:
    return DedupService(db=DatabaseManager(tmp_path / "dedup_test.db"))


def test_normalize(dedup: DedupService):
    assert DedupService.normalize("  Senior  Backend, Engineer!! ") == "senior backend engineer"
    assert DedupService.normalize("") == ""


def test_exact_hash_insensitive_to_case_and_punctuation(dedup: DedupService):
    a = DedupService.exact_hash("Senior Backend Engineer", "Acme Corp", "New York, NY")
    b = DedupService.exact_hash("  senior-backend_engineer ", "ACME corp", "new york ny")
    assert a == b


def test_cosine_of_identical_embeddings_is_one():
    v = simple_embedding("python developer backend")
    assert DedupService.cosine(v, v) == pytest.approx(1.0)


def test_exact_duplicate_rejected(dedup: DedupService):
    first = make_posting("Backend Engineer", "Acme", "Remote")
    assert not dedup.is_duplicate(first)
    dedup.record(first)

    dup = make_posting("Backend Engineer", "Acme", "Remote", job_id="other-id")
    assert dedup.is_duplicate(dup)


def test_near_duplicate_rejected_by_vector_tier(dedup: DedupService):
    base = make_posting("Senior Full-Stack Developer - Python & React", "Acme", "Remote")
    dedup.record(base)

    near = make_posting(
        "Senior Full Stack Developer Python React",
        "Acme",
        "Remote",
        job_id="reposted",
    )
    assert dedup.is_duplicate(near)


def test_distinct_roles_kept(dedup: DedupService):
    a = make_posting("Senior Backend Engineer - Python", "Acme", "Remote")
    dedup.record(a)

    b = make_posting("Senior DevOps Engineer - Kubernetes", "Acme", "Remote")
    assert not dedup.is_duplicate(b)


def test_filter_unique_counts_and_persists(dedup: DedupService):
    postings = [
        make_posting("Backend Engineer", "Acme", "Remote", "1"),
        make_posting("Backend Engineer", "Acme", "Remote", "2"),
        make_posting("DevOps Engineer", "Acme", "Remote", "3"),
    ]
    result = dedup.filter_unique(postings)

    assert len(result.unique) == 2
    assert result.rejected == 1
    assert result.repost_rate == pytest.approx(1 / 3)
    assert result.scraped == 3
    assert len(dedup.db.list_dedup_entries()) == 2


def test_persistence_across_service_instances(tmp_path: Path):
    db = DatabaseManager(tmp_path / "persist.db")
    first = DedupService(db=db)
    first.record(make_posting("Backend Engineer", "Acme", "Remote"))

    second = DedupService(db=db)
    assert second.is_duplicate(make_posting("Backend Engineer", "Acme", "Remote"))


def test_repost_reduction_meets_exit_criterion():
    """plan.md exit criterion: dedup rejects ≥80% of reposts in a synthetic corpus."""
    base = make_posting("Senior Data Engineer - Spark & Airflow", "Acme", "Remote")
    base_variants = [
        "Senior Data Engineer - Spark and Airflow",
        "Senior Data Engineer, Spark & Airflow",
        "Sr. Data Engineer (Spark/Airflow)",
        "Senior Data Engineer — Spark & Airflow",
        "Data Engineer Senior - Spark & Airflow",
    ]
    # Streaming crawl order: originals first, reposts later (as in real crawls).
    synthetic = [(base, False)]
    for i in range(3):
        synthetic.append(
            (
                make_posting(
                    f"Marketing Manager - Growth {i}", "Acme", "Remote", job_id=f"mm-{i}"
                ),
                False,
            )
        )
    for i, v in enumerate(base_variants):
        synthetic.append((make_posting(v, "Acme", "Remote", job_id=f"dup-{i}"), True))

    score = DedupService.repost_reduction(synthetic)

    assert score >= 0.8
