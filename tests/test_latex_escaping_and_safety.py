"""Tests for LaTeX escaping completeness and compilation safety flags (JOB-AUD-001)."""

from unittest.mock import patch

from jobot.documents.compiler import ResumeData, escape_latex
from jobot.documents.engines import LuaLaTeXRenderer


def test_escape_latex_special_characters():
    # Backslash, tildes, circumflex, and specials
    raw = r"C# & C++ ~ 5 years ^ senior \ lead; salary $100k+ with 100% {ownership} & user_profile"
    escaped = escape_latex(raw)

    assert r"\textbackslash{}" in escaped
    assert r"\textasciitilde{}" in escaped
    assert r"\textasciicircum{}" in escaped
    assert r"\&" in escaped
    assert r"\$" in escaped
    assert r"\%" in escaped
    assert r"\_" in escaped
    assert r"\{" in escaped
    assert r"\}" in escaped
    assert r"\#" in escaped

    # Ensure no naked special characters remain that break LaTeX
    assert "& " not in escaped.replace(r"\&", "")
    assert "%" not in escaped.replace(r"\%", "")
    assert "$" not in escaped.replace(r"\$", "")
    assert "#" not in escaped.replace(r"\#", "")


def test_lualatex_renderer_passes_no_shell_escape(tmp_path):
    renderer = LuaLaTeXRenderer()
    data = ResumeData(name="Test Candidate", contact="test@example.com")
    out_pdf = tmp_path / "resume.pdf"

    with patch("shutil.which", return_value="xelatex"), patch("subprocess.run") as mock_run:
        # Mock subprocess returning success and creating a fake PDF
        def fake_run(args, **kwargs):
            workdir = kwargs.get("cwd")
            if workdir:
                (workdir / "resume.pdf").write_bytes(b"%PDF-fake")
            from unittest.mock import MagicMock

            m = MagicMock()
            m.returncode = 0
            m.stdout = ""
            m.stderr = ""
            return m

        mock_run.side_effect = fake_run

        renderer.render(data, "default", out_pdf)

        assert mock_run.call_count == 1
        call_args = mock_run.call_args[0][0]
        assert "-no-shell-escape" in call_args
        assert "-halt-on-error" in call_args
