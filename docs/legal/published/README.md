# Published legal HTML root

This directory is the **only** location the application may load as public
`/privacy` or `/terms` HTML.

**It is empty by design.**

Do **not** copy counsel drafts from `docs/legal/` into this folder.
Do **not** place markdown drafts here and treat them as approved.
Do **not** set `LEGAL_*_PUBLISHED_VERSION_ID` until written approval of the
**published** consumer documents exists and EXT-20 / EXT-21 publication is an
explicit owner action. The 2026-08-19 signed counsel record is written
**conditional** approval only (EXT-19 remains `applied`) and does **not** by
itself authorize copying counsel drafts here.

Until an approved HTML file exists here **and** the matching env version id is
set, `/privacy` and `/terms` fail closed with HTTP 404.

The 2026-09-11 publication-activation attempt
([`../../roadmap/evidence/EARLY_ACCESS_LEGAL_PUBLICATION_ACTIVATION_2026-09-11.md`](../../roadmap/evidence/EARLY_ACCESS_LEGAL_PUBLICATION_ACTIVATION_2026-09-11.md))
reconfirmed this directory is empty of approved HTML. A later same-day
working-draft intake
([`../../roadmap/evidence/EARLY_ACCESS_LEGAL_WORKING_DRAFT_RECONCILIATION_2026-09-11.md`](../../roadmap/evidence/EARLY_ACCESS_LEGAL_WORKING_DRAFT_RECONCILIATION_2026-09-11.md))
transcribed the August 25 package under `docs/legal/` as review-only markdown.
Those working drafts are **not** approved HTML. Assent remains counsel-ambiguous.
Do **not** treat either attempt as publication.

Sprint 44/45 remain the publication/approval gates.
