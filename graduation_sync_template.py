#!/usr/bin/env python3
"""
graduation_sync.py
------------------
Daily sync script for a graduation slideshow photo collection.

Usage:
    python3 "graduation_sync.py"

What it does (in order):
  1. Creates a DDMMYYYY_HH_MM timestamped subfolder in the destination
  2. Copies all student folders from the Google Drive source into that subfolder
  3. Renames student folders from abbreviated names to full student names
  3.5 Copies files 6–10 from each student folder into a shared group_pictures/ folder
  4. Generates an HTML report showing file counts and submission status per student

Setup:
  1. Mount your Google Drive locally (via Google Drive for Desktop)
  2. Update SOURCE to point to your shared Google Drive folder
  3. Update DEST_BASE to point to your local working folder
  4. Update STUDENT_MAP with your students' abbreviated → full name mapping
  5. Update EXPECTED_FILES to match how many files each student should submit
"""

import os
import re
import shutil
import webbrowser
from datetime import datetime

# ---------------------------------------------------------------------------
# Configuration — update these for your own use
# ---------------------------------------------------------------------------

# Path to the shared Google Drive folder (locally mounted via Google Drive for Desktop)
# Example: "/Users/yourname/Library/CloudStorage/GoogleDrive-you@gmail.com/My Drive/slideshow"
SOURCE = "/path/to/your/google_drive/slideshow_folder"

# Local folder where timestamped snapshots will be saved
# Example: "/Users/yourname/Desktop/slideshow/snapshots"
DEST_BASE = "/path/to/your/local/destination"

# How many files each student is expected to submit
EXPECTED_FILES = 6

# Mapping: abbreviated folder name (as it appears in Google Drive) → full student name
#
# Students typically create folders with short names like "Jane D" or "John S".
# Add one entry per student. The key is the folder name in Google Drive;
# the value is the full name you want to appear in the run folder and report.
#
# Examples covering common edge cases:
#   Single last name:       "Jane D"   → "Jane Doe"
#   Hyphenated last name:   "Anna LM"  → "Anna Lopez-Martinez"
#   Multi-part last name:   "Sofia SP" → "Sofia Sanchez Pinto"
#   Short last name:        "Roger L"  → "Roger Le"
#
STUDENT_MAP = {
    # Replace these with your actual students
    "Jane D":    "Jane Doe",
    "John S":    "John Smith",
    "Anna LM":   "Anna Lopez-Martinez",
    "Sofia SP":  "Sofia Sanchez Pinto",
    "Roger L":   "Roger Le",
    # ... add all your students here
}

# Hidden / system files to skip during copy
IGNORE_PATTERNS = shutil.ignore_patterns(
    ".DS_Store", "._*", ".dropbox", "desktop.ini", "Thumbs.db"
)


# ---------------------------------------------------------------------------
# Helper — anonymize a full name to "First L." for privacy-safe output
# ---------------------------------------------------------------------------

def anonymize_name(full_name: str) -> str:
    """
    Convert a full student name to 'First L.' format.
    Used in terminal output so screen recordings don't expose full last names.
    E.g. 'Jane Doe' → 'Jane D.'
         'Sofia Sanchez Pinto' → 'Sofia P.'
         'Anna Lopez-Martinez' → 'Anna L.'
    """
    parts = full_name.split()
    first = parts[0]
    last_initial = parts[-1][0].upper() if len(parts) > 1 else ""
    return f"{first} {last_initial}." if last_initial else first


# ---------------------------------------------------------------------------
# Step 1 — Create timestamped run folder
# ---------------------------------------------------------------------------

def create_run_folder(dest_base: str, now: datetime) -> str:
    """
    Create (or reuse) a DDMMYYYY_HH_MM subfolder inside dest_base.
    Returns the full path to the run folder.
    """
    folder_name = now.strftime("%d%m%Y_%H_%M")
    run_folder = os.path.join(dest_base, folder_name)

    if os.path.exists(run_folder):
        print(f"[Step 1] Run folder already exists — reusing: {run_folder}")
    else:
        os.makedirs(run_folder)
        print(f"[Step 1] Created run folder: {run_folder}")

    return run_folder


# ---------------------------------------------------------------------------
# Step 2 — Copy student folders from source to run folder
# ---------------------------------------------------------------------------

