# Early Access private data export

**Status:** staging-only operator procedure. It does not authorize production,
public data access, a dashboard, or a new HTTP endpoint.

## Existing retrieval path

`scripts/export_early_access.py` reads the configured SQLAlchemy operational
store and writes these fields to CSV: full name, email, normalized email,
country, shopping interest, source, UTM attribution, referrer, confirmation
status, and created/updated timestamps.

The command requires `--out`. It refuses repository destinations, existing
files, and symlink destinations; never writes registrations to stdout;
neutralizes spreadsheet formulas; creates the file as owner-only `0600`; and
removes a partial file if export fails.

## Secure operator procedure

1. Work only in the AWS staging account and confirm the target is the private
   staging RDS database.
2. Use an approved AWS administrator session and the AWS Session Manager
   plugin. Start a Session Manager port-forwarding session through the
   SSM-online staging host to the private staging RDS endpoint. Do not open RDS
   publicly and do not add an SSH ingress rule.
3. Obtain the AWS-managed staging RDS credential through Secrets Manager in the
   local operator session. Do not paste it into chat, a ticket, shell history,
   GitHub Actions, or SSM command parameters.
4. Set `APP_ENV=staging`, `PERSISTENCE_BACKEND=sqlalchemy`, and a temporary
   `DATABASE_URL` that uses the local forwarded port. Run:

   ```text
   python scripts/export_early_access.py --out <new-private-path>/piqsavi-early-access-<date>.csv
   ```

5. Confirm the output mode is `0600`, open it only on the founder/operator
   device, and close the port-forwarding session immediately after use.
6. Remove the temporary database environment value from the shell and store or
   delete the CSV according to the approved privacy/retention policy once that
   policy exists.

## Fail-closed rules

- Never use stdout, terminal copy/paste, CI logs, GitHub artifacts, public S3,
  email, or the application API for exports.
- Never run against a production identifier unless a separately authorized
  production procedure exists.
- Stop if the Session Manager plugin, staging target identity, private tunnel,
  or approved AWS session cannot be verified.
- Production should replace master-database access with a least-privilege,
  audited read-only operator role before public launch.

## Current limitation

The local audit workstation did not have the Session Manager plugin installed,
so no real-registration export was performed during readiness QA. Repository
and persistence tests verify the export fields and safety behavior without
printing or downloading signup PII.
