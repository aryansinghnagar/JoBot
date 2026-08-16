"""Hardening tests for the CredentialVault keyfile fallback path (WS1-W7).

Covers: atomic 0600 keyfile creation (no tmp leftovers), valid Fernet key
round-trip, fail-closed refusal of loosened keyfile permissions (POSIX),
symlink refusal via O_NOFOLLOW (POSIX), and crash-recovery from a stale tmp
file. Windows runs the portable subset (NTFS user-profile ACLs cover the
permission model there).
"""

import os
import stat
from pathlib import Path

import pytest
from cryptography.fernet import Fernet
from jobot.models.domain import PersonalInfo, UserProfile
from jobot.storage.vault import CredentialVault

IS_POSIX = os.name == "posix"


@pytest.fixture()
def vault_dir(tmp_path: Path) -> Path:
    d = tmp_path / "vault"
    d.mkdir()
    return d


def _make_profile(profile_id: str = "p-harden") -> UserProfile:
    return UserProfile(
        profile_id=profile_id,
        personal_info=PersonalInfo(first_name="Hardening", email="harden@example.com"),
    )


def test_keyfile_fallback_roundtrip_and_no_tmp_leftover(vault_dir: Path) -> None:
    """Force the keyfile fallback by pointing at an empty dir with keyring
    bypassed (monkeypatch keyring to simulate an unavailable backend)."""
    import jobot.storage.vault as vault_mod

    class UnavailableKeyring:
        def __getattr__(self, name):
            raise RuntimeError("keyring unavailable")

    original = vault_mod.keyring
    vault_mod.keyring = UnavailableKeyring()
    try:
        vault = CredentialVault(vault_dir)
        key_file = vault_dir / "master.key"
        assert key_file.exists(), "keyfile fallback must create master.key"
        key_bytes = key_file.read_bytes()
        Fernet(key_bytes)  # raises if not a valid Fernet key
        # Round-trip via a second vault instance reading the same keyfile
        vault2 = CredentialVault(vault_dir)
        secret = "round-trip-secret"
        assert vault2.decrypt_data(vault.encrypt_data(secret)) == secret
        # Atomic create leaves no temp residue
        leftovers = [p.name for p in vault_dir.iterdir() if p.name.endswith(".tmp")]
        assert leftovers == [], f"tmp leftovers: {leftovers}"
    finally:
        vault_mod.keyring = original


def test_stale_tmp_from_crash_is_recovered(vault_dir: Path) -> None:
    import jobot.storage.vault as vault_mod

    class UnavailableKeyring:
        def __getattr__(self, name):
            raise RuntimeError("keyring unavailable")

    original = vault_mod.keyring
    vault_mod.keyring = UnavailableKeyring()
    try:
        # Simulate a crashed write: tmp exists, keyfile does not
        (vault_dir / "master.key.tmp").write_bytes(b"partial-garbage")
        CredentialVault(vault_dir)
        key_file = vault_dir / "master.key"
        assert key_file.exists()
        Fernet(key_file.read_bytes())
        assert not (vault_dir / "master.key.tmp").exists()
    finally:
        vault_mod.keyring = original


def test_encrypted_profile_roundtrip_atomic(vault_dir: Path, tmp_path: Path) -> None:
    vault = CredentialVault(vault_dir)
    profile = _make_profile()
    out = tmp_path / "profiles" / "p.enc"
    saved = vault.save_encrypted_profile(profile, out)
    assert saved == out
    assert not out.with_name(out.name + ".tmp").exists()
    loaded = vault.load_encrypted_profile(out)
    assert loaded.profile_id == profile.profile_id
    assert loaded.personal_info.email == profile.personal_info.email
    # Ciphertext must not contain plaintext PII
    blob = out.read_bytes()
    assert b"harden@example.com" not in blob
    assert b"Hardening" not in blob


@pytest.mark.skipif(not IS_POSIX, reason="POSIX permission model")
def test_keyfile_created_0600(vault_dir: Path) -> None:
    import jobot.storage.vault as vault_mod

    class UnavailableKeyring:
        def __getattr__(self, name):
            raise RuntimeError("keyring unavailable")

    original = vault_mod.keyring
    vault_mod.keyring = UnavailableKeyring()
    try:
        CredentialVault(vault_dir)
        mode = stat.S_IMODE((vault_dir / "master.key").stat().st_mode)
        assert mode == 0o600
    finally:
        vault_mod.keyring = original


@pytest.mark.skipif(not IS_POSIX, reason="POSIX permission model")
def test_loosened_keyfile_permissions_fail_closed(vault_dir: Path) -> None:
    import jobot.storage.vault as vault_mod

    class UnavailableKeyring:
        def __getattr__(self, name):
            raise RuntimeError("keyring unavailable")

    original = vault_mod.keyring
    vault_mod.keyring = UnavailableKeyring()
    try:
        CredentialVault(vault_dir)  # creates keyfile
        os.chmod(vault_dir / "master.key", 0o644)
        with pytest.raises(PermissionError):
            CredentialVault(vault_dir)
    finally:
        vault_mod.keyring = original


@pytest.mark.skipif(not IS_POSIX, reason="O_NOFOLLOW is POSIX-only")
def test_keyfile_symlink_refused(vault_dir: Path) -> None:
    import jobot.storage.vault as vault_mod

    class UnavailableKeyring:
        def __getattr__(self, name):
            raise RuntimeError("keyring unavailable")

    original = vault_mod.keyring
    vault_mod.keyring = UnavailableKeyring()
    try:
        CredentialVault(vault_dir)  # creates real keyfile
        real = vault_dir / "master.key"
        link = vault_dir / "link.key"
        link.symlink_to(real)
        with pytest.raises(OSError):
            CredentialVault._read_keyfile(link)
    finally:
        vault_mod.keyring = original
