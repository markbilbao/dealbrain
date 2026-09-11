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
    Mobile / 390: object-position 60% 42% plus the approved 4:5 crop

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
    1020 × 242, literal pixel crop of the master at (196, 318)–(1216, 560)
    SHA-256 20afee9c07a0c720474b3a391d8a9f6c9a1d5c4347e2dd5bc5866c304615d452
    No redraw, no CSS object-view-box / clip / negative positioning.
