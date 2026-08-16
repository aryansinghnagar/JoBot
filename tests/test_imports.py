"""Hermetic guard against undeclared runtime dependencies.

Discovers every ``jobot.*`` module under ``src/jobot`` (plus the package root)
and imports each one. When an import fails with ``ModuleNotFoundError``, the
missing top-level import is mapped to its distribution name and checked
against ``pyproject.toml``:

* declared in ``[project].dependencies`` -> tolerated (declared requirement;
  the environment simply did not install it, which CI never allows to happen
  because the test job runs ``pip install -e .[dev]``);
* declared in any ``[project.optional-dependencies]`` group -> skipped
  (optional extra such as ``providers`` or ``scrapers`` is not installed);
* declared nowhere -> FAILS: the module carries an undeclared runtime
  dependency.

Any other import-time exception (a module with side effects such as opening a
browser or a socket at import time) also fails, because imports must be safe
in a hermetic environment.

The check is deterministic and fast: no network, no browser, no filesystem
side effects beyond normal module imports (the full walk takes ~1s).
"""

from __future__ import annotations

import importlib
import pkgutil
import re
import tomllib
from importlib.metadata import packages_distributions
from pathlib import Path

import pytest

import jobot

PYPROJECT_PATH = Path(__file__).resolve().parents[1] / "pyproject.toml"

# Import-name -> distribution-name aliases for packages whose top-level import
# differs from their PyPI distribution name. Only consulted when the package
# is NOT installed (installed packages resolve via packages_distributions()).
_IMPORT_TO_DIST_ALIASES = {
    "google": "google-genai",
    "yaml": "pyyaml",
    "bs4": "beautifulsoup4",
    "dateutil": "python-dateutil",
    "dotenv": "python-dotenv",
    "PIL": "pillow",
    "Crypto": "pycryptodome",
    "OpenSSL": "pyopenssl",
    "sklearn": "scikit-learn",
    "cv2": "opencv-python",
}


def _normalize_dist(name: str) -> str:
    """Normalize a distribution name per PEP 503."""
    return re.sub(r"[-_.]+", "-", name).lower()


def _requirement_dist_name(requirement: str) -> str:
    """Extract the distribution name from a PEP 508 requirement string."""
    match = re.match(r"\s*([A-Za-z0-9][A-Za-z0-9._-]*)", requirement)
    return match.group(1) if match else requirement.strip()


def _declared_dependencies(pyproject: Path) -> tuple[set[str], set[str]]:
    """Return (required, optional) normalized distribution-name sets."""
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    project = data["project"]
    required = {_requirement_dist_name(r) for r in project["dependencies"]}
    optional: set[str] = set()
    for group in project.get("optional-dependencies", {}).values():
        optional.update(_requirement_dist_name(r) for r in group)
    return {_normalize_dist(n) for n in required}, {_normalize_dist(n) for n in optional}


def _module_names() -> list[str]:
    """Every jobot module, deterministic (sorted), root package included."""
    names = {m.name for m in pkgutil.walk_packages(jobot.__path__, prefix="jobot.")}
    names.add("jobot")
    return sorted(names)


def _resolve_distribution(missing_root_import: str) -> str:
    """Map a missing top-level import name to its best-guess distribution."""
    if missing_root_import in _IMPORT_TO_DIST_ALIASES:
        return _IMPORT_TO_DIST_ALIASES[missing_root_import]
    installed = packages_distributions().get(missing_root_import)
    if installed:
        return sorted(installed)[0]
    return missing_root_import


_REQUIRED_DISTS, _OPTIONAL_DISTS = _declared_dependencies(PYPROJECT_PATH)
_MODULE_NAMES = _module_names()


@pytest.mark.parametrize("module_name", _MODULE_NAMES)
def test_module_imports_only_declared_dependencies(module_name: str) -> None:
    """Importing any jobot module must not need an undeclared distribution."""
    try:
        importlib.import_module(module_name)
    except ModuleNotFoundError as exc:
        missing = exc.name or "<unknown>"
        if missing.split(".")[0] == "jobot":
            pytest.fail(
                f"{module_name} is missing its own submodule {missing!r}: "
                "broken package layout or stale editable install"
            )
        root_import = missing.split(".")[0]
        dist = _normalize_dist(_resolve_distribution(root_import))
        if dist in _OPTIONAL_DISTS:
            pytest.skip(
                f"{module_name} needs optional extra providing {dist!r}; "
                "not installed in this environment"
            )
        if dist in _REQUIRED_DISTS:
            pytest.skip(
                f"{module_name} needs required dependency {dist!r}; "
                "declared in pyproject.toml but not installed here"
            )
        pytest.fail(
            f"{module_name} imports {missing!r} but distribution {dist!r} is "
            "declared neither in [project].dependencies nor in any "
            "[project.optional-dependencies] group of pyproject.toml"
        )
    except Exception as exc:  # noqa: BLE001 - report any import-time side effect
        pytest.fail(
            f"{module_name} raised {type(exc).__name__} at import time "
            f"(modules must not require live services): {exc!r}"
        )


def test_dependency_universe_is_consistent() -> None:
    """Sanity: required and optional dependency sets are non-empty and disjoint."""
    assert _REQUIRED_DISTS, "no required dependencies parsed from pyproject.toml"
    assert _OPTIONAL_DISTS, "no optional dependencies parsed from pyproject.toml"
    assert not (_REQUIRED_DISTS & _OPTIONAL_DISTS), (
        "distributions declared both required and optional: "
        f"{_REQUIRED_DISTS & _OPTIONAL_DISTS}"
    )