def copy_student_files(source: str, run_folder: str) -> list[str]:
    """
    Copy every student subfolder from source into run_folder.
    Preserves the complete directory tree as-is (no flattening).
    Skips hidden/system files. Never touches the source.
    Returns list of abbreviated student folder names that were copied.
    """
    if not os.path.isdir(source):
        raise FileNotFoundError(f"Source folder not found: {source}")

    copied = []
    entries = sorted(os.scandir(source), key=lambda e: e.name)

    for entry in entries:
        if not entry.is_dir():
            continue
        if entry.name.startswith("."):
            continue  # skip hidden dirs

        dest_dir = os.path.join(run_folder, entry.name)

        # Also check if the folder was already copied and renamed to full student name
        full_name = STUDENT_MAP.get(entry.name)
        full_dest_dir = os.path.join(run_folder, full_name) if full_name else None

        if os.path.exists(dest_dir) or (full_dest_dir and os.path.exists(full_dest_dir)):
            print(f"  [skip] Already copied: {entry.name}")
            copied.append(entry.name)
            continue

        shutil.copytree(entry.path, dest_dir, ignore=IGNORE_PATTERNS, copy_function=shutil.copy2)
        file_count = sum(
            1 for e in os.scandir(dest_dir)
            if e.is_file() and not e.name.startswith(".")
        )
        print(f"  [copy] {entry.name} → {file_count} file(s)")
        copied.append(entry.name)

    print(f"[Step 2] Copied {len(copied)} student folder(s) to run folder.")
    return copied


# ---------------------------------------------------------------------------
# Step 3 — Rename abbreviated folders → full student names
# ---------------------------------------------------------------------------

def rename_folders(run_folder: str) -> dict[str, int]:
    """
    Rename each abbreviated folder inside run_folder to the full student name
    defined in STUDENT_MAP.  Also creates empty folders for any student in the
    master list who had no source folder (so every student appears in the report).

    Returns a dict: { full_student_name: file_count }
    """
    # Rename existing abbreviated folders
    for abbrev, full_name in STUDENT_MAP.items():
        old_path = os.path.join(run_folder, abbrev)
        new_path = os.path.join(run_folder, full_name)

        if os.path.exists(old_path) and not os.path.exists(new_path):
            os.rename(old_path, new_path)
            print(f"  [rename] '{abbrev}' → '{anonymize_name(full_name)}'")
        elif os.path.exists(new_path):
            pass  # already renamed (idempotent re-run)

    # Ensure every student in the master list has a folder (even if empty)
    all_full_names = set(STUDENT_MAP.values())
    for full_name in all_full_names:
        folder_path = os.path.join(run_folder, full_name)
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            print(f"  [create] Empty folder for: {anonymize_name(full_name)} (no source folder found)")

    # Build file-count dict (root-level files only — subfolders are not counted)
    counts: dict[str, int] = {}
    for full_name in sorted(all_full_names):
        folder_path = os.path.join(run_folder, full_name)
        count = sum(
            1 for e in os.scandir(folder_path)
            if e.is_file() and not e.name.startswith(".")
        )
        counts[full_name] = count

    print(f"[Step 3] Folder renaming complete.")
    return counts


# ---------------------------------------------------------------------------
# Step 3.5 — Collect group pictures (files 6–10) into group_pictures folder
# ---------------------------------------------------------------------------

def collect_group_pictures(run_folder: str) -> int:
    """
    For every root-level file in each student folder whose numeric prefix is
    between 6 and 10 (inclusive), copy it into run_folder/group_pictures/.

    Files are matched by a leading number followed by a space, e.g. "6 photo.jpg".
    Files 1–5 and 100+ are left untouched in the student folder.
    Files 6–10 are COPIED (not moved), so they remain in the student folder too.

    Returns the total number of files copied into group_pictures.
    """
    group_dir = os.path.join(run_folder, "group_pictures")
    os.makedirs(group_dir, exist_ok=True)

    total_copied = 0
    all_full_names = set(STUDENT_MAP.values())

    for student_name in sorted(all_full_names):
        student_dir = os.path.join(run_folder, student_name)
        if not os.path.isdir(student_dir):
            continue

        copied_for_student = []
        for entry in sorted(os.scandir(student_dir), key=lambda e: e.name):
            if not entry.is_file() or entry.name.startswith("."):
                continue

            match = re.match(r'^(\d+)\s', entry.name)
            if not match:
                continue

            num = int(match.group(1))
            if 6 <= num <= 10:
                dest = os.path.join(group_dir, entry.name)
                shutil.copy2(entry.path, dest)
                copied_for_student.append(entry.name)
                total_copied += 1

        if copied_for_student:
            print(f"  [group] {anonymize_name(student_name)}: {len(copied_for_student)} file(s) → group_pictures/")

    print(f"[Step 3.5] {total_copied} group picture(s) collected into group_pictures/")
    return total_copied


