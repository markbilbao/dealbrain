# Published legal HTML root

This directory is the **only** location the application may load as public
`/privacy` or `/terms` HTML.

**It is empty by design.**

Do **not** copy counsel drafts from `docs/legal/` into this folder.
Do **not** place markdown drafts here and treat them as approved.
Do **not** set `LEGAL_*_PUBLISHED_VERSION_ID` until EXT-19 written approval
exists and EXT-20 / EXT-21 publication is an explicit owner action.

Until an approved HTML file exists here **and** the matching env version id is
set, `/privacy` and `/terms` fail closed with HTTP 404.

Sprint 44/45 remain the publication/approval gates.
