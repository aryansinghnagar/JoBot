"""Automated verification that all CLI examples in user docs map to real Typer commands."""

import re
from pathlib import Path
from jobot.cli.main import app


def get_registered_cli_commands() -> set[str]:
    """Extract all registered command names from Typer app."""
    commands = set()
    for cmd in app.registered_commands:
        if cmd.name:
            commands.add(cmd.name)
    return commands


def extract_documented_jobot_commands(doc_path: Path) -> set[str]:
    """Parse markdown file and extract first token after 'jobot' in bash code blocks."""
    if not doc_path.exists():
        return set()
    text = doc_path.read_text(encoding="utf-8")
    # Matches lines like "jobot <cmd> ..." or "`jobot <cmd>`"
    matches = re.findall(r"(?:^|\n|`)\s*jobot\s+([a-zA-Z0-9_-]+)", text)
    return set(matches)


def test_user_guide_commands_exist():
    root = Path(__file__).resolve().parents[1]
    registered = get_registered_cli_commands()
    assert len(registered) > 0

    user_guide_path = root / "USER_GUIDE.md"
    documented = extract_documented_jobot_commands(user_guide_path)
    assert len(documented) > 0

    # Every command referenced in USER_GUIDE.md must exist
    unregistered = documented - registered
    assert not unregistered, f"USER_GUIDE.md references non-existent CLI commands: {unregistered}"


def test_cli_reference_commands_exist():
    root = Path(__file__).resolve().parents[1]
    registered = get_registered_cli_commands()

    cli_ref_path = root / "docs" / "user" / "cli-reference.md"
    documented = extract_documented_jobot_commands(cli_ref_path)
    assert len(documented) > 0

    unregistered = documented - registered
    assert not unregistered, f"cli-reference.md references non-existent CLI commands: {unregistered}"


def test_readme_commands_exist():
    root = Path(__file__).resolve().parents[1]
    registered = get_registered_cli_commands()

    readme_path = root / "README.md"
    documented = extract_documented_jobot_commands(readme_path)
    assert len(documented) > 0

    unregistered = documented - registered
    assert not unregistered, f"README.md references non-existent CLI commands: {unregistered}"


def test_setup_commands_exist():
    root = Path(__file__).resolve().parents[1]
    registered = get_registered_cli_commands()

    setup_path = root / "SETUP.md"
    documented = extract_documented_jobot_commands(setup_path)
    assert len(documented) > 0

    unregistered = documented - registered
    assert not unregistered, f"SETUP.md references non-existent CLI commands: {unregistered}"
