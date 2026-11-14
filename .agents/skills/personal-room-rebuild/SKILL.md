---
name: personal-room-rebuild
description: Rebuild a personal room or partial area from 3D Model Anything exports, using measured layout and img2threejs for individual photo-referenced objects. Use for fragmented room reconstructions or excessive capture effort; not for generic object-only modeling or automatic photogrammetry.
---

# Personal room rebuild

Use the sibling [scan-to-threejs skill](../scan-to-threejs/SKILL.md) for measurements,
coordinates and the viewer. Use the real installed **img2threejs** base skill for
individual objects. Read [integration.md](references/integration.md) when preparing
references or joining object factories to a room.

## Admit the capture before modeling

Ask for the extracted original room/session export if only JPEGs or a screenshot are
available. Photographs without camera metadata can guide appearance, but cannot
establish a measured room or matched-camera reconstruction. Do not ask for another
large photo batch before inspecting the existing evidence.

For one extracted `house-capture/5` session, inspect `manifest.json` and explicitly
select its original room index. A shared single-room export may use any index.
Run from the project root, with an output outside the input bundle:

```sh
python3 .agents/skills/scan-to-threejs/scripts/assess_capture.py \
  data/captures-in/my-session --room 7 --max-photos 24 \
  --out data/captures/my-session/evidence.json
```

Read the report, selected photos, and available diagnostics. `ready-for-review` is
input admission, never proof of fidelity. Exit 2 means no admissible posed references;
exit 1 means an input/IO error. Partial reports can still support a clearly marked
unmeasured area or a subset of objects. Exclusions are reviewable, not deletions.

For `house.json`, inspect active scan identities and use scan-to-threejs's house
importer. Assess each selected session separately. Never combine session-local poses
because room names match. Keep originals and reports under Git-ignored capture paths.

## Build in two layers

1. Establish floor, walls, openings and verified dimensions with scan-to-threejs.
   Inspect untextured geometry before blaming texture noise on geometry. If the
   room has no valid walls, do not run a wall-dependent converter or invent a floor
   outline. Work in an explicitly provisional local frame until measured evidence
   or a known reference dimension is available.
2. Pick one major object to validate the integration. Visually inspect its reference
   crop; select supplementary views only if they resolve shape ambiguity. Locate
   the installed img2threejs `SKILL.md`, read it, and use its public `generic` profile.
   Each object owns its state, spec and render comparisons. Follow its actual
   quality gates and bounded corrections; do not manufacture visual scores or mark
   missing renders as passing. Retain the full source photo and crop provenance.
3. Adapt the resulting `THREE.Group` into the existing `RoomModule`, normalizing
   units, axes and anchor before applying measured placement. Keep inferred scale
   or hidden geometry labeled as inferred. Verify the structural blockout from
   multiple real views before spending effort on materials.

The public base skill reconstructs individual objects in code. It does not align
photos, repair ARKit tracking, or offer a complete automatic room reconstruction.
The upstream `environment` plugin requires private access; do not depend on it or
claim its functionality is installed. If the base skill is missing, use the Mac
setup in [the handoff guide](../../../docs/personal-capture-mac.zh-TW.md) and the
upstream install instructions, then verify the resolved checkout/version. Permission
to rebuild a room does not authorize unrelated plugins, APIs or publishing photos.

## Review and deliver

Use the companion viewer's matched-camera tooling with **original photo array
indices**, not selection ranks. Sensor pixels and intrinsics stay paired; EXIF
rotation for viewing must not silently change projection coordinates. For cropped
object references, keep a separate crop camera; a crop is not the full-room camera.

Inspect several supported viewpoints plus a top view; compare wall placement,
silhouettes, object size, floor contact, overlap and materials. Run the viewer build
and report which checks actually ran. A model that looks clean from one viewpoint
is not a verified room. Stop at missing evidence or an upstream correction limit
and identify the smallest useful additional input.

Deliver editable room/object code, input-assessment report, comparison images, and
an explicit measured-versus-inferred list. Do not present a raw broken mesh as a
finished rebuild or claim real-device capture fixes from a simulator test.
