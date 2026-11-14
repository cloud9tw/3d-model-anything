# Personal Capture Implementation Plan

> **For agentic workers:** Use executing-plans to implement task-by-task. Steps use checkboxes for tracking.

**Goal:** Bound capture effort, save partial areas clearly, and route measured rooms plus selected object references into the public img2threejs workflow.

**Architecture:** Pure Swift capture policies drive the existing controller and SwiftUI. A read-only Python bundle assessor validates evidence and selects diverse references without altering capture files. A project skill bridges scan-to-threejs and an independently installed img2threejs base skill.

**Tech Stack:** Swift/SwiftUI/ARKit/RoomPlan; Python 3.10+ and Pillow; existing Three.js viewer.

**Spec:** `docs/personal-capture-img2threejs-design.zh-TW.md`

## Global Constraints

- Default automatic-photo budget: 60 per room; configurable before capture; manual photos remain available under existing tracking/write checks.
- Keep house-capture/5 compatibility; new metadata optional; old exports readable.
- Never equate photo coverage with room completion or infer alignment from names.
- Keep photos, metadata and reports private in ignored capture folders.
- Public img2threejs generic object workflow only; no private environment dependency or external AI API setup.
- macOS builds and actual iPhone testing are distinct evidence; no real-device success claims from CI.

## Review Focus

- A high-resolution callback or final held frame at the quota boundary must not add an extra automatic photo.
- Failed JPEG writes must release quota reservations; starting a new room must reset the budget.
- A partial area with no RoomPlan layout must remain exportable and be flagged as unmeasured.
- Untrusted paths, non-finite matrices, missing metadata and duplicate frames must not be admitted as valid posed evidence.
- Multiple sessions and repeated room indices must not be silently combined; a first-in-zone session does not establish house alignment.

### Task 1: Bounded capture and truthful save progress

**Files:** CaptureQuality.swift, CaptureController.swift, CaptureScreen.swift, ScanBundle.swift, SelfTest.swift; `apps/house-capture/tests/CapturePolicyTests.swift`; `.github/workflows/capture-check.yml`.

**Interfaces:** `CaptureScope` (`area`, `room`); `CaptureQuality(..., scope:)`; `AutomaticPhotoBudget` with `reserve()`, `complete(saved:)`, `canReserve`, `saved`, `pending`. The controller owns one budget per room; reserve at final save admission and release after JPEG completion.

- [x] Write a failing Swift partial-area quality regression against current code; run on a macOS Actions runner.
- [x] Add quota tests (60 accepted, 61st rejected; pending reservation; failed write retry; reset; zero/negative limits).
- [x] Implement policies and wire capture gating at candidate collection, commit and save, leaving manual admission independent.
- [x] Add pre-scan scope/limit controls, fixed save action, separate photo coverage and quota labels, and actual save-stage status.
- [x] Store optional capture scope and photo limit in room metadata; preserve legacy decoding.
- [x] Run policy tests, unsigned simulator build, and existing simulator self-tests where supported.
- [x] Commit the capture change.

### Task 2: Read-only reconstruction evidence assessment

**Files:** `.agents/skills/scan-to-threejs/scripts/assess_capture.py` and `test_assess_capture.py`.

**Interfaces:** `assess_bundle(bundle: Path, room: int, max_photos: int = 24) -> dict`; CLI `assess_capture.py BUNDLE --room N --max-photos N --out REPORT`. Explicit room/session selection, no ZIP extraction or multi-session merging. Report includes source hashes, layout status, alignment scope, selected references, exclusions with reasons, and diagnostics.

- [x] Write tests for invalid/missing poses, unsafe paths, duplicate/blurred photos, diverse selection, nonzero room indices, no-layout partials, and unchanged inputs.
- [x] Observe failing tests, then implement image/metadata validation and deterministic spatial/view selection with Pillow.
- [x] Report missing quality signals as unknown; retain original row indices for provenance and map them to converted viewer indices; write no images or modified metadata.
- [x] Run all importer tests; commit.

### Task 3: Usable skill bridge and Mac handoff

**Files:** `.agents/skills/personal-room-rebuild/SKILL.md`, supporting reference document, existing scan-to-threejs/SKILL.md, `docs/personal-capture-mac.zh-TW.md`, README.md.

**Interfaces:** Bridge consumes Task 2 report and the real installed img2threejs skill. Each admitted object gets its own state/spec; no fabricated success or visual scores. Output remains an existing viewer RoomModule.

- [x] Read skill-creator and img2threejs public contracts before writing bridge instructions.
- [x] Connect assessment → structural baseline → selected object references → img2threejs gates → coordinate adaptation → matched-camera comparison.
- [x] Document installation on Mac for Codex, branch checkout, Xcode signing, partial export recovery, and evidence requirements.
- [x] Validate skill metadata and exercise the assessor against synthetic fixtures; do not claim a reconstructed room without user inputs.
- [x] Commit.

### Task 4: Review and publish a reviewable branch

- [x] Run complete Python suite, viewer build, public-boundary check on canonical LF files, macOS Swift policies and simulator build.
- [x] Request one fresh whole-branch review; fix actionable issues with regression coverage.
- [ ] Push branch to user's fork, create/attach a draft PR, verify remote head and CI outcomes.
- [ ] Report concrete changes, checks, Mac checkout instructions, and missing physical-device evidence.
