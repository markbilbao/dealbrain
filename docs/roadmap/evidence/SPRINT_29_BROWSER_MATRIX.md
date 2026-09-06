# Sprint 29 Supported-Browser Matrix

**Status:** Recorded engineering target. Not a completed lab pass on every cell.  
**Frontend:** FastAPI HTML + shared CSS + vanilla ES modules.

| Browser | Desktop | Mobile | Notes |
|---|---|---|---|
| Chromium (current 2 versions) | Required | Required (Android Chrome) | Primary Ask overlay / `visualViewport` path |
| Firefox (current 2 versions) | Required | Optional | Native `<dialog>` + ES modules |
| Safari (current 2 versions) | Required | Required (iOS Safari) | Safe-area and keyboard-open dock are iOS-critical |
| Edge (current) | Required | n/a | Chromium-compatible |
| Samsung Internet | n/a | Best-effort | Not a launch blocker if Chrome Android passes |

## Must-pass behaviors

- Results / Compare / Why + persistent Ask
- Escape, focus trap, restore
- Market-selection shell
- Account register / login / export / delete presentation
- UUID pages remain noindex
- Reduced motion does not hide content

## Out of scope

- Internet Explorer
- Native apps
- Node/React production builds
- Pixel-perfect Sprint 44 artwork lab (Sprint 44)

Staging HTML/CSS/JS locks (skip link, dialog, Escape/focus-trap source, Ask 80/72) were verified on Deploy Staging #27. An interactive multi-browser lab pass is still not recorded here and is not a signed a11y audit.
