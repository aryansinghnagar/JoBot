import pytest
from jobot.documents.pdf_exporter import ResumeExporter
from jobot.evals.optimizer import EvalOptimizer
from jobot.gui.sidecar import StdioSidecarServer
from jobot.models.domain import PersonalInfo, UserProfile
from jobot.obs.alerts import AlertDispatcher, AlertLevel


def test_resume_exporter(tmp_path):
    exporter = ResumeExporter()
    profile = UserProfile(
        profile_id="adv_test",
        personal_info=PersonalInfo(first_name="Aryan", last_name="Nagar", email="aryan@example.com"),
        skills=["Python", "FastAPI", "SQLite"],
    )

    txt_resume = exporter.compile_text_resume(profile)
    assert "ARYAN NAGAR" in txt_resume
    assert "Python, FastAPI, SQLite" in txt_resume

    html_resume = exporter.compile_html_resume(profile)
    assert "<h1>Aryan Nagar</h1>" in html_resume

    exported_file = exporter.export_resume_files(profile, output_dir=tmp_path)
    assert exported_file.exists()


def test_alert_dispatcher():
    dispatcher = AlertDispatcher()
    alert = dispatcher.dispatch_alert("Test Milestone", "100 applications submitted", level=AlertLevel.INFO)

    assert alert.title == "Test Milestone"
    assert len(dispatcher.alert_history) == 1
    assert dispatcher.alert_history[0].level == AlertLevel.INFO


def test_eval_optimizer():
    optimizer = EvalOptimizer()
    metrics = optimizer.analyze_portal_performance()
    assert isinstance(metrics, dict)


def test_sidecar_rpc_server():
    server = StdioSidecarServer()

    # Test ping RPC
    req = {"jsonrpc": "2.0", "method": "ping", "params": {}, "id": 1}
    res = server.process_request(req)
    assert res["id"] == 1
    assert res["result"]["status"] == "pong"

    # Test unknown method RPC
    req_invalid = {"jsonrpc": "2.0", "method": "non_existent_method", "params": {}, "id": 2}
    res_invalid = server.process_request(req_invalid)
    assert res_invalid["error"]["code"] == -32601
