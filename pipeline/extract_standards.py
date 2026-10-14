"""Extract USA Swimming 2024-2028 Age Group Motivational Standards from the
official PDF into a normalized JSON dataset.

Usage:
    .venv\\Scripts\\python pipeline\\extract_standards.py

Reads:  data/standards/usa_swimming_2024_2028_motivational_standards.pdf
Writes: data/standards/motivational_standards.json

The PDF pages contain one or two sections. Each section starts with a header
line like "10 & under Girls Event 10 & under Boys". Rows look like:

    39.79 * 35.99 * 32.09 * 30.89 * 29.59 * 28.29 * 50 FR SCY 27.49 * ... 38.19 *

Girls times come first, in order B, BB, A, AA, AAA, AAAA (slowest -> fastest).
Relay rows (FR-R, MED-R) are skipped. Occasionally the course token ("SCY")
wraps onto the following line; the parser handles that.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path

import pdfplumber

ROOT = Path(__file__).resolve().parent.parent
PDF_PATH = ROOT / "data" / "standards" / "usa_swimming_2024_2028_motivational_standards.pdf"
OUT_PATH = ROOT / "data" / "standards" / "motivational_standards.json"

SOURCE_URL = (
    "https://websitedevsa.blob.core.windows.net/sitefinity/docs/default-source/"
    "timesdocuments/time-standards/2025/2028-motivational-standards-age-group.pdf"
)
DOCUMENT_TITLE = "USA Swimming 2024-2028 Motivational Standards"

LEVELS = ["B", "BB", "A", "AA", "AAA", "AAAA"]

AGE_GROUPS = ["10 & under", "11-12", "13-14", "15-16", "17-18"]

_TIME = re.compile(r"^\d{1,4}(?::[0-5]\d)?\.\d{2}$")
_SECTION_HEADER = re.compile(r"^(.+?)\s*Girls\s+Event\s+(.+?)\s+Boys\s*$")
# event cell: e.g. "50 FR SCY", "1650 FR SCY", "200 MED-R SCY", or "200 MED-R"
_EVENT = re.compile(
    r"^(\d{2,4})\s+(FR|BK|BR|FL|IM|FR-R|MED-R)(?:\s+(SCY|SCM|LCM))?$"
)


def _is_time(token: str) -> bool:
    return bool(_TIME.match(token))


def _time_to_seconds(text: str) -> float:
    if ":" in text:
        mins, sec = text.split(":")
        return round(int(mins) * 60 + float(sec), 2)
    return round(float(text), 2)


def parse_pdf(pdf_path: Path) -> tuple[list[dict], list[str]]:
    """Parse the PDF and return (records, errors)."""
    records: list[dict] = []
    errors: list[str] = []

    with pdfplumber.open(str(pdf_path)) as pdf:
        for page_no, page in enumerate(pdf.pages, start=1):
            lines = (page.extract_text() or "").splitlines()
            current_age_group: str | None = None
            pending_line: str | None = None  # row whose course wrapped, if any

            for line in lines:
                header = _SECTION_HEADER.match(line.strip())
                if header:
                    age = header.group(1).strip()
                    if age not in AGE_GROUPS:
                        errors.append(
                            f"page {page_no}: unrecognized age group {age!r}"
                        )
                        continue
                    current_age_group = age
                    continue

                if current_age_group is None:
                    continue

                if pending_line is not None:
                    # Previous row ended without a course token; expect the
                    # course alone on this line or appended.
                    pending_line = f"{pending_line} {line.strip()}"
                    line = pending_line
                    pending_line = None

                tokens = [t for t in line.split() if t != "*"]
                # Find the event cell: locate the distance+stroke pair.
                ev_idx = None
                for i in range(len(tokens) - 1):
                    m = _EVENT.match(" ".join(tokens[i:i + 3]))
                    m2 = _EVENT.match(" ".join(tokens[i:i + 2]))
                    if m:
                        ev_idx = i
                        ev_match = m
                        break
                    if m2:
                        ev_idx = i
                        ev_match = m2
                        break
                if ev_idx is None:
                    continue

                distance = int(ev_match.group(1))
                stroke = ev_match.group(2)
                course = ev_match.group(3)
                if course is None:
                    # The course token wrapped onto the next line; in the
                    # captured combined line it follows the stroke token.
                    # Search remaining tokens after the stroke for a course.
                    rest_start = ev_idx + 3 if _EVENT.match(
                        " ".join(tokens[ev_idx:ev_idx + 3])
                    ) else ev_idx + 2
                    found = None
                    for j in range(rest_start, len(tokens)):
                        if tokens[j] in ("SCY", "SCM", "LCM"):
                            found = tokens[j]
                            break
                    if found is None:
                        # truly wrapped: defer
                        pending_line = line
                        continue
                    course = found

                girls_tokens = [t for t in tokens[:ev_idx] if _is_time(t)]
                boys_tokens = [
                    t for t in tokens[ev_idx + 2:]
                    if _is_time(t)
                ]
                if len(girls_tokens) != 6 or len(boys_tokens) != 6:
                    errors.append(
                        f"page {page_no}: {distance} {stroke} {course} "
                        f"({current_age_group}): expected 6+6 times, got "
                        f"{len(girls_tokens)}+{len(boys_tokens)} — line skipped"
                    )
                    continue

                # Relays are standards for relay events, not individual swims.
                is_relay = stroke in ("FR-R", "MED-R")

                # Girls columns run B->AAAA (left to right); Boys columns are
                # mirrored on the right side, running AAAA->B. Normalize both
                # to B, BB, A, AA, AAA, AAAA order.
                boys_tokens = list(reversed(boys_tokens))

                for gender, tset in (("Girls", girls_tokens), ("Boys", boys_tokens)):
                    if is_relay:
                        continue
                    levels = {lv: _time_to_seconds(t) for lv, t in zip(LEVELS, tset)}
                    records.append(
                        {
                            "age_group": current_age_group,
                            "gender": gender,
                            "distance": distance,
                            "stroke": stroke,
                            "course": course,
                            "standards": levels,
                            "page": page_no,
                        }
                    )

    return records, errors


def validate(records: list[dict]) -> list[str]:
    """Structural validation; returns a list of problems (empty = OK)."""
    problems: list[str] = []
    seen: set[tuple] = set()
    for r in records:
        key = (r["age_group"], r["gender"], r["distance"], r["stroke"], r["course"])
        if key in seen:
            problems.append(f"duplicate record: {key}")
        seen.add(key)
        vals = [r["standards"][lv] for lv in LEVELS]
        # Standards must get strictly faster B -> AAAA
        if not all(vals[i] > vals[i + 1] for i in range(len(vals) - 1)):
            problems.append(
                f"non-monotonic standards for {key}: "
                f"{[f'{lv}={v}' for lv, v in zip(LEVELS, vals)]}"
            )
    return problems


def main() -> int:
    if not PDF_PATH.exists():
        print(f"PDF not found: {PDF_PATH}", file=sys.stderr)
        return 1

    records, errors = parse_pdf(PDF_PATH)
    problems = validate(records)
    errors.extend(problems)

    if errors:
        print(f"{len(errors)} extraction problem(s):", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 2

    dataset = {
        "metadata": {
            "title": DOCUMENT_TITLE,
            "source_url": SOURCE_URL,
            "source_pdf": PDF_PATH.name,
            "levels": LEVELS,
            "age_groups": AGE_GROUPS,
            "extraction_date": date.today().isoformat(),
            "document_printed": "10/10/2025",
            "notes": (
                "Standards are abolished/adjusted by USA Swimming for the "
                "2024-2028 quad. Times in seconds (float). Relay rows "
                "(FR-R/MED-R) excluded. Stars in the PDF denote events also "
                "on the Scholastic All-America list and are not data."
            ),
        },
        "records": sorted(
            records,
            key=lambda r: (
                AGE_GROUPS.index(r["age_group"]), r["gender"], r["course"],
                r["stroke"], r["distance"],
            ),
        ),
    }

    OUT_PATH.write_text(json.dumps(dataset, indent=2), encoding="utf-8")
    print(f"Wrote {len(records)} records to {OUT_PATH}")

    # Summary by age group x course (Girls only, what the app uses)
    from collections import Counter

    counts = Counter(
        (r["age_group"], r["course"]) for r in records if r["gender"] == "Girls"
    )
    for (age, course), n in sorted(counts.items(), key=lambda kv: (AGE_GROUPS.index(kv[0][0]), kv[0][1])):
        print(f"  Girls {age:<12} {course}: {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
