# Tasks

## 1. Validation of the baseline extraction

- [x] 1.1 Run `openspec validate "baseline-specs-from-code" --type change --strict` and fix all reported delta-format errors (verify: the command exits 0) — valid: True, issues: []
- [x] 1.2 Cross-check every requirement and scenario of the three specs against `exifcalibur.py`/README behavior, correcting discrepancies in the spec files only (verify: each scenario has a matching observable behavior in the code) — 1 discrepância corrigida (cap de 2048 px aplica-se só a arquivos >10 MiB; conversão por formato HEIC/TIFF não tem o cap); demais 22 requirements conferidos, edits só sob `openspec/`
- [x] 1.3 Confirm no runtime file was touched by this change (verify: no tracked file modified; untracked limited to `openspec/`, `.opencode/`, `exifcalibur-finder.shortcut` — git-ignored `.env` incluído)

## 2. Review and archive

- [x] 2.1 Present the spec-delta overview (3 capabilities, requirement counts) for user review and record any requested wording adjustment (verify: explicit user approval) — aprovado sem ajustes (opção 1, nesta sessão)
- [x] 2.2 Archive the change via the archive workflow and confirm the three main specs were created (verify: `openspec list --specs` shows `image-enrichment`, `batch-processing`, `configuration`) — arquivado como `2026-10-19-baseline-specs-from-code`; 23 requirements aplicados; as 3 capacidades existem em `openspec/specs/` (8/6/9 requirements)
