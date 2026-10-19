# README review fixes

## Why

A structured README review (readme-atlas) found two reader-blocking gaps in the quickstart
(no way to obtain the script; the local-endpoint example exits before doing anything for a
user without an `.env`), plus missing success evidence and three smaller gaps. The file was
built incrementally during several sessions, so the seams show.

## What Changes

- Add the `git clone` step so the quickstart is completable from a cold start (fix 1)
- Give the local-endpoint example an explicit `--api-key dummy` and explain that local
  servers ignore the key (fix 2)
- Show a real command transcript so a successful run is recognizable (fix 3)
- Center the README header block (title, banner, opening sentence) per the house layout
  convention; body stays left-aligned (fix 4)
- Document the >10 MiB payload behavior (downscale for the API call only, original file
  untouched) and the TIFF-payload nuance (fix 5)
- Complete the exit-code map with the empty-selection case (fix 6)
- Optionally add a MIT badge whose target (`LICENSE`) exists

Doc-only change: no code, script flag, or metadata-tag behavior changes.

## Capabilities

- New Capabilities: none
- Modified Capabilities: none (documentation-only change; `skip_specs: true` declared in
  `.openspec.yaml` because the change modifies no system requirements)

## Impact

- `README.md` only (~10 lines added/moved, 0 lines of behavior)
- Facts added must match `exifcalibur.py` evidence already verified in the review
  (exit-code paths, API-key gate, `image_payload` downscale at lines 268–284,
  `Path | None` type annotations requiring Python 3.10+)
- Out of scope (candidates for later changes): execution-warning edge when the
  JPEG converter fails on a >10 MiB file (`exifcalibur.py:281`); version badge
  (blocked until the first SemVer tag)
