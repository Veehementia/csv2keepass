# csv2keepass

Import browser-exported CSV password files into a KeePass (`.kdbx`) database — with safe, resumable progress tracking. Uses ```pykeepass```.

## Features

- **Browser support** — Chrome, Chromium, Brave, and any CSV with `name`, `url`, `username`, `password` columns
- **Three import modes** — fully automatic, fully manual (review each entry), or mixed (manual with a one-key switch to auto)
- **Resumable** — the CSV is updated with a `status` column after every entry; interrupted runs pick up exactly where they left off
- **Error-safe** — individual save failures are recorded and retried on the next run without stopping the import
- **Final report** — summary of added, skipped, errored, and already-processed entries
- **Secure password prompt** — master password is never echoed to the terminal and never stored

---

## Installation

**Requirements:** Python 3.10+

Install using pip:
```bash
pip install git+https://github.com/Veehementia/csv2keepass
```

Or install from source:
```bash
git clone https://github.com/Veehementia/csv2keepass
cd csv2keepass
pip install .
```

---

## Usage

```
csv2keepass --csv FILE --db FILE [options]
```

### Options

| Flag | Description |
|---|---|
| `--csv FILE` | Path to the exported browser CSV file **(required)** |
| `--db FILE` | Path to the KeePass `.kdbx` database **(required)** |
| `--password PASS` | Master password. Omit to be prompted securely *(recommended)* |
| `--keyfile FILE` | Path to a KeePass key file *(optional)* |
| `--create` | Create the database if it does not exist |
| `--group NAME` | Target group inside KeePass (created if missing; defaults to root) |
| `--mode MODE` | Import mode: `auto`, `manual` *(default)*, or `mixed` |

### Import modes

| Mode | Behaviour |
|---|---|
| `manual` | Review every entry — confirm the name, rename it, or skip it |
| `auto` | Import all pending entries automatically using the CSV name |
| `mixed` | Start in manual mode; type `a` at any prompt to switch the rest to auto |

---

## Examples

```bash
# Prompt for password, review every entry:
csv2keepass --csv passwords.csv --db mydb.kdbx

# Create a new database and import everything automatically:
csv2keepass --csv passwords.csv --db new.kdbx --create --mode auto

# Import into a group called "Brave", start manual, switch to auto later:
csv2keepass --csv passwords.csv --db mydb.kdbx --group Brave --mode mixed

# Use a key file alongside the master password:
csv2keepass --csv passwords.csv --db mydb.kdbx --keyfile mydb.keyx
```

---

## Exporting from your browser

### Chrome / Chromium
1. Go to `chrome://password-manager/passwords`
2. Click the **Settings** icon (top-right)
3. Click **Export passwords** → **Export passwords**

### Brave
1. Go to `brave://password-manager/passwords`
2. Click the **Settings** icon (top-right)
3. Click **Export passwords** → **Export**

---

## CSV format

The tool accepts any CSV with these columns (column order does not matter):

| Column | Required | Notes |
|---|---|---|
| `name` | ✅ | Entry title |
| `url` | ✅ | Site URL |
| `username` | ✅ | Login username or email |
| `password` | ✅ | Login password |
| `note` | ❌ | Optional notes (Brave exports this; Chrome does not) |

After the first run, a `status` column is appended:

| Value | Meaning |
|---|---|
| `added` | Successfully inserted — skipped on future runs |
| `skipped` | User chose to skip — skipped on future runs |
| `error` | Save failed — **retried** on the next run |
| *(empty)* | Not yet processed |

---

## Security notes

- Avoid passing `--password` on the command line — it will appear in your shell history. Omit the flag to be prompted securely instead.
- Delete the CSV file after a successful import — it stores passwords in plain text.
- The KeePass database is saved immediately after each successful entry, so a crash can never cause a partially-saved entry.

---

## License

MIT
