"""Phase 4 WS6: plugins — manifest, installer (file:// git), auditor, CLI."""

import subprocess
from pathlib import Path

import pytest
from jobot.plugins.auditor import PluginAuditor
from jobot.plugins.installer import PluginInstaller
from jobot.plugins.manifest import load_manifest
from typer.testing import CliRunner

from jobot.cli.main import app

GOOD_MANIFEST = """\
name: hello-bot
version: 1.0.0
description: Says hello
author: test
license: MIT
requires: []
permissions: [network]
entrypoints:
  - name: hello
    module: hello_plugin
    function: run
"""

BAD_NAME_MANIFEST = """\
name: ../escape
version: 1.0.0
permissions: []
entrypoints: []
"""

BAD_PERM_MANIFEST = """\
name: bad-perms
version: 1.0.0
permissions: [hack-all]
entrypoints: []
"""

SECRET_MANIFEST = """\
name: secret-bot
version: 1.0.0
permissions: []
entrypoints: []
settings:
  api_key: sk-live-12345
"""


def git(*args, cwd: Path):
    env = {"GIT_CONFIG_NOSYSTEM": "1"}
    proc = subprocess.run(
        ["git", "-c", "user.name=test", "-c", "user.email=test@example.com", *args],
        capture_output=True,
        text=True,
        cwd=str(cwd),
        env=env,
    )
    assert proc.returncode == 0, proc.stderr
    return proc


@pytest.fixture
def plugin_repo(tmp_path):
    repo = tmp_path / "hello-repo"
    repo.mkdir()
    (repo / "jobot-manifest.yaml").write_text(GOOD_MANIFEST, encoding="utf-8")
    (repo / "hello_plugin.py").write_text("def run():\n    return 'hello'\n", encoding="utf-8")
    git("init", cwd=repo)
    git("add", ".", cwd=repo)
    git("commit", "-m", "init", cwd=repo)
    return repo


def repo_url(repo: Path) -> str:
    return repo.as_uri()


def test_manifest_validation_good(tmp_path):
    (tmp_path / "jobot-manifest.yaml").write_text(GOOD_MANIFEST, encoding="utf-8")
    manifest = load_manifest(tmp_path)
    assert manifest.name == "hello-bot"
    assert manifest.entrypoints[0].function == "run"


def test_manifest_rejects_bad_name(tmp_path):
    (tmp_path / "jobot-manifest.yaml").write_text(BAD_NAME_MANIFEST, encoding="utf-8")
    with pytest.raises(ValueError, match="invalid plugin name"):
        load_manifest(tmp_path)


def test_manifest_rejects_bad_permission(tmp_path):
    (tmp_path / "jobot-manifest.yaml").write_text(BAD_PERM_MANIFEST, encoding="utf-8")
    with pytest.raises(ValueError, match="unknown permission"):
        load_manifest(tmp_path)


def test_install_via_file_url(plugin_repo, tmp_path, monkeypatch):
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    installer = PluginInstaller()
    manifest = installer.install(repo_url(plugin_repo))
    assert manifest.name == "hello-bot"
    dest = tmp_path / ".jobot" / "plugins" / "hello-bot"
    assert (dest / "jobot-manifest.yaml").exists()
    assert (dest / "hello_plugin.py").exists()
    assert installer.list_plugins()[0]["name"] == "hello-bot"


def test_install_rejects_duplicate(plugin_repo, tmp_path, monkeypatch):
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    installer = PluginInstaller()
    installer.install(repo_url(plugin_repo))
    with pytest.raises(ValueError, match="already installed"):
        installer.install(repo_url(plugin_repo))


def test_install_requires_manifest(tmp_path, monkeypatch):
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    repo = tmp_path / "no-manifest"
    repo.mkdir()
    git("init", cwd=repo)
    with pytest.raises(ValueError, match="missing jobot-manifest.yaml"):
        PluginInstaller().install(repo.as_uri())


def test_remove_plugin(plugin_repo, tmp_path, monkeypatch):
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    installer = PluginInstaller()
    installer.install(repo_url(plugin_repo))
    assert installer.remove("hello-bot") is True
    assert installer.list_plugins() == []
    assert installer.remove("hello-bot") is False


def test_auditor_passes_good_plugin(plugin_repo):
    report = PluginAuditor().audit(plugin_repo)
    assert report.passed is True
    assert report.plugin == "hello-bot"


def test_auditor_flags_secrets(tmp_path):
    (tmp_path / "jobot-manifest.yaml").write_text(SECRET_MANIFEST, encoding="utf-8")
    report = PluginAuditor().audit(tmp_path)
    assert report.passed is False
    assert any("secret" in f.message.lower() for f in report.findings)


def test_auditor_flags_dangerous_imports(tmp_path):
    (tmp_path / "jobot-manifest.yaml").write_text(GOOD_MANIFEST, encoding="utf-8")
    (tmp_path / "evil.py").write_text("import subprocess\n", encoding="utf-8")
    report = PluginAuditor().audit(tmp_path)
    assert report.passed is False
    assert any("subprocess" in f.message for f in report.findings)


def test_cli_plugin_list_empty(tmp_path, monkeypatch):
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    runner = CliRunner()
    result = runner.invoke(app, ["plugin", "list"])
    assert result.exit_code == 0


def test_cli_plugin_install_requires_url():
    runner = CliRunner()
    result = runner.invoke(app, ["plugin", "install"])
    assert result.exit_code != 0
