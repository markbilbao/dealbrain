SOURCE-ASSET GATE — PiqSavi Early Access

This file is documentation only. It must not be served as a public static asset.

Hero photography:
  The approved photographic master from the final Early Access handoff
  package is installed and served.

  Source of truth (unchanged PNG master):
    app/static/early_access/assets/piqsavi-hero-photographic-master.png
    1672 × 941, RGB PNG
    SHA-256 5773da03035e1bdea6f1a27a93aa2081789c224e66db7976744526c0fa4a4270

  Web derivative (byte-identical to the handoff WebP):
    app/static/early_access/assets/piqsavi-hero-photographic-master.webp
    SHA-256 b5808a86478e7fe7c3e2efcb87f9144da9564fc25dc13a66294e4e97d777295f

  Approved mobile 4:5 crop (derived from the same master):
    app/static/early_access/assets/piqsavi-hero-mobile-crop-752x941.png
    752 × 941, RGB PNG
    SHA-256 8233c03be73f23ee5ad430f15320dfd770eeae302910cbc361fbbd1cae303d9d

  Crop / focal-point application (Hero_Crop_Focal_Point_Specification.txt):
    Desktop / 1440 / 1024: object-position 58% 42%
    Tablet portrait / 768: object-position 59% 42%
    Mobile / 390: object-position 60% 47% plus the approved 4:5 crop

  The previous CSS gradient placeholder has been removed. The approved
  photographic source is what the landing page serves.

Logo:
  The exact approved PiqSavi master is installed at
  app/static/early_access/assets/piqsavi-logo.png
  (copied from the owner-supplied master PNG for the approved-design
  reconciliation; not redrawn or approximated).
  SHA-256 5189150b27fbd6a374ce8cc023ef735e5a5c752e667d45d716fdaa8900dfb42f
  The master file is kept intact and is not CSS-cropped at render time.

  Header / footer / signup use a derived icon+wordmark lockup:
    app/static/early_access/assets/piqsavi-logo-lockup.png
    797 × 167 RGBA
    Complete circular icon: literal pixels (197, 318)–(523, 669), uniformly
    scaled to wordmark cap-height so the mark is not cropped.
    Wordmark: literal pixels (594, 383)–(1216, 550). Tagline omitted.
    20px transparent gap. Icon and wordmark aspect ratios unchanged.
    SHA-256 f5d43f1d184b7a79fada0eedf2db61d3213a39acb02672cc4060c5f5638e47c2
    No redraw, no CSS object-view-box / clip / overflow / negative positioning.
