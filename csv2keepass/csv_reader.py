"""
csv_reader.py
─────────────
Handles loading, detecting, normalising, and saving the password CSV file.

Supported formats
─────────────────
- Generic / Brave  : name, url, username, password[, note]
- Chrome / Chromium: name, url, username, password          (no note column)
  Chrome exports the column as "username" since ~2021; older exports
  used "Login Name" — both are handled.

Status column
─────────────
After the first processed entry the CSV will gain a "status" column:
  added   – entry was successfully inserted into KeePass
  skipped – user chose to skip
  error   – entry failed to save (will be retried on next run)
  (empty) – not yet processed
"""

import csv
from dataclasses import dataclass, field
from pathlib import Path


# ── Status values ────────────────────────────────────────────────────────────

STATUS_ADDED   = "added"
STATUS_SKIPPED = "skipped"
STATUS_ERROR   = "error"
STATUS_PENDING = ""

DONE_STATUSES  = {STATUS_ADDED, STATUS_SKIPPED}

STATUS_COL     = "status"
NOTE_COL       = "note"


# ── Column name aliases (maps any known variant → canonical name) ─────────────

_ALIASES: dict[str, str] = {
    # username
    "login name": "username",
    "login":      "username",
    "user":       "username",
    # url
    "website":    "url",
    "web site":   "url",
    "uri":        "url",
    # name / title
    "title":      "name",
    "site name":  "name",
}


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class Entry:
    """One password entry, normalised from whatever CSV format was detected."""
    name:     str
    url:      str
    username: str
    password: str
    note:     str
    status:   str = STATUS_PENDING

    # Back-reference to the original dict row so we can mutate and re-save it.
    _row: dict = field(default_factory=dict, repr=False, compare=False)

    @property
    def is_pending(self) -> bool:
        return self.status not in DONE_STATUSES

    def mark(self, status: str) -> None:
        self.status = status
        self._row[STATUS_COL] = status


# ── CSV I/O ───────────────────────────────────────────────────────────────────

def _normalise_headers(fieldnames: list[str]) -> dict[str, str]:
    """Return a mapping {original_header: canonical_header} for known aliases."""
    mapping: dict[str, str] = {}
    for h in fieldnames:
        canonical = _ALIASES.get(h.strip().lower())
        if canonical:
            mapping[h] = canonical
    return mapping


def _normalise_row(row: dict, mapping: dict[str, str]) -> dict[str, str]:
    out = {}
    for k, v in row.items():
        out[mapping.get(k, k)] = v
    return out


def _validate_columns(fieldnames: list[str]) -> None:
    required = {"name", "url", "username", "password"}
    canonical = {_ALIASES.get(h.strip().lower(), h.strip().lower()) for h in fieldnames}
    missing = required - canonical
    if missing:
        raise ValueError(
            f"CSV is missing required columns: {', '.join(sorted(missing))}.\n"
            f"  Found columns: {', '.join(fieldnames)}"
        )


def load(csv_path: Path) -> tuple[list[Entry], list[str]]:
    """
    Load a CSV file and return (entries, original_fieldnames).

    The original fieldnames list is kept so we can write the file back
    without reordering or dropping any user columns.
    """
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        # utf-8-sig strips the BOM that Chrome/Edge sometimes add
        reader     = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        _validate_columns(fieldnames)
        alias_map  = _normalise_headers(fieldnames)
        raw_rows   = list(reader)

    entries: list[Entry] = []
    for raw in raw_rows:
        row = _normalise_row(raw, alias_map)

        # Ensure status key exists in the original dict
        if STATUS_COL not in raw:
            raw[STATUS_COL] = STATUS_PENDING

        entry = Entry(
            name     = row.get("name",     "").strip(),
            url      = row.get("url",      "").strip(),
            username = row.get("username", "").strip(),
            password = row.get("password", "").strip(),
            note     = row.get(NOTE_COL,   "").strip(),
            status   = raw.get(STATUS_COL, STATUS_PENDING).strip(),
            _row     = raw,
        )
        entries.append(entry)

    return entries, fieldnames


def save(csv_path: Path, entries: list[Entry], original_fieldnames: list[str]) -> None:
    """Write all entries back to the CSV file, preserving column order."""
    # Make sure status column is included
    out_fields = list(original_fieldnames)
    if STATUS_COL not in out_fields:
        out_fields.append(STATUS_COL)

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=out_fields, extrasaction="ignore")
        writer.writeheader()
        for entry in entries:
            writer.writerow(entry._row)
