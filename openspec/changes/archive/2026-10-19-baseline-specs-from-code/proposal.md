# Proposal

## Why

The repository ships a working CLI (`exifcalibur.py`) with a full README, but no
OpenSpec capability specs. Without a requirements baseline, future changes
(default model swap, new tags, HEIC graduation from experimental, merge-rule
tweaks) risk silently breaking behavior that today is only encoded in the code
and in the session history. Extracting the observed behavior from the
implementation establishes a verifiable ground truth before any new change.

## What Changes

- Add three new capability specs derived from (and only from) the current
  implementation — no code is modified:
  - Per-image enrichment pipeline: metadata read, vision-model analysis
    (OpenAI-compatible endpoint), response normalization, and exiftool write of
    description, keywords and generic people descriptors.
  - Batch processing: file/folder discovery (recursive, extension-filtered),
    per-file result lines, worker concurrency, failure isolation, summary
    line, JSON report option, and exit codes.
  - Configuration: precedence chain (CLI flag > environment variable > `.env`
    file > built-in default), minimal `.env` parsing, required API key check,
    and the exiftool dependency check.
- Document the currently fixed decisions as requirements: overwrite-by-default
  vs `--merge` fill-empty-fields, `--dry-run` no-write guarantee, payload
  downscale above 10 MiB for the API only (original file untouched), max 15
  keywords / 10 people deduplicated, and people described generically (never
  invented names).

## Capabilities

### New Capabilities

- `image-enrichment`: transforming a single image file into enriched metadata
  — vision API analysis contract, response normalization limits, metadata
  tags written (XMP + IPTC), overwrite/merge/dry-run write behavior, and the
  oversized/heic payload conversion rule.
- `batch-processing`: selecting which files get processed (paths, folders,
  recursion, extension filter, unsupported warnings), sequential vs parallel
  execution, per-file status output, summary line, JSON report file, and exit
  code semantics.
- `configuration`: how runtime settings resolve (flags, env vars, `.env`,
  defaults), what is mandatory (API key, exiftool binary), and the fixed
  built-in defaults (base URL, model, language).

### Modified Capabilities

(none — first specs for this project; no existing requirements change)

## Impact

- `/Users/alisio/dev/exifcalibur/openspec/` — three new spec directories
  (`image-enrichment`, `batch-processing`, `configuration`).
- No runtime code, tests, README or dependencies change in this workflow.
- After archival, future changes will propose deltas against these baseline
  specs.
