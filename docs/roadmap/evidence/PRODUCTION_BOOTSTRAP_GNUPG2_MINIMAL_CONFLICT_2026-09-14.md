# Production bootstrap — AL2023 gnupg2-minimal conflict (2026-09-14)

**Resulting state:** `AL2023 GPG BOOTSTRAP COMPATIBILITY FIX READY FOR OWNER REVIEW — NO AWS MUTATION PERFORMED`

**Scope:** Code, tests, and documentation only. This change does **not** apply Terraform, replace the live production EC2 host, mutate AWS, change DNS, rerun Deploy Production, or merge.

**Verified `origin/main` at branch creation:** `630c175612e36e8fff0da537cfc2a7eaddb7d0d7`

## Incident (live host, not mutated by this PR)

New production EC2 `i-0994a8ce7a650535e` is running AMI
`al2023-ami-2023.12.20260909.0-kernel-6.18-x86_64` (non-minimal standard AL2023).
Instance status checks are OK. SSM `PingStatus = Online` and `amazon-ssm-agent`
is active. Production bootstrap marker `/opt/dealbrain/bootstrap.ok` does **not**
exist. Docker is inactive.

`/var/log/dealbrain/bootstrap.log` shows the exact failure:

1. Standard AL2023 already has `gnupg2-minimal-2.3.7-1.amzn2023.0.9.x86_64`.
2. Bootstrap requests full `gnupg2` in the fail-closed `dnf -y install` transaction.
3. DNF aborts because `gnupg2-minimal` conflicts with `gnupg2`.
4. The package transaction therefore stops **before Docker** starts
   (`systemctl enable docker` / `systemctl start docker` never run).
5. `bootstrap.ok` is never written.

This is a package-set conflict on standard AL2023, not a cloud-init, AMI-minimal,
or SSM-agent failure. SSM was already online, which is why `bootstrap.log` could
be read.

## Root cause in repository

`infra/ec2/user_data/production.sh` (and the same pattern in
`infra/ec2/user_data/staging.sh`) listed `gnupg2` in the unconditional AL2023
package install:

```
dnf -y install \
  docker \
  ...
  gnupg2
```

The script later requires `command -v gpg`. Standard AL2023 already provides
`gpg` via `gnupg2-minimal`. Installing full `gnupg2` is unnecessary and
fail-closed-aborts the whole transaction.

## Compatibility fix (this PR)

| Change | Behavior |
|--------|----------|
| Runtime package list | Keep fail-closed install of `docker`, `awscli`, `jq`, `python3`, `tar`, `gzip`, `findutils`, `util-linux`, `coreutils`. Do **not** request full `gnupg2`. Leave `dnf -y update \|\| true` unchanged. |
| `gpg` prerequisite | If `gpg` already exists, keep the AL2023 provider package and do not replace it. Only install `gnupg2-minimal` when `gpg` is genuinely absent. Then fail closed if `command -v gpg` still fails. |
| Docker start | Still happens only after the package install and GPG prerequisite. |
| Compose plugin GPG | Exact Docker Inc fingerprint pin, fingerprint verification before trust/import, `gpgcheck=1`, `repo_gpgcheck=1`, repo normally disabled, `includepkgs=docker-compose-plugin`, Amazon `docker` engine retained. No `docker-ce` / unsigned GitHub Compose binary / convenience script. |
| Forbidden workarounds | No `--allowerasing`, package removal, `rpm --nodeps`, or disabled signature checking. |

## Owner follow-up (not this PR)

After merge and independent review, replace or re-bootstrap the current
production host out-of-band so the corrected `user_data` actually runs.
This PR does not mutate AWS.
