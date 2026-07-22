import base64
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import keyring
from jobot.models.domain import UserProfile

SERVICE_NAME = "jobot_vault"
KEYRING_USERNAME = "master_key"


class CredentialVault:
    """
    Credential & Profile Vault.
    Uses AES-256 Fernet symmetric encryption key stored securely in the OS Keyring.
    Falls back to a protected local keyfile (~/.jobot/vault.key) if Keyring is unavailable.
    """

    def __init__(self, key_dir: Optional[Path] = None):
        if key_dir is None:
            key_dir = Path.home() / ".jobot" / "vault"
            key_dir.mkdir(parents=True, exist_ok=True)
        self.key_dir = key_dir
        self.fernet = Fernet(self._get_or_create_master_key())

    def _get_or_create_master_key(self) -> bytes:
        # Try reading key from OS Keyring first
        try:
            stored_key = keyring.get_password(SERVICE_NAME, KEYRING_USERNAME)
            if stored_key:
                return stored_key.encode()
        except Exception:
            pass

        # Fallback: Local keyfile
        key_file = self.key_dir / "master.key"
        if key_file.exists():
            with open(key_file, "rb") as f:
                return f.read()

        # Generate new Fernet master key
        new_key = Fernet.generate_key()
        try:
            keyring.set_password(SERVICE_NAME, KEYRING_USERNAME, new_key.decode())
        except Exception:
            # Save to keyfile with 0600 permissions
            with open(key_file, "wb") as f:
                f.write(new_key)
            if os.name == "posix":
                os.chmod(key_file, 0o600)

        return new_key

    def encrypt_data(self, data: str) -> bytes:
        return self.fernet.encrypt(data.encode())

    def decrypt_data(self, encrypted_bytes: bytes) -> str:
        return self.fernet.decrypt(encrypted_bytes).decode()

    # -------------------------------------------------------------------
    # Profile Storage Operations
    # -------------------------------------------------------------------

    def save_encrypted_profile(self, profile: UserProfile, profile_path: Optional[Path] = None) -> Path:
        if profile_path is None:
            profile_dir = Path.home() / ".jobot" / "profiles"
            profile_dir.mkdir(parents=True, exist_ok=True)
            profile_path = profile_dir / f"{profile.profile_id}.enc"
        else:
            profile_path.parent.mkdir(parents=True, exist_ok=True)

        profile_json = profile.model_dump_json()
        encrypted_bytes = self.encrypt_data(profile_json)

        with open(profile_path, "wb") as f:
            f.write(encrypted_bytes)

        if os.name == "posix":
            os.chmod(profile_path, 0o600)

        return profile_path

    def load_encrypted_profile(self, profile_path: Path) -> UserProfile:
        with open(profile_path, "rb") as f:
            encrypted_bytes = f.read()

        decrypted_json = self.decrypt_data(encrypted_bytes)
        return UserProfile.model_validate_json(decrypted_json)
