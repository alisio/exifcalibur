<div align="center">

# exifcalibur

<p align="center">
  <img src="banner.png" alt="exifcalibur — a golden sword piercing a stack of photo frames, surrounded by camera, location, face and search tag icons" width="100%">
</p>

**Enrich image metadata (description, keywords, people) with any OpenAI-compatible vision model.**

</div>

exifcalibur sends your photos to a vision endpoint and writes the results straight into the image files using [exiftool](https://exiftool.org):

| What | Where it goes |
|------|---------------|
| description | `XMP-dc:Description` + `IPTC:Caption-Abstract` |
| keywords (objects, scene, concepts) | `XMP-dc:Subject` + `IPTC:Keywords` |
| people (generic descriptors, never invented names) | `XMP-iptcExt:PersonInImage` |

The written metadata is standard XMP/IPTC, so any library manager (digiKam, Lightroom, Bridge, exiftool itself) can read it. Nothing is stored in a private database.

## Supported formats

JPEG, PNG, WebP and TIFF. HEIC/HEIF is **experimental**: exiftool can write metadata into it, and on macOS the payload sent to the model is converted to JPEG automatically (on other platforms the raw HEIC is sent, if the endpoint accepts it).

Files larger than 10 MiB are downscaled to ≤2048 px JPEG for the API call only; HEIC and TIFF payloads are converted to JPEG when a converter (`sips` on macOS, ImageMagick elsewhere) is available. The original file is never modified.

## Requirements

- Python 3.10+ (macOS, Linux or Windows WSL)
- [exiftool](https://exiftool.org) in `PATH` (e.g. `brew install exiftool`)
- An API key for any OpenAI-compatible vision endpoint

## Usage

Get the script and run from the repository directory:

```bash
git clone https://github.com/alisio/exifcalibur
cd exifcalibur
```

```bash
# one file or many
python3 exifcalibur.py photo.jpg vacation/best.png

# a whole folder (recursive) or several
python3 exifcalibur.py ~/Pictures/2023 ~/Pictures/2024

# only ask the model again for images that already have a description,
# and do not touch existing keywords/people (fill empty fields only)
python3 exifcalibur.py --merge ~/Pictures/2023

# show what would be written without saving anything
python3 exifcalibur.py --dry-run --merge ~/Pictures/2023

# parallel API calls, JSON report
python3 exifcalibur.py --workers 4 --report report.json ~/Pictures/2023
```

A successful run prints one line per file plus a final summary:

```
[written] photo.jpg - description=yes
Summary: 1 file(s) - 1 written
Model: minimax/minimax-m3.1-flash:free (lang=en, endpoint=https://openrouter.ai/api/v1)
```

Exit code is `0` when nothing failed, `1` when at least one file failed — it is also `1` when the selection is empty ("Nothing to do"). Individual failures never stop the batch.

### Options

| Flag | Meaning |
|------|---------|
| `--api-key KEY` | API key |
| `--base-url URL` | OpenAI-compatible base URL (default: `https://openrouter.ai/api/v1`) |
| `--model NAME` | vision model (default: `minimax/minimax-m3.1-flash:free`) |
| `--lang CODE` | language of the written metadata (default: `en`; e.g. `pt-BR`, `es`) |
| `--workers N` | parallel API calls (default: 1) |
| `--merge` | fill only empty fields instead of overwriting |
| `--dry-run` | run everything except the final write |
| `--report FILE` | save a JSON report with per-file results |

## Configuration

Precedence, highest first: **CLI flags → environment variables → `.env` file → defaults**.

| Variable | Default |
|----------|---------|
| `API_KEY` | (none, required) |
| `BASE_URL` | `https://openrouter.ai/api/v1` |
| `MODEL` | `minimax/minimax-m3.1-flash:free` (free tier; rate-limited — retry later on 429) |
| `EXIFCALIBUR_LANG` | `en` |
| `WORKERS` | `1` |

The `.env` file is read from the working directory (plain `KEY=VALUE` lines); copy `.env.example` as a starting point:

```bash
cp .env.example .env   # then edit .env
```

Example pointing to a local server (Ollama, LM Studio…):

```bash
python3 exifcalibur.py --base-url http://localhost:11434/v1 --model qwen3-vl:32b --api-key dummy ~/Pictures
```

Local servers usually ignore the key — any non-empty value satisfies the check.

## Overwrite vs merge

By default (overwrite mode), the description and keyword lists **are replaced** by the model's answer. Use `--merge` when you already manage metadata in a library app (e.g. digiKam): images that already have a description are skipped entirely (no API call), and empty fields are filled. Person regions (face areas with names) are never modified by exifcalibur in either mode.

## License

[MIT](LICENSE)
