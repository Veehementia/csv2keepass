"""
cli.py
──────
Command-line interface for csv2keepass.
"""

from __future__ import annotations

import getpass
import sys
from pathlib import Path

import argparse

from csv2keepass.importer import Mode, run
from csv2keepass.keepass  import open_db, get_or_create_group


# ── Argument parser ───────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="csv2keepass",
        description=(
            "Import browser-exported CSV password files into a KeePass database.\n\n"
            "Supported CSV formats:\n"
            "  • Chrome / Chromium  (name, url, username, password)\n"
            "  • Brave              (name, url, username, password, note)\n"
            "  • Any CSV with those columns (extra columns are preserved)\n\n"
            "The CSV file is updated with a 'status' column after each entry so\n"
            "the import can be safely interrupted and resumed later.\n"
            "Entries marked 'added' or 'skipped' are never re-processed."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "examples:\n"
            "  # Basic import (will prompt for password):\n"
            "  csv2keepass --csv passwords.csv --db mydb.kdbx\n\n"
            "  # Create a new database and import automatically:\n"
            "  csv2keepass --csv passwords.csv --db new.kdbx --create --mode auto\n\n"
            "  # Import into a specific group, start manual, switch to auto later:\n"
            "  csv2keepass --csv passwords.csv --db mydb.kdbx --group Brave --mode mixed\n\n"
            "  # Use a key file in addition to the master password:\n"
            "  csv2keepass --csv passwords.csv --db mydb.kdbx --keyfile mydb.keyx\n"
        ),
    )

    # Required
    parser.add_argument(
        "--csv",
        required=True,
        metavar="FILE",
        help="Path to the exported browser CSV file.",
    )
    parser.add_argument(
        "--db",
        required=True,
        metavar="FILE",
        help="Path to the KeePass database (.kdbx).",
    )

    # Auth
    parser.add_argument(
        "--password",
        default=None,
        metavar="PASS",
        help=(
            "Master password for the KeePass database. "
            "Omit this flag to be prompted securely (recommended — "
            "passing passwords on the command line leaks them into shell history)."
        ),
    )
    parser.add_argument(
        "--keyfile",
        default=None,
        metavar="FILE",
        help="Path to a KeePass key file (optional, used alongside the master password).",
    )

    # Database options
    parser.add_argument(
        "--create",
        action="store_true",
        help="Create the KeePass database if it does not already exist.",
    )
    parser.add_argument(
        "--group",
        default=None,
        metavar="NAME",
        help=(
            "Name of the group inside KeePass to import into. "
            "The group is created if it does not exist. "
            "Defaults to the root group."
        ),
    )

    # Import mode
    parser.add_argument(
        "--mode",
        choices=["auto", "manual", "mixed"],
        default="manual",
        help=(
            "Import mode (default: manual).\n"
            "  auto   – import all entries automatically using the CSV name.\n"
            "  manual – review and confirm (or rename/skip) each entry.\n"
            "  mixed  – start in manual mode; type 'a' at any prompt to\n"
            "           switch to automatic for all remaining entries."
        ),
    )

    return parser


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = build_parser()
    args   = parser.parse_args()

    csv_path = Path(args.csv)
    db_path  = Path(args.db)

    # ── Validate inputs ───────────────────────────────────────────────────────
    if not csv_path.exists():
        parser.error(f"CSV file not found: {csv_path}")

    # ── Auth ──────────────────────────────────────────────────────────────────
    password = args.password
    if not password:
        try:
            password = getpass.getpass("Master password: ")
        except KeyboardInterrupt:
            print("\nAborted.")
            sys.exit(0)

    # ── Open database ─────────────────────────────────────────────────────────
    print()
    try:
        kp = open_db(db_path, password, args.keyfile, args.create)
    except (FileNotFoundError, ValueError, Exception) as exc:
        print(f"Error opening database: {exc}")
        sys.exit(1)

    # ── Target group ──────────────────────────────────────────────────────────
    try:
        group = get_or_create_group(kp, args.group)
    except Exception as exc:
        print(f"Error accessing group: {exc}")
        sys.exit(1)

    # ── Mode ──────────────────────────────────────────────────────────────────
    mode = {
        "auto":   Mode.AUTO,
        "manual": Mode.MANUAL,
        "mixed":  Mode.MIXED,
    }[args.mode]

    # ── Summary header ────────────────────────────────────────────────────────
    print(f"  CSV file  : {csv_path}")
    print(f"  Database  : {db_path}")
    print(f"  Group     : {group.name}")
    print(f"  Mode      : {args.mode}")
    if args.mode == "manual":
        print("  Tip       : use --mode mixed to switch to auto mid-run.\n")
    else:
        print()

    # ── Run import ────────────────────────────────────────────────────────────
    try:
        result = run(csv_path, kp, group, mode)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user. Progress has been saved to the CSV.")
        sys.exit(0)
    except Exception as exc:
        print(f"\nUnexpected error: {exc}")
        sys.exit(1)

    # ── Final report ──────────────────────────────────────────────────────────
    _print_report(result, db_path, csv_path)

    sys.exit(1 if result.errors else 0)


def _print_report(result, db_path: Path, csv_path: Path) -> None:
    from csv2keepass.importer import ImportResult  # local import to avoid circularity
    SEP = "─" * 54

    print(f"\n{SEP}")
    print("  Import complete — summary")
    print(SEP)
    print(f"  Added successfully : {result.added}")
    print(f"  Skipped            : {result.skipped}")
    print(f"  Errors             : {result.errors}")
    print(f"  Already processed  : {result.already_done}")
    print(SEP)

    if result.errors:
        print("  The following entries failed and are marked 'error' in the CSV.")
        print("  Fix any issues and re-run — they will be retried automatically.")
        for name in result.error_names:
            print(f"    • {name}")
        print(SEP)

    print(f"  Database : {db_path}")
    print(f"  CSV      : {csv_path}")
    print(SEP)