# ---------------------------------------------------------------------------
# Step 4 — Generate HTML report
# ---------------------------------------------------------------------------

def generate_report(counts: dict[str, int], run_folder: str, timestamp: str) -> str:
    """
    Produce an HTML report showing file counts and submission status per student.
    Expected: EXPECTED_FILES files per student.
    Saves to run_folder/report_DDMMYYYY_HH_MM.html and opens in default browser.
    Returns the path to the report file.
    """
    total_students = len(counts)
    submitted = sum(1 for c in counts.values() if c > 0)
    complete  = sum(1 for c in counts.values() if c == EXPECTED_FILES)

    def row_style(count: int) -> tuple[str, str, str]:
        """Returns (bg_color, emoji, label)."""
        if count == 0:
            return "#ffd6d6", "🔴", "No files"
        elif count < EXPECTED_FILES:
            return "#fff3cd", "🟡", f"Partial ({count}/{EXPECTED_FILES})"
        elif count == EXPECTED_FILES:
            return "#d4edda", "✅", "Complete"
        else:  # count > EXPECTED_FILES
            return "#cce5ff", "🔵", f"Extra ({count}/{EXPECTED_FILES})"

    rows_html = ""
    for i, (name, count) in enumerate(sorted(counts.items()), start=1):
        bg, emoji, label = row_style(count)
        rows_html += f"""
        <tr style="background:{bg};">
            <td style="text-align:center;">{i}</td>
            <td>{name}</td>
            <td style="text-align:center;font-weight:bold;">{count}</td>
            <td>{emoji} {label}</td>
        </tr>"""

    run_label = datetime.strptime(timestamp, "%d%m%Y_%H_%M").strftime(
        "%B %d, %Y at %I:%M %p"
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Graduation Slideshow — Submission Report</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
      max-width: 800px;
      margin: 40px auto;
      padding: 0 20px;
      color: #222;
      background: #f9f9f9;
    }}
    h1 {{ color: #2c3e50; margin-bottom: 4px; }}
    .subtitle {{ color: #666; margin-bottom: 24px; font-size: 0.95em; }}
    .summary {{
      background: #fff;
      border: 1px solid #ddd;
      border-radius: 8px;
      padding: 16px 20px;
      margin-bottom: 24px;
      display: flex;
      gap: 32px;
      flex-wrap: wrap;
    }}
    .stat {{ text-align: center; }}
    .stat .num {{ font-size: 2em; font-weight: bold; color: #2c3e50; }}
    .stat .lbl {{ font-size: 0.85em; color: #666; margin-top: 2px; }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: #fff;
      border-radius: 8px;
      overflow: hidden;
      box-shadow: 0 1px 4px rgba(0,0,0,0.08);
    }}
    thead tr {{ background: #2c3e50; color: #fff; }}
    th, td {{
      padding: 10px 14px;
      text-align: left;
      border-bottom: 1px solid #eee;
      font-size: 0.95em;
    }}
    th {{ font-weight: 600; letter-spacing: 0.03em; }}
    tr:last-child td {{ border-bottom: none; }}
    .legend {{
      margin-top: 20px;
      font-size: 0.85em;
      color: #555;
      display: flex;
      gap: 20px;
      flex-wrap: wrap;
    }}
    .legend span {{ display: flex; align-items: center; gap: 6px; }}
    footer {{ margin-top: 32px; font-size: 0.8em; color: #aaa; text-align: center; }}
  </style>
</head>
<body>
  <h1>🎓 Graduation Slideshow</h1>
  <p class="subtitle">Submission report — {run_label}</p>

  <div class="summary">
    <div class="stat">
      <div class="num">{total_students}</div>
      <div class="lbl">Total students</div>
    </div>
    <div class="stat">
      <div class="num">{submitted}</div>
      <div class="lbl">Submitted any files</div>
    </div>
    <div class="stat">
      <div class="num">{complete}</div>
      <div class="lbl">Submitted all {EXPECTED_FILES} files</div>
    </div>
    <div class="stat">
      <div class="num">{total_students - submitted}</div>
      <div class="lbl">No files yet</div>
    </div>
  </div>

  <table>
    <thead>
      <tr>
        <th style="width:40px;">#</th>
        <th>Student Name</th>
        <th style="width:90px;">Files</th>
        <th>Status</th>
      </tr>
    </thead>
    <tbody>{rows_html}
    </tbody>
  </table>

  <div class="legend">
    <span>🔴 No files</span>
    <span>🟡 Partial (1–{EXPECTED_FILES - 1} files)</span>
    <span>✅ Complete ({EXPECTED_FILES} files)</span>
    <span>🔵 Extra (&gt;{EXPECTED_FILES} files)</span>
  </div>

  <footer>
    Run folder: {run_folder}<br>
    Generated by graduation_sync.py
  </footer>
</body>
</html>
"""

    report_filename = f"report_{timestamp}.html"
    report_path = os.path.join(run_folder, report_filename)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"[Step 4] Report saved: {report_path}")
    return report_path


# ---------------------------------------------------------------------------
# Step 4b — Generate anonymized HTML report (first name + last initial only)
# ---------------------------------------------------------------------------

def generate_anonymized_report(counts: dict[str, int], run_folder: str, timestamp: str) -> str:
    """
    Same layout as generate_report() but replaces every full student name
    with 'First L.' so the file is safe to share publicly (e.g. YouTube).
    Saves as report_anon_DDMMYYYY_HH_MM.html inside run_folder.
    Returns the path to the anonymized report file.
    """
    # Build anonymized counts dict, handling potential collisions by appending a counter
    anon_counts: dict[str, int] = {}
    for full_name, count in counts.items():
        anon = anonymize_name(full_name)
        if anon in anon_counts:
            suffix = 2
            while f"{anon} ({suffix})" in anon_counts:
                suffix += 1
            anon = f"{anon} ({suffix})"
        anon_counts[anon] = count

    total_students = len(anon_counts)
    submitted = sum(1 for c in anon_counts.values() if c > 0)
    complete  = sum(1 for c in anon_counts.values() if c == EXPECTED_FILES)

    def row_style(count: int) -> tuple[str, str, str]:
        if count == 0:
            return "#ffd6d6", "🔴", "No files"
        elif count < EXPECTED_FILES:
            return "#fff3cd", "🟡", f"Partial ({count}/{EXPECTED_FILES})"
        elif count == EXPECTED_FILES:
            return "#d4edda", "✅", "Complete"
        else:
            return "#cce5ff", "🔵", f"Extra ({count}/{EXPECTED_FILES})"

    rows_html = ""
    for i, (name, count) in enumerate(sorted(anon_counts.items()), start=1):
        bg, emoji, label = row_style(count)
        rows_html += f"""
        <tr style="background:{bg};">
            <td style="text-align:center;">{i}</td>
            <td>{name}</td>
            <td style="text-align:center;font-weight:bold;">{count}</td>
            <td>{emoji} {label}</td>
        </tr>"""

    run_label = datetime.strptime(timestamp, "%d%m%Y_%H_%M").strftime(
        "%B %d, %Y at %I:%M %p"
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Graduation Slideshow — Submission Report (Anonymized)</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
      max-width: 800px;
      margin: 40px auto;
      padding: 0 20px;
      color: #222;
      background: #f9f9f9;
    }}
    h1 {{ color: #2c3e50; margin-bottom: 4px; }}
    .subtitle {{ color: #666; margin-bottom: 4px; font-size: 0.95em; }}
    .anon-badge {{
      display: inline-block;
      background: #e8f4f8;
      border: 1px solid #b8d9e8;
      border-radius: 4px;
      padding: 2px 8px;
      font-size: 0.8em;
      color: #2980b9;
      margin-bottom: 20px;
    }}
    .summary {{
      background: #fff;
      border: 1px solid #ddd;
      border-radius: 8px;
      padding: 16px 20px;
      margin-bottom: 24px;
      display: flex;
      gap: 32px;
      flex-wrap: wrap;
    }}
    .stat {{ text-align: center; }}
    .stat .num {{ font-size: 2em; font-weight: bold; color: #2c3e50; }}
    .stat .lbl {{ font-size: 0.85em; color: #666; margin-top: 2px; }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: #fff;
      border-radius: 8px;
      overflow: hidden;
      box-shadow: 0 1px 4px rgba(0,0,0,0.08);
    }}
    thead tr {{ background: #2c3e50; color: #fff; }}
    th, td {{
      padding: 10px 14px;
      text-align: left;
      border-bottom: 1px solid #eee;
      font-size: 0.95em;
    }}
    th {{ font-weight: 600; letter-spacing: 0.03em; }}
    tr:last-child td {{ border-bottom: none; }}
    .legend {{
      margin-top: 20px;
      font-size: 0.85em;
      color: #555;
      display: flex;
      gap: 20px;
      flex-wrap: wrap;
    }}
    .legend span {{ display: flex; align-items: center; gap: 6px; }}
    footer {{ margin-top: 32px; font-size: 0.8em; color: #aaa; text-align: center; }}
  </style>
</head>
<body>
  <h1>🎓 Graduation Slideshow</h1>
  <p class="subtitle">Submission report — {run_label}</p>
  <p class="anon-badge">🔒 Anonymized — first name &amp; last initial only</p>

  <div class="summary">
    <div class="stat">
      <div class="num">{total_students}</div>
      <div class="lbl">Total students</div>
    </div>
    <div class="stat">
      <div class="num">{submitted}</div>
      <div class="lbl">Submitted any files</div>
    </div>
    <div class="stat">
      <div class="num">{complete}</div>
      <div class="lbl">Submitted all {EXPECTED_FILES} files</div>
    </div>
    <div class="stat">
      <div class="num">{total_students - submitted}</div>
      <div class="lbl">No files yet</div>
    </div>
  </div>

  <table>
    <thead>
      <tr>
        <th style="width:40px;">#</th>
        <th>Student</th>
        <th style="width:90px;">Files</th>
        <th>Status</th>
      </tr>
    </thead>
    <tbody>{rows_html}
    </tbody>
  </table>

  <div class="legend">
    <span>🔴 No files</span>
    <span>🟡 Partial (1–{EXPECTED_FILES - 1} files)</span>
    <span>✅ Complete ({EXPECTED_FILES} files)</span>
    <span>🔵 Extra (&gt;{EXPECTED_FILES} files)</span>
  </div>

  <footer>
    Generated by graduation_sync.py
  </footer>
</body>
</html>
"""

    report_filename = f"report_anon_{timestamp}.html"
    report_path = os.path.join(run_folder, report_filename)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"[Step 4b] Anonymized report saved: {report_path}")
    return report_path


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------

def main():
    now = datetime.now()
    timestamp = now.strftime("%d%m%Y_%H_%M")

    print("=" * 60)
    print("  Graduation Slideshow Sync")
    print(f"  {now.strftime('%B %d, %Y %I:%M %p')}")
    print("=" * 60)

    # Step 1
    run_folder = create_run_folder(DEST_BASE, now)

    # Step 2
    print("\n[Step 2] Copying student folders from Google Drive source...")
    copy_student_files(SOURCE, run_folder)

    # Step 3
    print("\n[Step 3] Renaming folders to full student names...")
    counts = rename_folders(run_folder)

    # Step 3.5
    print("\n[Step 3.5] Collecting group pictures (files 6–10)...")
    collect_group_pictures(run_folder)

    # Step 4
    print("\n[Step 4] Generating HTML report...")
    report_path = generate_report(counts, run_folder, timestamp)

    # Step 4b
    print("\n[Step 4b] Generating anonymized HTML report...")
    anon_report_path = generate_anonymized_report(counts, run_folder, timestamp)

    # Summary
    submitted = sum(1 for c in counts.values() if c > 0)
    complete  = sum(1 for c in counts.values() if c == EXPECTED_FILES)
    print("\n" + "=" * 60)
    print(f"  ✅ Done!  {submitted}/{len(counts)} students submitted files")
    print(f"  ✅ Complete ({EXPECTED_FILES} files): {complete}/{len(counts)}")
    print(f"  📄 Report:            {report_path}")
    print(f"  🔒 Anonymized report: {anon_report_path}")
    print("=" * 60)

    # Open report in default browser
    webbrowser.open(f"file://{report_path}")


if __name__ == "__main__":
    main()
