# Graduation Slideshow Photo Organizer

A Python script that tracks and organizes student photo submissions for a graduation slideshow. Built to manage a class of students each submitting photos via a shared Google Drive folder.

---

## What it does

Each time you run it, the script:

1. **Snapshots** all student folders from Google Drive into a local `DDMMYYYY_HH_MM` timestamped folder — so every run is preserved and you can compare across days
2. **Renames** abbreviated student folders (e.g. `Jane D`) to full names (e.g. `Jane Doe`)
3. **Collects group pictures** — files numbered 6–10 in each student folder are copied into a shared `group_pictures/` folder for the "shared memories" section of the slideshow
4. **Generates two HTML reports**:
   - Full-name report for your own use
   - Anonymized report (first name + last initial only) safe to share or screen-record

Reports are color-coded by submission status:

| Color | Meaning |
|---|---|
| 🔴 Red | No files submitted |
| 🟡 Yellow | Partial (fewer than expected) |
| ✅ Green | Complete |
| 🔵 Blue | Extra files submitted |

---

## Setup

### Requirements

- Python 3.10+
- Google Drive mounted locally via [Google Drive for Desktop](https://www.google.com/drive/download/)
- No third-party Python packages needed (stdlib only)

### Configuration

Open `graduation_sync_template.py` and update the three sections at the top:

```python
# Path to your shared Google Drive folder (locally mounted)
SOURCE = "/path/to/your/google_drive/slideshow_folder"

# Local folder where timestamped snapshots will be saved
DEST_BASE = "/path/to/your/local/destination"

# How many files each student is expected to submit
EXPECTED_FILES = 6

# Abbreviated folder name → full student name
STUDENT_MAP = {
    "Jane D":   "Jane Doe",
    "John S":   "John Smith",
    # ... add all your students
}
```

### Run

```bash
python3 graduation_sync_template.py
```

The script opens the HTML report in your browser automatically when done.

---

## File naming convention for group pictures

The script expects student files to be named with a leading number followed by a space:

```
1 baby_photo.jpg
2 first_grade.jpg
...
6 class_photo_2019.jpg   ← copied to group_pictures/
7 class_photo_2020.jpg   ← copied to group_pictures/
...
10 class_photo_2023.jpg  ← copied to group_pictures/
100 bonus_photo.jpg      ← left in student folder only
```

Files 6–10 go to `group_pictures/`. Files 1–5 and 100+ stay in the student folder only.

---

## Output structure

```
destination/
└── 25052026_11_35/           ← timestamped run folder
    ├── Jane D./               ← renamed student folders
    ├── John S./
    ├── ...
    ├── group_pictures/        ← shared group photos from all students
    ├── report_25052026_11_35.html        ← full-name report
    └── report_anon_25052026_11_35.html   ← anonymized report
```

---

## Re-running

The script is idempotent — running it twice in the same minute reuses the existing folder and skips already-copied student folders. Run it again in a new minute to get a fresh snapshot.

---

## Privacy

- The script **never modifies source files** — Google Drive content is always read-only
- Terminal output uses first name + last initial only (safe to screen-record)
- The anonymized HTML report uses first name + last initial only (safe to share)
- Student photos and run folders should be kept local — see `.gitignore`

---

## Background

Built with [Claude](https://claude.ai) through an iterative prompting conversation — no prior Python experience required to adapt it. The full build process is documented in a YouTube video (link coming soon).
