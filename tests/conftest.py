import threading
import time
import pytest
from tests.mock_ats.server import app as flask_app


@pytest.fixture(scope="session")
def live_mock_ats_server():
    server_thread = threading.Thread(
        target=lambda: flask_app.run(
            host="127.0.0.1", port=5800, debug=False, use_reloader=False
        ),
        daemon=True,
    )
    server_thread.start()
    time.sleep(1.0)
    yield "http://127.0.0.1:5800"
