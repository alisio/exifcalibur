# configuration Specification

## Purpose
TBD - created by archiving change baseline-specs-from-code. Update Purpose after archive.

## Requirements

### Requirement: Configuration precedence chain

Runtime settings SHALL resolve per key in the strict order: CLI flag
(highest), then the matching environment variable, then a matching `KEY` in
a `.env` file in the current working directory, then the built-in default.
An empty-string value SHALL NOT count as set at any layer.

#### Scenario: environment variable overrides dot-env

- **WHEN** the same key (for example `BASE_URL`) is present both in the
  environment and in `.env` with different values
- **THEN** the environment value is used

#### Scenario: CLI flag overrides everything

- **WHEN** a CLI flag for a key is provided together with lower-precedence
  sources for the same key
- **THEN** the flag value wins

### Requirement: Language variable is EXIFCALIBUR_LANG

The metadata language SHALL be read only from the `EXIFCALIBUR_LANG`
environment variable (or `--lang`); the generic Unix `LANG` locale variable
SHALL NOT influence the metadata language.

#### Scenario: locale LANG is ignored

- **WHEN** the shell environment sets `LANG=en_GB.UTF-8` but no
  `EXIFCALIBUR_LANG` (nor `--lang`)
- **THEN** the written metadata uses the default language, not the locale
  value

### Requirement: Built-in defaults

The system SHALL default to `https://openrouter.ai/api/v1` as base URL,
`minimax/minimax-m3.1-flash:free` as model, EN English (`en`) as metadata
language and 1 as worker count.

#### Scenario: no configuration present

- **WHEN** no flags, environment variables or `.env` file provide any value
- **THEN** the OpenRouter default endpoint, the MiniMax free vision model,
  English metadata and sequential processing are used

### Requirement: Minimal dot-env file parsing

The system SHALL read a plain `.env` file in the current working directory
supporting `KEY=VALUE` lines, `#` comments, optional `export ` prefix and
optional single/double quotes around values. An unreadable `.env` SHALL
produce a warning and be ignored, not an error.

#### Scenario: quoted values with comments parsed

- **WHEN** `.env` contains commented lines and `MODEL="some/model"`
- **THEN** the value is read unquoted and `MODEL` precedes the built-in
  default

### Requirement: API key mandatory

The system SHALL refuse to run when no API key resolves from any source
(CLI flag, `API_KEY` env, `.env`), printing an error that names all three
sources and exiting 1 before any file processing.

#### Scenario: missing key aborts early

- **WHEN** the program is invoked without any API key source
- **THEN** it exits 1 with the usage error and no file is touched

### Requirement: exiftool dependency mandatory

The system SHALL require the `exiftool` binary on PATH before processing;
if absent it SHALL print an installation-pointer error and exit 1.

#### Scenario: exiftool not installed

- **WHEN** `exiftool` is not found in PATH
- **THEN** the program exits 1 pointing to https://exiftool.org
