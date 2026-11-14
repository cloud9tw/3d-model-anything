# Execution ledger — plan: docs/superpowers/plans/2026-11-14-personal-capture.md

- Design approved by user. Execute inline on `codex/personal-capture-img2threejs` in the existing dedicated checkout; no additional worktree needed.
- Baseline: seven importer tests pass. No Swift toolchain exists on this Windows host; run Swift policies and iOS compilation on GitHub macOS runners.
- Baseline public audit: default Windows cp950 decoding fails; UTF-8 mode then exposes CRLF checkout hash differences in seven unchanged text assets. Validate canonical LF export rather than modifying asset hashes.
- Pre-flight: Task 3 consumes the report schema in Task 2; original photo row indices and per-room/session scope must survive filtering. Capture metadata additions in Task 1 remain optional for old exports.
- User failure ZIP is absent. End-to-end reconstruction and physical capture validation remain pending, regardless of synthetic or CI results.
