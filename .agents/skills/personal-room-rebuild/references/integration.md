# Evidence and object integration contract

## Capture assessment

`assess_capture.py` reads one already-extracted session. It does not extract ZIPs,
merge sessions, modify images or change camera poses. Pillow is required.

`personal-room-evidence/1` fields:

- `source`, `manifestSha256`, `photoIndexFile`, `photoIndexSha256`: input identity.
- `room`, `session`, `alignment`: original identities; `scope` stays `session-only`
  and `housePlacementVerified` stays false even when the session says `first`.
- `layout.status`: `measured` means syntactically valid reported wall measurements;
  it does not prove their real-world accuracy. `unmeasured` or `invalid` must not
  become a fabricated room outline.
- `selected[].photoIndex`: original index in `photos/photos.json`. Keep this for
  matched-camera comparisons. `selectionRank` is only selection order.
- Selected references retain raw sensor dimensions, intrinsics, camera-to-session
  transform, EXIF orientation, hashes and missing quality signals.
- `excluded`: invalid metadata/files, duplicates, redundant viewpoints or the
  reference budget. An exclusion is never permission to delete the original.
- `diagnostics`: location/hash of diagnostics when available, not a root-cause
  conclusion. Inspect original records before attributing fragmentation to tracking.

Selection uses image contrast/exposure, motion-blur metadata, position and viewing
direction. It cannot know which furniture matters or whether all room surfaces were
seen. Visually inspect chosen references and deliberately supplement weakly covered
objects. Twenty-four is a starting reference budget, not a fidelity requirement.

## Running img2threejs

The upstream base skill is independently installed on Mac:
https://github.com/img2threejs/img2threejs/blob/main/docs/INSTALL.md

Read the resolved `SKILL.md`, record its version and commit, and follow its current
commands. The integration was inspected against v2.0.1 source commit
`0c0c49bc168e648dbaf9c8c080474de0b3a941b6`; newer versions require checking their
contracts, not silently claiming the pinned version is installed.

Use a separate ignored object workspace such as
`data/captures/my-room/objects/desk/`. Run upstream scripts from that skill's root
with absolute state, reference, spec and output paths so objects cannot share or
overwrite each other's `.img2threejs/state.json`. Initialize the public `generic`
profile, then use `forge/next.py` at start/resume and respect the returned gates.
Do not invoke a private environment profile for a whole room.

If cropping a photo, retain its original hash, pixel-space crop rectangle and
orientation. Match the object camera using the crop's own frame. Never replace the
uncropped photo referenced by the room's camera metadata. Reference-derived material
assets remain private unless publishing is separately authorized.

## Placing object factories

`createObjectModel(...)` returns a `THREE.Group`. Its own geometry, pivots and local
origin are not assumed to match RoomPlan. Read its spec before placement.

Use a wrapper group to adapt the object coordinate convention, physical size and
floor/center anchor. Apply measured room position and orientation outside that
wrapper. The conceptual order is:

`roomPlacement × axisConversion × physicalScale × originCorrection × objectLocal`

Three.js multiplication applies the rightmost transform first. Avoid baking room
translation into procedural vertex data; keep the object editable. Do not apply
`worldToRoom` a second time to positions already converted by the room importer.

RoomPlan object boxes are bounds, not final surfaces. Use verified dimensions where
available; don't nonuniformly stretch recognizable geometry merely to match a noisy
box. Check floor contact and multiple views. If only an image exists, report scale
as inferred and ask for one useful dimension when physical scale matters.

Keep house placement separate from room coordinates. A valid camera-to-session
matrix and a matching name are not house alignment. Use the original
scan-to-threejs transform contract and verified session/zone placement.

## Stop conditions

- No readable image: request the original reference.
- No trustworthy layout: offer an explicitly unmeasured partial reconstruction.
- No installed base skill: complete supported setup or report the setup gap.
- Conflicting frames, missing views, a failed visual gate or exhausted correction
  allowance: report that specific gap; don't bypass a gate or replace it with a
  plausible-looking result.
