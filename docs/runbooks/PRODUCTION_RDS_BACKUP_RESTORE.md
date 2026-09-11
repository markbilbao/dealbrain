# Production RDS backup and restore (Early Access)

**Audience:** owner/ops after production Terraform is applied.  
**Scope:** durable Early Access registration data on production RDS.  
**This document does not claim a restore rehearsal occurred.** A future
owner-controlled rehearsal remains required before public cutover.

Do not run these steps from GitHub Actions. Do not delete or modify the live
production instance as part of rollback. Application rollback restores a
previously approved **image digest** only; it must not `alembic downgrade`,
drop databases, or call `rds:DeleteDBInstance` / `rds:ModifyDBInstance`.

## What Terraform models (not yet applied)

Production RDS (`dealbrain-production-postgres`) is defined with:

| Control | Value |
|---------|--------|
| Engine | PostgreSQL 16.x |
| Storage | Encrypted (gp3) |
| Public accessibility | `false` (private subnets only) |
| Multi-AZ | `true` |
| Deletion protection | `true` |
| Automated backup retention | **30 days** (minimum; variable rejects `< 30`) |
| Final snapshot on destroy | required (`skip_final_snapshot = false`) |
| Copy tags to snapshots | `true` |
| Master password | AWS-managed Secrets Manager (ARN only in Terraform) |

Automated backups alone are not an operator procedure. Use them **and** the
manual snapshot / restore-to-new-instance steps below.

## Backup retention

- **Automated backups:** 30 days (RDS backup window; point-in-time restore within
  retention).
- **Manual snapshots:** retained until the owner deletes them. Take one before
  first public traffic and before any risky schema change.
- **Final snapshot:** Terraform will demand a named final snapshot if the
  instance is ever destroyed (`dealbrain-production-final`). Do not disable this.

## Manual snapshot before cutover

Owner/ops, after RDS is live and **before** DNS cutover:

```bash
# Read-only identity check — confirm this is production, not staging.
aws rds describe-db-instances \
  --db-instance-identifier dealbrain-production-postgres \
  --query 'DBInstances[0].{Id:DBInstanceIdentifier,MultiAZ:MultiAZ,DeletionProtection:DeletionProtection,BackupRetention:BackupRetentionPeriod,Public:PubliclyAccessible}'

aws rds create-db-snapshot \
  --db-instance-identifier dealbrain-production-postgres \
  --db-snapshot-identifier dealbrain-production-pre-cutover-$(date -u +%Y%m%dT%H%M%SZ)
```

Record the snapshot identifier in the cutover evidence pack. Do not print
master passwords. Confirm the snapshot status becomes `available` before
continuing.

## Restore-to-new-instance procedure

Restore never overwrites the live producer. Restore to a **new** instance in
the production VPC private subnets, verify Early Access rows, then destroy the
throwaway instance.

1. Choose a snapshot (manual pre-cutover snapshot **or** an automated snapshot
   identifier from `describe-db-snapshots`).
2. Restore:

```bash
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier dealbrain-production-restore-rehearsal \
  --db-snapshot-identifier <SNAPSHOT_ID> \
  --db-subnet-group-name dealbrain-production-db \
  --vpc-security-group-ids <production-rds-sg> \
  --no-publicly-accessible \
  --no-deletion-protection
```

3. Wait until `available`. Do not attach this instance to the production ALB.
4. From a break-glass host in the production VPC (not GitHub):

```bash
# Use the AWS-managed secret ARN for the *restored* instance (new ARN).
# Do not log the password. Early Access rows live in operational_entities.
psql "postgresql://dealbrain@<restore-endpoint>:5432/dealbrain" \
  -c "SELECT COUNT(*) FROM operational_entities WHERE store = 'early_access.registrations';"
```

   Exact store key is `early_access.registrations` on `operational_entities`.
   Confirm counts and a sample of non-PII fields (id, created_at) match the
   live producer taken just before snapshot. Do not export email lists to
   tickets or chat.
5. Destroy the throwaway instance after verification:

```bash
aws rds delete-db-instance \
  --db-instance-identifier dealbrain-production-restore-rehearsal \
  --skip-final-snapshot
```

Do **not** run `delete-db-instance` against `dealbrain-production-postgres`.

## Verification of restored Early Access registration data

Minimum checks on the restore instance:

- Instance is PostgreSQL, not publicly accessible, in the production VPC.
- Schema revision matches the snapshot’s application revision (or is a known
  forward-compatible revision).
- `COUNT(*)` of `operational_entities` rows with
  `store = 'early_access.registrations'` equals the pre-snapshot count.
- Spot-check that a known test registration (if one exists) is present.
- Application must still fail closed if pointed at localhost / sqlite / compose
  aliases — never assemble production `DATABASE_URL` from the restore host by
  accident for public traffic.

## Rollback interaction

| Action | RDS |
|--------|-----|
| Deploy Production | May run Alembic **upgrade** only on the live instance |
| Rollback Production | Image digest + host compose only. `alembic current` for evidence. **No** downgrade, **no** snapshot restore, **no** delete/modify RDS |
| Disaster recovery | Owner restores a snapshot to a **new** instance, re-points host `DATABASE_URL` only under a separate authorized procedure, then health-checks |

If rollback evidence cannot be `rollback_ok` because the target digest’s
migrations are incompatible with the current schema, **fail closed**. Do not
downgrade the database to force the image back.

## Honest status

| Item | Status |
|------|--------|
| Backup/restore procedure documented | This file |
| Automated backups modeled in Terraform | Yes (30-day retention) |
| Terraform applied / RDS live | **No** (owner apply required) |
| Manual pre-cutover snapshot taken | **No** |
| Restore rehearsal executed | **No — still required** |
