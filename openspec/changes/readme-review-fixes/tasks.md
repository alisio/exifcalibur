# Tasks: README review fixes

All edits target `README.md` at the repository root. Every fix carries its own
verification inline; the review evidence (commit-reviewed `exifcalibur.py`) is the
single factual source.

## 1. Reader-path fixes (significant)

- [x] 1.1 Fix 1 — add the obtain-the-script step before the first command block: `git clone https://github.com/alisio/exifcalibur && cd exifcalibur` (right after `## Usage` heading or a new `## Getting the script` intro line). Verify: a reader following the README top-to-bottom has the script in place before the first `python3 exifcalibur.py` call.
- [x] 1.2 Fix 2 — local-endpoint example (currently `--base-url … ~/Pictures` at the bottom of Configuration): add `--api-key dummy` and one sentence: local servers (Ollama/LM Studio) ignore the key; any non-empty value satisfies the gate. Verify: copying the example verbatim no longer exits with the missing-key error (matches the Observed behavior of the Ollama session test).
- [x] 1.3 Fix 3 — paste a real transcript (3–4 lines: `[written] …`, `Summary: …`, `Model: …`) after the first usage block so success is recognizable. Verify: transcript matches actual output shape produced by the script (per-file `[written]`/`[skipped]` lines, Summary, Model line).

## 2. Fact-completeness fixes (editorial)

- [x] 2.1 Fix 5 — in `## Supported formats`, add one sentence: files larger than 10 MiB are downscaled to ≤2048 px JPEG for the API call only; HEIC/TIFF payloads are converted to JPEG when a converter (sips/ImageMagick) is available; the original file is never modified. Verify: wording matches `image_payload` behavior (`exifcalibur.py:268-284`).
- [x] 2.2 Fix 6 — extend the exit-code paragraph: the run also exits `1` when the selection is empty ("Nothing to do"). Verify: consistent with the noticed behavior of `main()` return codes.
- [x] 2.3 Fix 4 — wrap the header block (H1 title, banner, opening sentence) in a centered `<div align="center">` container with blank lines around the Markdown; keep all body sections left-aligned. Verify: no other centering introduced; banner `<img>` stays inside the container.

## 3. Final check

- [x] 3.1 Re-read the full README as a cold-start reader and diff each fix against the review findings list (fixes 1–6 all addressed, no publicized machine-specific paths, no secret material). Note validation limits in the apply report: rendering inspected from source only; commands traced by inspection plus the session's earlier executed tests (OpenRouter real runs, Ollama local run with dummy key).
