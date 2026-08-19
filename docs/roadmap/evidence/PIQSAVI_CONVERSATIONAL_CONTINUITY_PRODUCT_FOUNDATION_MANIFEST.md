# PiqSavi Conversational Continuity — Product Foundation Authority Manifest

**Manifest status:** OWNER APPROVED FOR DEVELOPMENT

**Approval date:** 2026-08-19 Asia/Manila

**Scope:** Conversational Continuity Product Foundation artwork only

**Implementation owner:** Sprint 29

**Launch verification:** CC-01 under EC-02 / EC-22

**Source package:** `PiqSavi_Conversational_Continuity_Strict_Pixel_Consistency_REVIEW`

## Supersession

The owner approval recorded on 2026-08-19 supersedes only the status line
`REVIEW ONLY — NOT FOR DEVELOPMENT` in `README_REVIEW_ONLY.txt`.

The legacy README remains in the source package as provenance evidence and must
not be edited or treated as the current authority.

This manifest is the controlling development authority for the artwork listed
below. It does not approve implementation completion or public launch.

## Immutability rule

The listed artwork files are approved exactly at the recorded SHA-256 values.

Implementation may reproduce the approved UI in code but must not modify,
overwrite, crop, scale, recolor, recomposite, regenerate, or silently replace
the approved source artwork.

Any changed hash, replacement artwork, or changed insertion geometry requires
a new owner-approved manifest.

## Pixel-consistency invariants

- Desktop Ask PiqSavi insertion row: exactly 80 px.
- Mobile Ask PiqSavi insertion row: exactly 72 px.
- Original header pixels remain exact.
- Every original pixel below the inserted row remains exact and is translated
  only by the approved insertion height.
- No base-master card, typography, price, PiqScore, merchant, freshness,
  navigation, or layout redesign is authorized.
- Conversation overlays and mobile sheets remain separate interaction states.
- Research states must not display fabricated execution counts.
- Updated Results returns to the exact approved Results shell with Ask PiqSavi
  retained.

## Approved artifact-set checksum

`approved_artifact_set_sha256` is computed over UTF-8 lines ordered
lexicographically by filename:

`<sha256><two spaces><filename><LF>`

for every approved file below, excluding `README_REVIEW_ONLY.txt`.

approved_artifact_set_sha256:
`98a0faa4aede278a39e28e3462fc76bfb7a0813faaad760fc09e71067b11e5ed`

## Approved artifact inventory

```text
efe759b09eeb529cf75bbb37d4482967defc107267e83aa0560b61672c4e0bfb  A_Results_Desktop_Exact_Master_Plus_Ask_PiqSavi.png
dc712a162c429e1984ac462e98421c229a68bf4df135f7c66666b6ca72907b26  B_Compare_Desktop_Exact_Master_Plus_Ask_PiqSavi.png
06085f6efcee6f454ddb5b2d15ad0360afa2bc297386d8b7e052d8b5b6dc28b3  C_Why_Best_Piq_Desktop_Exact_Master_Plus_Ask_PiqSavi.png
7dcb0ccabe9e4d8528ee1ef426b1c98d5e253f15d478022d3e3dd66a7d51c79b  D1_Desktop_Conversation_Empty.png
c027f907a306e18d6eaccf4bf2aad21bff3d24100bc519d0288b833e0ce8d503  D2_Desktop_Conversation_Answer.png
5f4ce831bd6da782a1b8774f8610f30735dd5ff63178f17f61db2a1741ea8005  D3_Desktop_Conversation_MultiTurn.png
2ee904ce3b0cfd269c1fc5dce701624961ae67609c3b1c0f033d9c1bddc2c6b6  D4_Desktop_Research_Again_Confirmation.png
3047ae640ecacf74acd04cace8e685df4e4a9b52b7a917cd3113b23bb3059ceb  D5_Desktop_Insufficient_Evidence.png
1a22468d3b90cdf4edadb56e1f4438e09fb312d50cb9f65df475d021865540e9  D6_Desktop_Conversation_Technical_Error.png
29a8841114d19bdc20b03c3e47a8b8b5516c95ebbaf378c82aae8e98723048c1  E1_Mobile_Conversation_Sheet_Empty.png
79180fb4a5772f4a97a8715b7522bf0d10b5e5bea54dec72902c1eff2c35a38c  E2_Mobile_Conversation_Sheet_MultiTurn.png
f803548bbbdda63a3bdf8c2b664f401a7f70d768212a34e857c4d34c4deacfc1  E3_Mobile_Conversation_Sheet_Keyboard_Open.png
d81b0cc3e1f6f8c7cc4bb9c58c63cd2bbcadb16aafd0f6aff565338b4b955f22  E4_Mobile_Research_Again_Confirmation.png
0db29ba712687d2821b01aac0524c646f006b367197ae028ebe5f7ac6eb2de8c  E5_Mobile_Conversation_Technical_Error.png
551d3a5fc49116e5835cbe0e2d940cbbec1544adf5ff2d57c1213fe75e6956bb  F1_Desktop_Research_Again_State.png
a2f3bc726d901e82f6d41f2b7918ad53a8c6f51b4b5f04d5ef6820eee5102066  F2_Mobile_Research_Again_State.png
efe759b09eeb529cf75bbb37d4482967defc107267e83aa0560b61672c4e0bfb  G1_Desktop_Updated_Results_Return_Exact_Shell.png
dc3f117ae4c14840bd6e0ecda653bd7a61b8040cf14213704956f985fea55137  G2_Mobile_Updated_Results_Return_Exact_Shell.png
dc3f117ae4c14840bd6e0ecda653bd7a61b8040cf14213704956f985fea55137  M_Results_Mobile_Exact_Master_Plus_Ask_PiqSavi.png
cceb8df4dc96fc3ee1405969c18a5b265b434895e3bb16cf8facc3447b898832  N_Compare_Mobile_Exact_Master_Plus_Ask_PiqSavi.png
e0babf29dc15e98a0faac7b398e4b6326aa131c96b68ce9ee79b0707b3422dcd  O_Why_Best_Piq_Mobile_Exact_Master_Plus_Ask_PiqSavi.png
16663233161f467a06b3e11981d0a6b8f3a04cca987519a9ec4eca34fd034e85  PIXEL_CONSISTENCY_QA.json
03177669a5919aa3bfaa2ee12a294e9a8d0bf1a064986f55140b9e36d255c458  QA_Compare_Master_vs_Insertion.png
fbaeb909234d75d9d2385c16fef2047d6f8f6c2ed9beab4d7cd5668e6c7d0f1e  QA_Results_Master_vs_Insertion.png
477e2ca85a902dbe61a2395676da65ca1c4be91ad92de9eb55e6e59d1e745f9d  QA_Why_Best_Piq_Master_vs_Insertion.png
```

## Legacy metadata provenance

`README_REVIEW_ONLY.txt` remains unchanged with SHA-256:

`d03fe81f74d45009d291d39d0d2e422ae26195af06b1bf2eeac2e17ed9e1f4de`

Its historical review-only status is superseded by this owner-approved
manifest. Its pixel-consistency and truthful-execution notes remain applicable.

## Verification requirement

Sprint 29 must verify every source checksum before implementation begins.
Sprint 44 must verify the implemented visual states against this manifest.
Sprint 45 must attach the successful manifest verification to CC-01 / EC-22.

A checksum mismatch is fail-closed and requires renewed owner approval.
