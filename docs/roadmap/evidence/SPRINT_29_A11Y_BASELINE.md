# Sprint 29 Accessibility Baseline Checklist

**Status:** Engineering baseline recorded. Not a signed third-party audit.  
**Surfaces:** Results, Compare, Why, Ask overlay, location dialog, account/auth/support pages.

| Requirement | Implementation | Automated evidence |
|---|---|---|
| Skip link | `.skip-link` on decision and account documents | `test_sprint29_accessibility.py` |
| Semantic HTML | `header` / `nav` / `main` / `footer` / labeled forms | document-route tests |
| Dialog semantics | Ask overlay `role="dialog"` `aria-modal="true"` `aria-labelledby` | same |
| Location dialog | native `<dialog>` | Product Foundation pages |
| Keyboard | Ask submit, chips, nav toggle, market select, account forms | JS + HTML |
| Focus trap | Tab cycles inside Ask panel | `focusableIn` in `consumer.js` |
| Focus restore | Last opener restored on Ask close | `askRestoreFocus` |
| Escape / close | Escape closes Ask and location; labeled close button | `initDialogEscape` |
| Live announcements | Ask body `aria-live="polite"`; account `role="status"` | HTML tests |
| Reduced motion | `prefers-reduced-motion` disables smooth scroll / spinner | CSS |
| Zoom / reflow | fluid `min()` widths; no fixed viewport lock beyond `viewport-fit=cover` | CSS |
| Screen-reader labels | Ask inputs, close, account, market select | HTML |
| Mobile safe area | `env(safe-area-inset-*)` on Ask dock | CSS test |
| Keyboard-open composer | `visualViewport` sets `--kb-inset` and `.is-keyboard-open` | JS test |
| Ask insertion height | 80px desktop / 72px mobile | `test_ask_insertion_heights_match_manifest` |

Owner sign-off of this checklist is still required for Sprint 29 close. This file records the engineering baseline only.
