# Search Console — explicit deferral

EXT-29 remains `not_started`.

This record does not verify a Search Console property, does not submit a sitemap to Google, and does not claim indexing or ranking.

Not done:

- no Google API call
- no Search Console verification token
- no DNS or HTML verification file
- no ranking or coverage claim

Private UUID decision routes stay `noindex`.

Sprint 39 acceptance allows Search Console to be deferred with no ranking claim. Setup, if it happens, is a later owner action. It is not part of Sprint 39.2.

The 2026-10-02 closure-readiness audit confirms that this deferral still satisfies the Sprint 39 acceptance alternative. EXT-29 stays `not_started`. That audit does not call Google Search Console and does not add a verification token.
