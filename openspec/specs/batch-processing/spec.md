# batch-processing Specification

## Purpose
TBD - created by archiving change baseline-specs-from-code. Update Purpose after archive.

## Requirements

### Requirement: Path selection rules

The system SHALL accept one or more path arguments. A path that is a file
with a supported extension (JPEG, PNG, WebP, TIFF, HEIC/HEIF) SHALL be
processed; a path that is a directory SHALL be scanned recursively for
files with supported extensions; a file with an unsupported extension
SHALL be warned about and skipped; a nonexistent path SHALL be warned
about and skipped. The resulting work set SHALL be deduplicated and, in
sequential mode, processed in sorted path order.

#### Scenario: folder scanned recursively

- **WHEN** a directory path is given as input
- **THEN** every file with a supported image extension inside the directory
  tree (any depth) is queued for processing exactly once

#### Scenario: unsupported file type warned and skipped

- **WHEN** a file argument has an extension outside the supported set
- **THEN** a warning is printed and the file is not processed

#### Scenario: nonexistent path warned and skipped

- **WHEN** a path argument points to nothing
- **THEN** a warning is printed naming the missing path and processing
  continues with the remaining inputs

### Requirement: Empty selection aborts with error

If no supported image files result from the selection, the system SHALL
print "Nothing to do: no supported image files found." and exit with
status 1.

#### Scenario: folder without supported images

- **WHEN** the input paths yield zero supported files
- **THEN** the process exits with code 1 and the "Nothing to do" message

### Requirement: Sequential and parallel execution

The system SHALL process files sequentially by default and, with
`--workers N` (N >= 1), with at most N parallel API workers. In parallel
mode results SHALL be ordered by path in the summary and report.

#### Scenario: workers flag increases parallelism

- **WHEN** `--workers 2` is given for a multi-file batch
- **THEN** up to two files are processed concurrently

#### Scenario: workers floored at one

- **WHEN** a workers value lower than 1 is configured
- **THEN** the effective worker count is 1

### Requirement: Per-file status line

For every processed file the system SHALL print one status line in the
form `[status] path - detail`, where status is `written`, `dry-run`,
`skipped` or `failed`, and detail carries the explanatory reason when
present.

#### Scenario: written file line

- **WHEN** a file is successfully enriched
- **THEN** a line `[written] <path> - description=yes` is printed

#### Scenario: skipped file line names the reason

- **WHEN** a file is skipped in merge mode
- **THEN** the line reports `skipped` and the reason (already has a
  description)

### Requirement: Failure isolation

An error in one file SHALL NOT abort the batch; every subsequent file
SHALL still be processed and each failure SHALL be recorded individually.

#### Scenario: one broken file does not stop the batch

- **WHEN** one file fails during analysis or write
- **THEN** the remaining files are still processed and each result keeps its
  own status

### Requirement: Final summary lines

At the end the system SHALL print a summary line with the total file count
and per-status counts, followed by a model line exposing the effective
model, metadata language and endpoint.

#### Scenario: summary with counts

- **WHEN** the batch finishes
- **THEN** lines like "Summary: N file(s) - X written, Y failed" and
  "Model: <model> (lang=<lang>, endpoint=<url>)" are printed

### Requirement: JSON report option

With `--report FILE`, the system SHALL write a JSON file containing, for
every processed file, its path, status, detail, description and keywords.
If the report cannot be written, the system SHALL warn and not fail the
run.

#### Scenario: report written on success

- **WHEN** `--report` points to a writable path
- **THEN** a JSON report with a `files` array covering every processed file
  is written and its path announced

#### Scenario: unwritable report path warns only

- **WHEN** the report file cannot be written
- **THEN** a warning is printed to stderr and the exit code still reflects
  only the processing results

### Requirement: Exit code semantics

The system SHALL exit 0 when at least one file was processed and none
failed, and 1 when the selection is empty or any file failed.

#### Scenario: partial failure exits nonzero

- **WHEN** some files are written and some fail
- **THEN** the process exits with code 1
