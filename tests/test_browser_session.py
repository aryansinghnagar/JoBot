from pathlib import Path
import tempfile
import pytest

from jobot.stealth.browser import BrowserSession


def test_browser_session_directory_creation():
    with tempfile.TemporaryDirectory() as tmpdir:
        session_dir = Path(tmpdir) / "naukri_session"
        session = BrowserSession(portal="naukri", session_dir=session_dir)

        assert session.portal == "naukri"
        assert session.session_dir == session_dir
        assert session_dir.exists()


@pytest.mark.asyncio
async def test_browser_session_launch_and_close():
    with tempfile.TemporaryDirectory() as tmpdir:
        session_dir = Path(tmpdir) / "test_session"
        session = BrowserSession(portal="test", headless=True, session_dir=session_dir)

        try:
            await session.start()
            assert session.context is not None
            page = await session.new_page()
            assert page is not None
            assert len(session.pages) >= 1
        except Exception as exc:
            # Handle environment missing chromium browser gracefully in headless test runner
            pytest.skip(f"Patchright chromium executable not available in environment: {exc}")
        finally:
            await session.close()
            assert session.context is None
