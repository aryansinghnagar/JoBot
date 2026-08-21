import pytest

from jobot.memory.vector import VectorMemory
from jobot.models.domain import Application, ApplicationStatus
from jobot.security.pii_masker import PIIMasker
from jobot.stealth.http_client import StealthHTTPClient


def test_pii_masker_email_and_phone():
    masker = PIIMasker()
    text = "Contact Jane at jane.doe@example.com or +15551234567 for details."
    masked, mapping = masker.mask(text)

    assert "jane.doe@example.com" not in masked
    assert "+15551234567" not in masked
    assert "[EMAIL_0]" in masked or "[PHONE_0]" in masked

    unmasked = masker.unmask(masked, mapping)
    assert unmasked == text


def test_vector_memory_store_and_retrieve():
    mem = VectorMemory(collection_name="test_qa")
    mem.store_answer("p1", "What is your notice period?", "30 days", site="naukri")
    mem.store_answer("p2", "What are your core skills?", "Python, FastAPI", site="naukri")

    results = mem.retrieve_similar("notice period", top_k=1)
    assert len(results) >= 1
    assert "answer" in results[0]


@pytest.mark.asyncio
async def test_stealth_http_client_get():
    client = StealthHTTPClient()
    # Mock GET test
    assert client.impersonate == "chrome120"
    assert "User-Agent" in client.default_headers


def test_domain_application_record():
    rec = Application(
        application_id="app_123",
        job_id="job_456",
        user_profile_id="default",
        site="naukri",
        status=ApplicationStatus.VERIFIED,
        idempotency_key="hash_789",
    )
    assert rec.application_id == "app_123"
    assert rec.status == ApplicationStatus.VERIFIED
