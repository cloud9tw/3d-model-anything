# Execution ledger — plan: docs/superpowers/plans/2026-11-14-personal-capture.md

- Design approved by user. Execute inline on `codex/personal-capture-img2threejs` in the existing dedicated checkout; no additional worktree needed.
- Baseline: seven importer tests pass. No Swift toolchain exists on this Windows host; run Swift policies and iOS compilation on GitHub macOS runners.
- Baseline public audit: default Windows cp950 decoding fails; UTF-8 mode then exposes CRLF checkout hash differences in seven unchanged text assets. Validate canonical LF export rather than modifying asset hashes.
- Pre-flight: Task 3 consumes the report schema in Task 2; original photo row indices and per-room/session scope must survive filtering. Capture metadata additions in Task 1 remain optional for old exports.
- User failure ZIP is absent. End-to-end reconstruction and physical capture validation remain pending, regardless of synthetic or CI results.
- Task 1 RED: macOS run 43575896854 failed on the original partial-area behavior (runtime assertion, not compilation). GREEN: policy job in run 43576133889 passes, including quota reservations/failure/reset/boundary checks. Full iOS build exposed a compiler error; resolving before delivery.
- Task 2 RED: 11 new assessment tests failed with the missing implementation. GREEN: 18 combined Python tests pass under PYTHONUTF8=1 (propagated to child processes on Windows).
- Task 3: bridge and upstream-routing metadata validate; viewer TypeScript/production build passes, with the existing large-bundle size warning. No user-room visual reconstruction has been attempted without inputs.
- Compile fix: simulator build failed in the existing CoverageEngine object-face tuple inference, outside the new policy. Added explicit SIMD tuple types and scalar half-dimensions, preserving the same five faces; the next full build is the regression check.
