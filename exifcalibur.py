#!/usr/bin/env python3
"""exifcalibur - enrich image metadata with an OpenAI-compatible vision model.

Reads images (JPEG, PNG, WebP, TIFF, HEIC), asks an OpenAI-compatible vision
endpoint for a description, keywords and generic people descriptors, and writes
the results into the image files with exiftool:

- description  -> XMP-dc:Description  + IPTC:Caption-Abstract
- keywords     -> XMP-dc:Subject      + IPTC:Keywords
- people       -> XMP-iptcExt:PersonInImage (generic descriptors, never names)

Configuration (highest to lowest precedence): CLI flags, environment
variables, .env file in the working directory, built-in defaults.

Requires: exiftool (https://exiftool.org). No third-party Python packages.
Compatible with macOS, Linux and Windows WSL.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "qwen/qwen3-vl-235b-a22b-instruct"
DEFAULT_LANG = "en"

IMAGE_EXTENSIONS = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
    ".heic": "image/heic",  # experimental
    ".heif": "image/heic",  # experimental
}

LANGUAGE_NAMES = {
    "en": "English",
    "pt": "Portuguese (Brazil)",
    "pt-BR": "Portuguese (Brazil)",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "ja": "Japanese",
    "zh": "Chinese (Simplified)",
}

PROMPT_TEMPLATE = """Analyze this photo for image library enrichment purposes. Respond with ONLY a JSON object (no markdown, no code fences) with these fields:
{{
  "description": "<one to two sentence description of the photo>",
  "keywords": [<5 to 15 lowercase keywords covering objects, scene, concepts and any visible people>],
  "people": [<zero or more generic descriptors of visible people, e.g. "woman", "child"; NEVER invent names>]
}}
Rules:
- Write the "description" field in {language}.
- Write the "keywords" in {language}, lowercase, in singular where natural.
- Do not invent people names: describe visible people generically only.
- Do not include camera metadata, EXIF dates or file properties.
"""


@dataclass
class Config:
    api_key: str
    base_url: str
    model: str
    lang: str
    merge: bool = False
    dry_run: bool = False
    workers: int = 1
    report_path: Path | None = None


@dataclass
class Result:
    path: str
    status: str  # written | dry-run | skipped | failed
    detail: str = ""
    description: str | None = None
    keywords: list[str] = field(default_factory=list)


# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------

def load_dotenv(path: Path) -> dict[str, str]:
    """Minimal .env parser: KEY=VALUE lines, '#' comments, optional quotes."""
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"warning: cannot read .env ({exc})", file=sys.stderr)
        return values
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.lower().startswith("export "):
            line = line[7:]
        key, sep, value = line.partition("=")
        if not sep:
            continue
        value = value.strip().strip("'\"").strip()
        values[key.strip()] = value
    return values


def resolve_config(args: argparse.Namespace) -> Config:
    dotenv = load_dotenv(Path.cwd() / ".env")

    def pick(es: str, flag: Any, default: Any) -> Any:
        if flag is not None:
            return flag
        if es in os.environ and os.environ[es]:
            return os.environ[es]
        if es in dotenv and dotenv[es]:
            return dotenv[es]
        return default

    api_key = pick("API_KEY", args.api_key, "")
    workers = int(pick("WORKERS", args.workers, 1))
    return Config(
        api_key=str(api_key),
        base_url=str(pick("BASE_URL", args.base_url, DEFAULT_BASE_URL)).rstrip("/"),
        model=str(pick("MODEL", args.model, DEFAULT_MODEL)),
        lang=str(pick("LANG", args.lang, DEFAULT_LANG)),
        merge=args.merge,
        dry_run=args.dry_run,
        workers=max(1, workers),
        report_path=Path(args.report) if args.report else None,
    )


# --------------------------------------------------------------------------
# exiftool helpers
# --------------------------------------------------------------------------

def check_exiftool() -> None:
    if shutil.which("exiftool") is None:
        print(
            "error: exiftool is required but was not found in PATH.\n"
            "Install it from https://exiftool.org (e.g. 'brew install exiftool').",
            file=sys.stderr,
        )
        raise SystemExit(1)


def run_exiftool(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["exiftool", *args], capture_output=True, text=True, check=False
    )


def read_current_metadata(path: Path) -> dict[str, Any]:
    """Return the descritive metadata currently stored in the file."""
    proc = run_exiftool(
        [
            "-j",
            "-XMP-dc:Description",
            "-XMP-dc:Subject",
            "-XMP-iptcExt:PersonInImage",
            "-IPTC:Caption-Abstract",
            "-IPTC:Keywords",
            str(path),
        ]
    )
    if proc.returncode != 0:
        raise RuntimeError(f"exiftool read failed: {proc.stderr.strip()}")
    try:
        return json.loads(proc.stdout)[0]
    except (json.JSONDecodeError, IndexError) as exc:
        raise RuntimeError(f"unexpected exiftool output: {proc.stdout!r}") from exc


WRITE_TAGS = [
    "-XMP-dc:Description",
    "-XMP-dc:Subject",
    "-XMP-iptcExt:PersonInImage",
    "-IPTC:Caption-Abstract",
    "-IPTC:Keywords",
]


def write_metadata(
    path: Path,
    description: str,
    keywords: list[str],
    people: list[str],
    merge: bool,
    current: dict[str, Any],
) -> None:
    """Write enrichment into the file. With merge=True, existing values are
    kept untouched and only empty fields are filled."""
    args = ["-overwrite_original", "-q", "-q", "-sep", ", "]
    tags: list[str] = []
    if merge:
        existing_desc = str(current.get("Description") or current.get("Caption-Abstract") or "").strip()
        existing_keys = current.get("Subject") or current.get("Keywords") or []
        existing_people = current.get("PersonInImage") or []
        if not existing_desc and description:
            tags += [f"-XMP-dc:Description={description}", f"-IPTC:Caption-Abstract={description}"]
        if not existing_keys and keywords:
            tags += [f"-XMP-dc:Subject={', '.join(keywords)}", f"-IPTC:Keywords={', '.join(keywords)}"]
        if not existing_people and people:
            tags += [f"-XMP-iptcExt:PersonInImage={', '.join(people)}"]
        if not tags:
            return  # merge mode and everything is already filled
    else:
        if description:
            tags += [f"-XMP-dc:Description={description}", f"-IPTC:Caption-Abstract={description}"]
        if keywords:
            tags += [f"-XMP-dc:Subject={', '.join(keywords)}", f"-IPTC:Keywords={', '.join(keywords)}"]
        if people:
            tags += [f"-XMP-iptcExt:PersonInImage={', '.join(people)}"]
        if not tags:
            return
    proc = run_exiftool([*args, *tags, str(path)])
    if proc.returncode != 0:
        raise RuntimeError(f"exiftool write failed: {proc.stderr.strip()}")


# --------------------------------------------------------------------------
# Vision model
# --------------------------------------------------------------------------

def image_payload(path: Path) -> tuple[str, bytes]:
    """Return (mime, image bytes) suitable for sending to the vision API."""
    mime = IMAGE_EXTENSIONS.get(path.suffix.lower(), "application/octet-stream")
    data = path.read_bytes()
    if mime == "image/heic" and sys.platform == "darwin" and shutil.which("sips"):
        # Many OpenAI-compatible endpoints accept only common formats; HEIC
        # is converted to JPEG when the platform converter is available.
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "converted.jpg"
            proc = subprocess.run(
                ["sips", "-s", "format", "jpeg", str(path), "--out", str(out)],
                capture_output=True, text=True, check=False,
            )
            if proc.returncode == 0 and out.is_file():
                return "image/jpeg", out.read_bytes()
    if mime == "image/tiff" and sys.platform == "darwin" and shutil.which("sips"):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "converted.jpg"
            proc = subprocess.run(
                ["sips", "-s", "format", "jpeg", str(path), "--out", str(out)],
                capture_output=True, text=True, check=False,
            )
            if proc.returncode == 0 and out.is_file():
                return "image/jpeg", out.read_bytes()
    return mime, data


def build_prompt(lang: str) -> str:
    language = LANGUAGE_NAMES.get(lang, lang)
    return PROMPT_TEMPLATE.format(language=language)


def extract_json(text: str) -> dict[str, Any]:
    """Tolerant JSON extraction: handles code fences and stray text."""
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`\n").lstrip("json").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    if start >= 0:
        decoder = json.JSONDecoder()
        try:
            obj, _ = decoder.raw_decode(text[start:])
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            pass
    raise ValueError(f"model did not return valid JSON: {text[:200]!r}")


def analyze_image(path: Path, cfg: Config) -> dict[str, Any]:
    mime, data = image_payload(path)
    b64 = base64.b64encode(data).decode("ascii")
    body = {
        "model": cfg.model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": build_prompt(cfg.lang)},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime};base64,{b64}"},
                    },
                ],
            }
        ],
        "max_tokens": 500,
        "temperature": 0.2,
    }
    request = Request(
        f"{cfg.base_url}/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {cfg.api_key}",
            # Cloudflare-based endpoints (e.g. OpenCode Zen) block the default
            # Python-urllib User-Agent with HTTP 403 (error 1010).
            "User-Agent": "exifcalibur/1.0 (metadata enrichment script)",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=180) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        snippet = exc.read(300).decode("utf-8", errors="replace")
        raise RuntimeError(f"API returned HTTP {exc.code}: {snippet}") from exc
    except (URLError, TimeoutError) as exc:
        raise RuntimeError(f"API request failed: {exc}") from exc
    try:
        content = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"unexpected API response: {json.dumps(payload)[:300]}") from exc
    return extract_json(content)


def normalize_analysis(proposal: dict[str, Any], cfg: Config) -> tuple[str, list[str], list[str]]:
    description = str(proposal.get("description", "")).strip()
    raw_keywords = proposal.get("keywords", [])
    keywords = [str(k).strip().lower() for k in raw_keywords if str(k).strip()]
    seen: set[str] = set()
    keywords = [k for k in keywords if not (k in seen or seen.add(k))][:15]
    raw_people = proposal.get("people", [])
    people_values = [str(p).strip() for p in raw_people if str(p).strip()]
    seen_people: set[str] = set()
    people = [p for p in people_values if not (p in seen_people or seen_people.add(p))][:10]
    return description, keywords, people


# --------------------------------------------------------------------------
# File collection and processing
# --------------------------------------------------------------------------

def collect_files(paths: list[str]) -> list[Path]:
    files: set[Path] = set()
    for raw in paths:
        p = Path(raw).expanduser()
        if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS:
            files.add(p.resolve())
        elif p.is_dir():
            for ext in IMAGE_EXTENSIONS:
                for found in p.rglob(f"*{ext}"):
                    files.add(found.resolve())
        elif p.is_file():
            print(f"warning: unsupported file type, skipping {p}", file=sys.stderr)
        else:
            print(f"warning: path not found, skipping {raw}", file=sys.stderr)
    return sorted(files)


def process_file(path: Path, cfg: Config) -> Result:
    result = Result(path=str(path), status="failed")
    try:
        current = read_current_metadata(path)
        existing_desc = (
            str(current.get("Description") or current.get("Caption-Abstract") or "").strip()
        )
        if cfg.merge and existing_desc:
            result.status = "skipped"
            result.detail = "already has a description (use overwrite mode to replace)"
            return result

        proposal = analyze_image(path, cfg)
        description, keywords, people = normalize_analysis(proposal, cfg)
        result.description = description
        result.keywords = keywords

        if cfg.dry_run:
            result.status = "dry-run"
            result.detail = "would write (dry-run)"
            return result

        write_metadata(path, description, keywords, people, cfg.merge, current)
        result.status = "written"
        return result
    except Exception as exc:  # noqa: BLE001 - one bad file must not stop the batch
        result.status = "failed"
        result.detail = str(exc)
        return result


def print_summary(results: list[Result]) -> None:
    counts: dict[str, int] = {}
    for r in results:
        counts[r.status] = counts.get(r.status, 0) + 1
    parts = [f"{count} {status}" for status, count in sorted(counts.items())]
    print(f"\nSummary: {len(results)} file(s) - {', '.join(parts) or 'none'}")


def report_data(results: list[Result]) -> dict[str, Any]:
    return {
        "files": [
            {
                "path": r.path,
                "status": r.status,
                "detail": r.detail,
                "description": r.description,
                "keywords": r.keywords,
            }
            for r in results
        ]
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="exifcalibur",
        description="Enrich image metadata (description, keywords, people) with an OpenAI-compatible vision model.",
        epilog="Configuration precedence: CLI flags > environment variables (API_KEY, BASE_URL, MODEL, LANG) > .env file > defaults.",
    )
    parser.add_argument("paths", nargs="+", metavar="PATH", help="image files and/or folders (recursive)")
    parser.add_argument("--api-key", help="API key (otherwise API_KEY env or .env)")
    parser.add_argument("--base-url", help=f"OpenAI-compatible base URL (default: {DEFAULT_BASE_URL})")
    parser.add_argument("--model", help=f"vision model name (default: {DEFAULT_MODEL})")
    parser.add_argument("--lang", help='language for the written metadata (default: "%s")' % DEFAULT_LANG)
    parser.add_argument("--workers", type=int, help="parallel API calls (default: 1)")
    parser.add_argument("--merge", action="store_true", help="fill only empty fields instead of overwriting")
    parser.add_argument("--dry-run", action="store_true", help="show what would be written without saving")
    parser.add_argument("--report", metavar="FILE", help="write a JSON report with results for every file")
    args = parser.parse_args(argv)

    check_exiftool()
    cfg = resolve_config(args)
    if not cfg.api_key:
        print(
            "error: no API key. Provide --api-key, set API_KEY, or put it in a .env file.",
            file=sys.stderr,
        )
        return 1

    files = collect_files(args.paths)
    if not files:
        print("Nothing to do: no supported image files found.", file=sys.stderr)
        return 1

    results: list[Result] = []
    if cfg.workers == 1:
        for path in files:
            result = process_file(path, cfg)
            results.append(result)
            status_line = result.detail if result.detail else f"description={'yes' if result.description else '-'}"
            print(f"[{result.status}] {result.path} - {status_line}")
    else:
        with ThreadPoolExecutor(max_workers=cfg.workers) as pool:
            futures = {pool.submit(process_file, p, cfg): p for p in files}
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
                status_line = result.detail if result.detail else f"description={'yes' if result.description else '-'}"
                print(f"[{result.status}] {result.path} - {status_line}")
        results.sort(key=lambda r: r.path)

    print_summary(results)
    if cfg.report_path:
        try:
            cfg.report_path.write_text(
                json.dumps(report_data(results), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            print(f"Report saved to {cfg.report_path}")
        except OSError as exc:
            print(f"warning: could not save report ({exc})", file=sys.stderr)

    return 1 if any(r.status == "failed" for r in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
