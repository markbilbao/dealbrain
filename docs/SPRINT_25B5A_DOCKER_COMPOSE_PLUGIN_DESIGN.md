# Sprint 25b.5a — Docker Compose Plugin on Amazon Linux 2023 (Staging)

**Status:** Implemented in repository (live EC2 replace / AWS mutation out of scope)  
**Scope:** Staging host bootstrap only — production `user_data` remains empty  

## Decision

Temporarily enable the Docker Inc **RHEL 9 stable** RPM repository, install **only** `docker-compose-plugin` after Docker GPG fingerprint verification, keep the Amazon Linux 2023 `docker` engine, then disable the third-party repo (`enabled=0`) while preserving `includepkgs=docker-compose-plugin`.

## Why

- AL2023 default repos do not ship `docker-compose-plugin` (confirmed in Sprint 25b.4c).
- Unsigned GitHub Compose binaries are forbidden.
- Full `docker-ce` / `--allowerasing` would replace or conflict with Amazon’s engine and is rejected.
- Compose-only Docker Inc RPM metadata requires `/bin/sh` only (no `docker-ce` dependency).

## Hard constraints

| Requirement | Enforcement |
|-------------|-------------|
| Install only `docker-compose-plugin` | `dnf -y install "$PLUGIN_PKG"`; repo `includepkgs=` |
| Keep Amazon Docker Engine | Continue AL2023 `dnf install docker`; post-assert `rpm -q docker` |
| Never install `docker-ce` / `docker-ce-cli` | Script denylist + post-check `! rpm -q` |
| Never use `--allowerasing` | Absent from installer; unit-tested |
| Docker Inc signed RPMs only | `gpgcheck=1` + `repo_gpgcheck=1`; no GitHub binary URLs |
| Exactly one primary GPG fingerprint | Parse `pub:`/`fpr:` pairs; reject empty, malformed, or multi-key material before `rpm --import` |
| Verify GPG fingerprint before trust | Pin `060A 61C5 1B55 8A7F 742B 77AA C52F EB6B 621E 9F35`; abort on mismatch before `rpm --import` |
| Failure-path repo disable | EXIT trap restores locked disabled repo after enable; preserves original failure status |
| Locked disabled state | `enabled=0` + `includepkgs=docker-compose-plugin` + `gpgcheck=1` + `repo_gpgcheck=1` |
| Idempotent installer | Skip when plugin + Amazon docker + locked disabled repo already OK |
| Bootstrap fail-closed | No `bootstrap.ok` unless `docker compose version` succeeds |
| Production untouched | Staging `user_data` / staging docs / staging tests only |

## Trust boundary

| Component | Source of truth |
|-----------|-----------------|
| Compose plugin | `https://download.docker.com/linux/rhel/9/$basearch/stable` |
| Docker Engine | Amazon Linux 2023 `docker` RPM (default repos) |
| GPG fingerprint | `060A61C51B558A7F742B77AAC52FEB6B621E9F35` |

## GPG validation (exact one-key)

Before `rpm --import`:

1. Download Docker Inc key material to a temp file.
2. Extract **primary** fingerprints only (`fpr:` immediately following each `pub:`; ignore subkey fingerprints).
3. Require **exactly one** primary fingerprint.
4. Normalize (strip spaces/colons; uppercase) and require it to be 40 hex chars.
5. Require exact match with `060A61C51B558A7F742B77AAC52FEB6B621E9F35`.
6. On empty, malformed, multiple-key, or mismatched input: fail closed **before** import.
7. Install and import only the same verified key file.

## Failure-path repository disable

Once the installer intends to enable the Docker Inc repo:

1. Install an `EXIT` trap (`_cleanup_docker_repo`).
2. Mark `_DOCKER_REPO_ENABLE_ACTIVE=1`, then write the repo with `enabled=1` (still `includepkgs`, `gpgcheck=1`, `repo_gpgcheck=1`).
3. Run `dnf -y install docker-compose-plugin`.
4. On **any** exit (install failure, assert failure, or success), the trap restores the locked disabled configuration:
   - `enabled=0`
   - `includepkgs=docker-compose-plugin`
   - `gpgcheck=1`
   - `repo_gpgcheck=1`
5. Trap behavior for status:
   - Preserve the original non-zero exit status.
   - Cleanup must not mask the original error.
   - Cleanup failure is reported on stderr and may escalate success→failure, but never converts failure→success.
6. Successful runs also finish with the repo locked and disabled (`write_docker_repo 0` plus the EXIT trap).

`repo_locked_disabled` requires all four invariants above and rejects weakened configs (for example missing `repo_gpgcheck=1`).

## Bootstrap sequence

1. AL2023 packages (`docker`, `awscli`, `jq`, `gnupg2`, …)
2. `systemctl enable --now docker`; assert Amazon `docker`
3. Idempotence short-circuit (compose OK + plugin RPM + Amazon docker + locked disabled repo)
4. Fetch Docker GPG → exactly-one primary fingerprint gate → `rpm --import`
5. Arm fail-safe EXIT restore; write locked `docker-ce.repo` (`enabled=1`, `includepkgs=docker-compose-plugin`)
6. `dnf -y install docker-compose-plugin` (no `--allowerasing`)
7. Rewrite repo with `enabled=0` (keep `includepkgs` + gpg knobs); EXIT trap re-asserts the same
8. Assert compose + Amazon engine + absence of `docker-ce*`; write entrypoint + `bootstrap.ok`

## Files

| Path | Role |
|------|------|
| `scripts/deploy/host/install-compose-plugin.sh` | Reviewed idempotent installer (source of truth) |
| `infra/ec2/user_data/staging.sh` | Embeds + runs installer; hard-gates Compose before `bootstrap.ok` |
| `tests/unit/test_sprint25b3_staging_deploy.py` | Signed-path / denylist / fingerprint / fail-safe cleanup / embed-sync tests |

## Maintenance

```bash
dnf -y --enablerepo=docker-ce-stable update docker-compose-plugin
# Re-assert fingerprint/repo lockdown, then ensure enabled=0
docker compose version
```

When Amazon ships a native plugin package, prefer migrating off the Docker Inc trust root and remove `/etc/yum.repos.d/docker-ce.repo`.

## Residual risk

Docker Inc is an additional upstream trust root beside Amazon. Accepted because unsigned binaries are worse and AL2023 does not yet ship the plugin. Compensated by exact one-key fingerprint pin, compose-only `includepkgs`, fail-safe repo disable (including failure paths), and `repo_gpgcheck=1` in the locked disabled state.

## Explicit non-scope

- No Terraform plan/apply
- No EC2 replace
- No AWS mutations
- No production Terraform / `user_data` changes
