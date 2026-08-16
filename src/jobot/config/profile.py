"""profiles/ YAML schema + loader (SETUP.md Tier 4, config-only).

Per Phase 1 decision: the YAML holds non-identity sections (search, target,
resume_base, llm, outreach). Identity facts remain canonical in the
Fernet-encrypted vault (`~/.jobot/profiles/default.enc`). A missing YAML is
not an error — defaults apply.
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel, Field

DEFAULT_PROFILE_DIR = Path.home() / ".jobot" / "profiles"


class SearchConfig(BaseModel):
    keywords: List[str] = Field(default_factory=list)
    location: str = ""
    sites: List[str] = Field(default_factory=list)
    remote_only: bool = False
    visa_sponsor_required: bool = False


class TargetConfig(BaseModel):
    min_salary_usd: Optional[int] = None
    min_role_level: str = ""
    blacklisted_companies: List[str] = Field(default_factory=list)
    blacklisted_keywords: List[str] = Field(default_factory=list)


class ExperienceEntry(BaseModel):
    company: str = ""
    title: str = ""
    dates: str = ""
    bullets: List[str] = Field(default_factory=list)


class EducationEntry(BaseModel):
    degree: str = ""
    school: str = ""
    year: Optional[int] = None


class ResumeBaseConfig(BaseModel):
    summary: str = ""
    skills: List[str] = Field(default_factory=list)
    experience: List[ExperienceEntry] = Field(default_factory=list)
    education: List[EducationEntry] = Field(default_factory=list)


class LLMTaskOverride(BaseModel):
    provider: str = ""
    model: str = ""


class LLMConfig(BaseModel):
    default_provider: str = "gemini"
    fallback_chain: List[str] = Field(default_factory=lambda: ["gemini", "openai", "anthropic"])
    daily_cost_cap_usd: float = 5.0
    task_overrides: Dict[str, LLMTaskOverride] = Field(default_factory=dict)


class OutreachConfig(BaseModel):
    presets: List[str] = Field(default_factory=list)
    daily_dm_cap: int = 5


class ProfileConfig(BaseModel):
    search: SearchConfig = Field(default_factory=SearchConfig)
    target: TargetConfig = Field(default_factory=TargetConfig)
    resume_base: ResumeBaseConfig = Field(default_factory=ResumeBaseConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    outreach: OutreachConfig = Field(default_factory=OutreachConfig)


def _resolve_name(name: Optional[str]) -> str:
    if name:
        return name
    return os.getenv("JOBOT_PROFILE", "default")


def profile_config_path(name: Optional[str] = None, profile_dir: Optional[Path] = None) -> Path:
    return (profile_dir or DEFAULT_PROFILE_DIR) / f"{_resolve_name(name)}.yaml"


def load_profile_config(
    name: Optional[str] = None, profile_dir: Optional[Path] = None
) -> ProfileConfig:
    path = profile_config_path(name, profile_dir)
    if not path.exists():
        return ProfileConfig()
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(raw, dict):
            return ProfileConfig()
        return ProfileConfig(**raw)
    except Exception as exc:  # noqa: BLE001
        import logging

        logging.getLogger(__name__).warning(
            "Failed to parse profile config %s (defaults used): %s", path, exc
        )
        return ProfileConfig()


def load_llm_settings(name: Optional[str] = None) -> LLMConfig:
    """LLM settings for ModelRouter: profile YAML, env override, then defaults."""
    config = load_profile_config(name).llm
    provider_env = os.getenv("JOBOT_DEFAULT_LLM_PROVIDER")
    if provider_env:
        config.default_provider = provider_env
    return config


def task_override_map(name: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
    settings = load_llm_settings(name)
    return {task: override.model_dump() for task, override in settings.task_overrides.items()}
