"""
keepass.py
──────────
Thin wrapper around pykeepass for opening/creating the database
and inserting entries.
"""

from __future__ import annotations

import sys
from pathlib import Path

try:
    from pykeepass import PyKeePass, create_database
    from pykeepass.exceptions import CredentialsError
except ImportError:
    print("Error: pykeepass is not installed.")
    print("  Install it with:  pip install pykeepass")
    sys.exit(1)

from csv2keepass.csv_reader import Entry


def open_db(
    db_path: Path,
    password: str,
    keyfile: str | None,
    create: bool,
) -> PyKeePass:
    """Open (or optionally create) a KeePass database. Raises on failure."""
    if not db_path.exists():
        if create:
            print(f"  Database not found — creating: {db_path}")
            create_database(str(db_path), password=password, keyfile=keyfile)
        else:
            raise FileNotFoundError(
                f"Database not found: {db_path}\n"
                "  Use --create to create a new database."
            )
    try:
        return PyKeePass(str(db_path), password=password, keyfile=keyfile)
    except CredentialsError:
        raise ValueError("Wrong master password (or key file).")


def get_or_create_group(kp: PyKeePass, group_name: str | None):
    """Return the target group, creating it under root if it doesn't exist."""
    if group_name is None:
        return kp.root_group
    group = kp.find_groups(name=group_name, first=True)
    if group is None:
        print(f"  Group '{group_name}' not found — creating it.")
        group = kp.add_group(kp.root_group, group_name)
    return group


def add_entry(kp: PyKeePass, group, entry: Entry, title: str) -> None:
    """
    Add a single entry to the database and save immediately.
    Raises on any failure so the caller can handle it and mark the entry
    as errored without aborting the whole run.
    """
    kp.add_entry(
        destination_group=group,
        title=title,
        username=entry.username,
        password=entry.password,
        url=entry.url or None,
        notes=entry.note or None,
    )
    kp.save()
