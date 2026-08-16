import logging
import os
from pathlib import Path
from typing import Optional
from cryptography.fernet import Fernet
import keyring
from jobot.models.domain import UserProfile

SERVICE_NAME = "jobot_vault"
KEYRING_USERNAME = "master_key"

logger = logging.getLogger(__name__)

# Fail-closed posture for the vault keyfile: it decrypts every stored
# credential, so a permissive mode or a swapped symlink target must abort
# startup rather than silently hand the key to another local user.
_KEYFILE_REQUIRED_MODE = 0o600
_O_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)


class CredentialVault:
    """
    Credential & Profile Vault.
    Uses AES-256 Fernet symmetric encryption key stored securely in the OS Keyring.
    Falls back to a protected local keyfile (~/.jobot/vault/master.key) if Keyring
    is unavailable. The fallback keyfile is created atomically with 0600 perms,
    read with O_NOFOLLOW (POSIX), and refused if its permissions have been
    loosened (POSIX). On Windows, NTFS user-profile ACLs provide the equivalent
    protection for files under the user's home directory.
    """

    def __init__(self, key_dir: Optional[Path] = None):
        if key_dir is None:
            key_dir = Path.home() / ".jobot" / "vault"
        key_dir.mkdir(parents=True, exist_ok=True)
        if os.name == "posix":
            key_mode = key_dir.stat().st_mode & 0o777
            if key_mode & 0o077:
                os.chmod(key_dir, 0o700)
        self.key_dir = key_dir
        self.fernet = Fernet(self._get_or_create_master_key())

    def _get_or_create_master_key(self) -> bytes:
        # Try reading key from OS Keyring first (jobot_vault or legacy jobaut_vault)
        try:
            stored_key = keyring.get_password(SERVICE_NAME, KEYRING_USERNAME)
            if stored_key:
                return stored_key.encode()
            legacy_key = keyring.get_password("jobaut_vault", KEYRING_USERNAME)
            if legacy_key:
                try:
                    keyring.set_password(SERVICE_NAME, KEYRING_USERNAME, legacy_key)
                except Exception:
                    logger.debug("Keyring migration write failed; using legacy key")
                return legacy_key.encode()
        except Exception:
            logger.debug("OS keyring unavailable; falling back to local keyfile")

        # Fallback: Local keyfile
        key_file = self.key_dir / "master.key"
        if key_file.exists():
            return self._read_keyfile(key_file)

        # Generate new Fernet master key
        new_key = Fernet.generate_key()
        try:
            keyring.set_password(SERVICE_NAME, KEYRING_USERNAME, new_key.decode())
        except Exception:
            self._write_keyfile_atomic(key_file, new_key)

        return new_key

    # -------------------------------------------------------------------
    # Keyfile hardening primitives
    # -------------------------------------------------------------------

    @staticmethod
    def _read_keyfile(key_file: Path) -> bytes:
        """Read the master key without following symlinks (POSIX)."""
        if os.name == "posix":
            mode = key_file.stat().st_mode & 0o777
            if mode != _KEYFILE_REQUIRED_MODE:
                raise PermissionError(
                    f"Vault keyfile {key_file} has mode {oct(mode)}; expected "
                    f"{oct(_KEYFILE_REQUIRED_MODE)}. Refusing to read a "
                    "loosely permissioned key. Fix with: chmod 600 <keyfile>."
                )
        flags = os.O_RDONLY | _O_NOFOLLOW
        fd = os.open(key_file, flags)
        f = os.fdopen(fd, "rb")
        try:
            return f.read()
        finally:
            f.close()

    @staticmethod
    def _write_keyfile_atomic(key_file: Path, data: bytes) -> None:
        """Create the keyfile 0600 atomically: no window where it is readable
        by group/other and no partially-written key on crash."""
        tmp_file = key_file.with_name(key_file.name + ".tmp")
        # Clear a stale temp from a crashed write; on POSIX unlink also drops
        # any symlink planted at the tmp name before O_EXCL|O_NOFOLLOW reopens.
        tmp_file.unlink(missing_ok=True)
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | _O_NOFOLLOW
        fd = os.open(tmp_file, flags, _KEYFILE_REQUIRED_MODE)
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(data)
            if os.name == "posix":
                os.chmod(tmp_file, _KEYFILE_REQUIRED_MODE)
            os.replace(tmp_file, key_file)
        except OSError:
            tmp_file.unlink(missing_ok=True)
            raise

    def encrypt_data(self, data: str) -> bytes:
        return self.fernet.encrypt(data.encode())

    def decrypt_data(self, encrypted_bytes: bytes) -> str:
        return self.fernet.decrypt(encrypted_bytes).decode()

    # -------------------------------------------------------------------
    # Profile Storage Operations
    # -------------------------------------------------------------------

    def save_encrypted_profile(
        self, profile: UserProfile, profile_path: Optional[Path] = None
    ) -> Path:
        if profile_path is None:
            profile_dir = Path.home() / ".jobot" / "profiles"
            profile_dir.mkdir(parents=True, exist_ok=True)
            profile_path = profile_dir / f"{profile.profile_id}.enc"
        else:
            profile_path.parent.mkdir(parents=True, exist_ok=True)

        profile_json = profile.model_dump_json()
        encrypted_bytes = self.encrypt_data(profile_json)

        tmp_path = profile_path.with_name(profile_path.name + ".tmp")
        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | _O_NOFOLLOW
        fd = os.open(tmp_path, flags, 0o600)
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(encrypted_bytes)
            if os.name == "posix":
                os.chmod(tmp_path, 0o600)
            os.replace(tmp_path, profile_path)
        except OSError:
            tmp_path.unlink(missing_ok=True)
            raise

        return profile_path

    def load_encrypted_profile(self, profile_path: Path) -> UserProfile:
        flags = os.O_RDONLY | _O_NOFOLLOW
        fd = os.open(profile_path, flags)
        f = os.fdopen(fd, "rb")
        try:
            encrypted_bytes = f.read()
        finally:
            f.close()

        decrypted_json = self.decrypt_data(encrypted_bytes)
        return UserProfile.model_validate_json(decrypted_json)
