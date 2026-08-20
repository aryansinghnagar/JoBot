# Release Process

This document describes how JoBot releases are cut, signed, and
published. It is the canonical reference for the maintainer on duty.

## 1. Version policy

JoBot follows [Semantic Versioning 2.0.0](https://semver.org/). The
canonical version is in `pyproject.toml` at the project root; all
other manifests (`package.json`, `gui/package.json`,
`gui/src-tauri/tauri.conf.json`, `gui/src-tauri/Cargo.toml`,
`gui/src-tauri/Cargo.lock`, `package-lock.json`) are kept in sync by
`scripts/sync_versions.py`.

* `0.x.y` — pre-1.0 development. Breaking changes land on `main`.
  `0.2.x` is the current Active line (see `SECURITY.md`).
* `1.0.0` — first stable release. After 1.0, SemVer rules apply
  strictly: backwards-incompatible changes require a major bump.
* Tags are the source of truth. Every published artifact (PyPI wheel,
  desktop installer) is built from a tag of the form `v0.2.0`,
  `v0.2.1`, …, never from a branch tip.

Run `python scripts/sync_versions.py --check` before tagging to
catch drift; the CI `docs-lint` and `supply-chain` jobs enforce this
on every pull request.

## 2. Pre-release checklist

1. **All tests green on `main`.** The CI matrix covers Ubuntu, macOS,
   and Windows × Python 3.11 / 3.12 / 3.13. Watch for intermittent
   OS-specific failures.
2. **Lint and types clean.** `ruff check src/`, `ruff format --check src/`,
   and `mypy src/ --ignore-missing-imports` must all pass.
3. **Supply chain gates green.** The `Security Gates` workflow runs
   `pip-audit --strict` on the runtime dependency set and `npm audit
   --audit-level=high` on the GUI tree. Both must pass.
4. **Changelog updated.** `CHANGELOG.md` must have an entry under the
   version being released. Move items from `[Unreleased]` to a new
   `[0.2.x] — YYYY-MM-DD` section.
5. **Audit remediation log updated.** `AUDIT_REMEDIATION.md` lists
   every finding fixed in the current cycle; verify the count matches
   what was actually shipped.

## 3. Bumping the version

```bash
# 1. Pick the next version (e.g. 0.2.1 for a patch release).
python scripts/bump_version.py 0.2.1

# 2. Verify all 7 manifests are in sync.
python scripts/sync_versions.py --check

# 3. Update CHANGELOG.md and AUDIT_REMEDIATION.md (manual).

# 4. Commit the version bump.
git commit -am "release: v0.2.1"
```

## 4. Tagging the release

```bash
# Annotated, signed tag (use -s if your GPG key is configured).
git tag -a v0.2.1 -m "Release v0.2.1"

# Push the tag. This triggers .github/workflows/release-desktop.yml
# and .github/workflows/publish.yml.
git push origin v0.2.1
```

Tag push is what fires the release pipeline. **Do not push the tag
until the pre-release checklist is fully green.**

## 5. Building desktop installers (release-desktop.yml)

The `release-desktop.yml` workflow runs on every `v*` tag push and on
`workflow_dispatch`. It builds signed installers for four targets:

| Platform              | OS             | Target                          | Artifact            |
| --------------------- | -------------- | ------------------------------- | ------------------- |
| `windows-x86_64`      | `windows-latest`  | `x86_64-pc-windows-msvc`      | `.msi` / `.exe` (signtool-signed when `WINDOWS_CERTIFICATE_BASE64` is set) |
| `macos-arm64`         | `macos-14`     | `aarch64-apple-darwin`          | `.dmg` (codesigned + notarised when `MACOS_CERTIFICATE_BASE64` is set) |
| `macos-x86_64`        | `macos-13`     | `x86_64-apple-darwin`           | `.dmg` (same as above) |
| `linux-x86_64`        | `ubuntu-latest`| `x86_64-unknown-linux-gnu`      | `.AppImage` / `.deb` (no code signing on Linux) |

### Code signing (Phase B1, JOB-SEC-009)

macOS and Windows installers are signed before they are uploaded as
release artifacts. Certificates / notarisation credentials are stored
as GitHub Actions secrets (repository → Settings → Secrets and
variables → Actions):

#### macOS

| Secret name                    | Description                                                  |
| ------------------------------ | ------------------------------------------------------------ |
| `MACOS_CERTIFICATE_BASE64`     | Developer ID Application certificate (`.p12`, base64)       |
| `MACOS_CERTIFICATE_PASSWORD`   | Password for the `.p12`                                       |
| `MACOS_SIGNING_IDENTITY`       | "Developer ID Application: Your Name (TEAMID)"              |
| `MACOS_NOTARY_API_KEY_BASE64`  | App Store Connect API key (`.p8`, base64)                    |
| `MACOS_NOTARY_API_KEY_ID`      | API key ID (10-char alphanumeric)                            |
| `MACOS_NOTARY_API_ISSUER_ID`   | API issuer ID (UUID)                                          |

The workflow imports the `.p12` into a temporary keychain, sets
`APPLE_SIGNING_IDENTITY` so Tauri 2's bundler invokes `codesign`
during the build, then runs `xcrun notarytool submit --wait` +
`xcrun stapler staple` on each `.dmg`.

#### Windows

| Secret name                       | Description                                            |
| --------------------------------- | ------------------------------------------------------ |
| `WINDOWS_CERTIFICATE_BASE64`      | Code-signing certificate (`.pfx`, base64)              |
| `WINDOWS_CERTIFICATE_PASSWORD`    | Password for the `.pfx`                                 |

The workflow decodes the `.pfx`, imports it into the current user's
personal certificate store, and signs every `.msi` / `.exe` with
`signtool` (SHA-256 + RFC-3161 timestamp from DigiCert).

If any secret is absent (e.g. forked builds, dev `workflow_dispatch`
runs), the signing step is skipped and unsigned artifacts are still
uploaded so contributors can test locally. Production releases MUST
have all secrets set — verify the workflow log shows the signing step
ran (look for `Signing <path>` / `Submitting <path> for notarisation`).

## 6. Publishing to PyPI (publish.yml)

The `publish.yml` workflow runs on tag push and builds a source
distribution + wheel via `python -m build`. It publishes to PyPI
using trusted publishing (OIDC) — no API token stored as a secret.
Verify the package appears at `https://pypi.org/project/jobot/` and
that `pip install jobot==0.2.1` works in a clean virtualenv.

## 7. Creating the GitHub Release

1. Go to <https://github.com/aryansinghnagar/JoBot/releases/new>.
2. Select the tag you just pushed (`v0.2.1`).
3. Title: `Release v0.2.1`.
4. Body: paste the relevant section from `CHANGELOG.md`.
5. Attach the desktop installer artifacts from the
   `release-desktop.yml` run (download each
   `jobot-desktop-<platform>` artifact zip and re-upload the installers
   inside it; GitHub does not auto-attach workflow artifacts to a
   release).
6. Check **Set as the latest release** if this is the new stable line.
7. Publish.

## 8. Post-release

1. Bump the version in `pyproject.toml` to the next `-dev` (e.g.
   `0.2.2.dev0` or `0.3.0.dev0` if a minor bump is planned).
2. Add a new `[Unreleased]` section at the top of `CHANGELOG.md`.
3. Update `SECURITY.md` supported-versions table if the Active line
   changed (e.g. when 0.3.x ships, mark 0.2.x as Maintenance).
4. Commit: `post-release: bump to 0.2.2.dev0`.

## 9. Rollback

If a release ships with a critical defect:

1. **Do not delete the tag.** SemVer requires that published versions
   are immutable; yanking is the right tool.
2. Yank the PyPI release: `python -m twine yank jobot==0.2.1`.
3. Cut a patch release (`0.2.2`) following the same process above.
4. Update `SECURITY.md` to mark the yanked version as "Yanked —
   upgrade to <fixed version>".

Desktop installers cannot be yanked in the same way — publish a
GitHub Release Note warning and ship a patched installer as soon as
possible.

## 10. Security release process

For a vulnerability fix that warrants a CVE:

1. Cut the fix on a private branch (no PR until the advisory is
   published).
2. Coordinate disclosure via GitHub Security Advisories
   (`https://github.com/aryansinghnagar/JoBot/security/advisories/new`).
3. Once the advisory is published and CVE assigned, ship the fix as
   a patch release following the standard process above; reference
   the CVE ID in `CHANGELOG.md` and `SECURITY.md`.

## 11. Pointers

* `scripts/bump_version.py` — bumps the version in `pyproject.toml`
  and re-runs `sync_versions.py` to propagate.
* `scripts/sync_versions.py` — verifies all 7 manifests agree.
* `scripts/check_master_plan_citations.py` — verifies
  `MASTER_PLAN_EXPANDED.md` section references resolve (CI gate).
* `.github/workflows/release-desktop.yml` — desktop installer pipeline.
* `.github/workflows/publish.yml` — PyPI publish pipeline.
* `.github/workflows/security-gates.yml` — `pip-audit` + `npm audit`
  + `gitleaks` gates.
* `.github/workflows/ci.yml` — primary test matrix.
