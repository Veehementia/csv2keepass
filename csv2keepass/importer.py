"""
importer.py
───────────
Orchestrates the import loop in three modes:

  auto     – import everything without asking, using the CSV name as-is
  manual   – ask the user to confirm / rename / skip each entry
  mixed    – start in manual mode; the user can type 'a' at any prompt
             to switch to auto for all remaining entries
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path

from pykeepass import PyKeePass

from csv2keepass import csv_reader
from csv2keepass.csv_reader import Entry, STATUS_ADDED, STATUS_ERROR, STATUS_SKIPPED
from csv2keepass.keepass import add_entry


# ── Mode ─────────────────────────────────────────────────────────────────────

class Mode(Enum):
    AUTO   = auto()
    MANUAL = auto()
    MIXED  = auto()   # starts as MANUAL, can switch to AUTO mid-run


# ── Result tracking ───────────────────────────────────────────────────────────

@dataclass
class ImportResult:
    added:        int = 0
    skipped:      int = 0
    errors:       int = 0
    already_done: int = 0
    error_names:  list[str] = field(default_factory=list)

    @property
    def total_processed(self) -> int:
        return self.added + self.skipped + self.errors


# ── UI helpers ────────────────────────────────────────────────────────────────

SEP = "─" * 54

def _mask(pwd: str) -> str:
    return "*" * len(pwd) if pwd else "(empty)"


def _print_entry(entry: Entry, i: int, total: int) -> None:
    print(f"\n{SEP}")
    print(f"  Entry {i} of {total}")
    print(SEP)
    print(f"  Name     : {entry.name     or '(empty)'}")
    print(f"  URL      : {entry.url      or '(empty)'}")
    print(f"  Username : {entry.username or '(empty)'}")
    print(f"  Password : {_mask(entry.password)}")
    if entry.note:
        print(f"  Note     : {entry.note}")
    print(SEP)


def _prompt_manual(entry: Entry, i: int, total: int, mixed: bool) -> tuple[str | None, bool]:
    """
    Interactive prompt for a single entry.

    Returns (title, switch_to_auto):
      title          – chosen title string, or None to skip
      switch_to_auto – True if the user asked to continue automatically
    """
    _print_entry(entry, i, total)

    auto_hint = "  [a]            switch to automatic for remaining entries\n" if mixed else ""

    while True:
        print(f"  [Enter]        keep name as-is  → '{entry.name or '(empty)'}'")
        print(f"  [custom name]  type a new name and press Enter")
        print(f"  [s]            skip this entry")
        if mixed:
            print(f"  [a]            switch to automatic for all remaining entries")
        raw = input("  Your choice: ").strip()

        if raw.lower() == "s":
            return None, False
        if mixed and raw.lower() == "a":
            return entry.name or None, True   # use default name, then go auto
        if raw == "":
            return entry.name or None, False
        return raw, False


# ── Core import loop ──────────────────────────────────────────────────────────

def run(
    csv_path: Path,
    kp: PyKeePass,
    group,
    mode: Mode,
) -> ImportResult:
    entries, fieldnames = csv_reader.load(csv_path)

    pending      = [e for e in entries if e.is_pending]
    already_done = len(entries) - len(pending)
    total        = len(pending)

    result = ImportResult(already_done=already_done)

    if already_done:
        label = "entry" if already_done == 1 else "entries"
        print(f"  Resuming — {already_done} {label} already processed, {total} remaining.")

    if total == 0:
        print("  Nothing left to process.")
        return result

    # In MIXED mode we start in manual and may switch to auto mid-run.
    effective_auto = (mode == Mode.AUTO)

    for i, entry in enumerate(pending, start=1):

        # ── Determine title ──────────────────────────────────────────────────
        switch_to_auto = False

        if effective_auto:
            title = entry.name or None
            if title:
                print(f"  [{i}/{total}] Auto-importing '{title}' …", end=" ", flush=True)
            else:
                print(f"  [{i}/{total}] Skipping — entry has no name.")
                _mark_and_save(entry, STATUS_SKIPPED, entries, fieldnames, csv_path)
                result.skipped += 1
                continue
        else:
            title, switch_to_auto = _prompt_manual(
                entry, i, total, mixed=(mode == Mode.MIXED)
            )

        # ── Skip ─────────────────────────────────────────────────────────────
        if title is None:
            _mark_and_save(entry, STATUS_SKIPPED, entries, fieldnames, csv_path)
            if not effective_auto:
                print(f"  → Skipped.")
            else:
                print("skipped.")
            result.skipped += 1

            if switch_to_auto:
                effective_auto = True
            continue

        # ── Add to KeePass ───────────────────────────────────────────────────
        try:
            add_entry(kp, group, entry, title)
            _mark_and_save(entry, STATUS_ADDED, entries, fieldnames, csv_path)
            if effective_auto:
                print("done.")
            else:
                print(f"  → Added as '{title}'.")
            result.added += 1

        except Exception as exc:
            _mark_and_save(entry, STATUS_ERROR, entries, fieldnames, csv_path)
            if effective_auto:
                print(f"ERROR.")
            else:
                print(f"  → ERROR saving entry.")
            print(f"     {type(exc).__name__}: {exc}")
            result.errors += 1
            result.error_names.append(entry.name or "(unnamed)")

        if switch_to_auto:
            effective_auto = True
            print(f"\n  Switching to automatic mode for the remaining entries …\n")

    return result


# ── Helpers ───────────────────────────────────────────────────────────────────

def _mark_and_save(
    entry: Entry,
    status: str,
    all_entries: list[Entry],
    fieldnames: list[str],
    csv_path: Path,
) -> None:
    entry.mark(status)
    csv_reader.save(csv_path, all_entries, fieldnames)
