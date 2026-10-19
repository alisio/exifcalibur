# Spec Delta

## ADDED Requirements

### Requirement: Per-image vision analysis

The system SHALL, for every selected image file, request an enrichment
proposal from the configured OpenAI-compatible chat-completions endpoint,
sending the image as a base64 data-URI message alongside a prompt that
demands a single JSON object with exactly three fields: `description`
(one to two sentences), `keywords` (5 to 15 lowercase keywords) and
`people` (zero or more generic person descriptors). The prompt SHALL
instruct the model to write `description` and `keywords` in the configured
metadata language and to never invent people names.

#### Scenario: image sent to vision endpoint

- **WHEN** the processing of a supported image file starts
- **THEN** a chat-completions request is made to `<base-url>/chat/completions`
  with the file content encoded inline (base64 data URI) and the language-aware
  analysis prompt

#### Scenario: people described generically only

- **WHEN** the prompt is constructed
- **THEN** it forbids invented names and allows only generic descriptors for
  visible people (for example "woman", "child")

### Requirement: Enriched metadata written to the file

The system SHALL persist the normalized analysis into the image file via
exiftool as follows: description into both XMP-dc:Description and
IPTC:Caption-Abstract; keywords into both XMP-dc:Subject and
IPTC:Keywords; people into XMP-iptcExt:PersonInImage. The original file
SHALL be edited in place, preserving its other existing metadata.

#### Scenario: successful overwrite write

- **WHEN** analysis succeeds and no write-mode flags are set
- **THEN** the description, keywords and people values are stored in the
  mapped XMP and IPTC tags of the same file that was analyzed

#### Scenario: exiftool write failure

- **WHEN** the exiftool write command returns an error
- **THEN** the file is reported as `failed` with the exiftool error detail

### Requirement: Analysis normalization

The system SHALL normalize the model output before writing: description
trimmed as a string; keywords lowercased, stripped, deduplicated
(keeping first occurrences) and capped at 15 entries; people deduplicated
and capped at 10 entries.

#### Scenario: duplicate and overflowing keywords

- **WHEN** the model response contains duplicated keywords or more than 15
  entries
- **THEN** the written keyword list is deduplicated and contains at most 15
  items

### Requirement: Tolerant model-response parsing

The system SHALL accept model responses whose content wraps the JSON object
in markdown code fences or surrounds it with stray text, by extracting the
first valid JSON object. When the response content is empty, the system
SHALL fail the file and, if the response carries a reasoning trace, hint
that a non-reasoning model should be used.

#### Scenario: JSON wrapped in code fences

- **WHEN** the model returns the JSON object inside a ```code fence``` or with
  surrounding prose
- **THEN** the enrichment proceeds normally with the extracted object

#### Scenario: empty model content

- **WHEN** the API response message has empty `content`
- **THEN** the file fails with an explanatory error, mentioning
  "reasoning-only response" when a reasoning trace is present

### Requirement: Overwrite mode is the default write policy

By default the system SHALL replace any existing values of the mapped
tags with the newly generated ones.

#### Scenario: existing description replaced

- **WHEN** a file already has stored metadata and is processed without
  `--merge`
- **THEN** the model-generated values replace the previously stored values

### Requirement: Merge mode fills only empty fields

With `--merge`, the system SHALL skip, without calling the API, any file
that already has a description; otherwise it SHALL write only the mapped
tags that have no current value, leaving all existing values untouched.

#### Scenario: merge skips already-described file

- **WHEN** a file with an existing description is processed with `--merge`
- **THEN** no API request is made and the file is reported as `skipped`

#### Scenario: merge fills missing fields only

- **WHEN** a file has keywords but no description and is processed with
  `--merge`
- **THEN** the description tags are written while the existing keywords are
  preserved unchanged

### Requirement: Dry run writes nothing

With `--dry-run`, the system SHALL report the result for each file without
modifying any file on disk.

#### Scenario: dry run leaves files untouched

- **WHEN** processing runs with `--dry-run`
- **THEN** files are reported with status `dry-run` and their metadata is not
  changed

### Requirement: Payload conversion for constrained endpoints

For API submission the system SHALL convert in memory only, never touching
the original file: a source file exceeding 10 MiB becomes a JPEG payload
with maximum dimension 2048 px; a HEIC/HEIF or TIFF source file is sent as
JPEG (format conversion, without the size-dimension cap). If no platform
converter (sips or ImageMagick) is available and the file exceeds the size
limit, the system SHALL warn and send the original bytes.

#### Scenario: oversized photo downscaled for API only

- **WHEN** a supported photo larger than 10 MiB is processed
- **THEN** the API receives a downscaled JPEG payload while the file on disk
  keeps its original bytes and metadata intact

#### Scenario: HEIC or TIFF converted to JPEG

- **WHEN** a HEIC/HEIF or TIFF file is analyzed
- **THEN** a converted JPEG payload is sent instead of the native format

#### Scenario: no converter available for oversized file

- **WHEN** the file exceeds 10 MiB and no converter tool is installed
- **THEN** a warning is emitted and the original bytes are sent unconverted

### Requirement: API errors fail the file, not the run

When the analysis request fails (non-2xx response, network error or
malformed response envelope), the system SHALL report the individual file
as `failed` with the error detail instead of aborting the whole run.

#### Scenario: HTTP error from endpoint

- **WHEN** the endpoint answers with a non-2xx status
- **THEN** the file is reported as `failed` including the status code and a
  response snippet, and the remaining files continue to be processed
