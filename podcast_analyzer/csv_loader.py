# This module reads CSV files into a list of dictionaries

import csv
import re

from pathlib import Path
from speaker import SpeakerProfile
from .exceptions import InvalidIdentifierError

# Take in a csv file path and return the rows
def read_csv_rows(file_path: str | Path) -> list[dict[str, str]]:
    # Make sure the path is a Path object
    path = Path(file_path)

    # Open the file and read it with csv's DictReader
    with open(path, "r", encoding="utf-8", newline='') as csv_file:
        reader = csv.DictReader(csv_file)

        # Checking for header row or else DictReader cant make dictionaries
        if reader.fieldnames is None:
            raise ValueError(f"{path} is empty or is missing a header row.")

        return list(reader)


# Take in speakers csv file path and create SPEAKER profiles
def load_speakers (file_path: str | Path) -> dict[str, SpeakerProfile]:
    # Read the CSV rows first
    rows = read_csv_rows(file_path)
    speakers = {}

    # Make a SpeakerProfile for each row, transforming strings into adequate types
    for row in rows:
        speaker_id = row["speaker_id"]

        # Check that the ID follows the rule: S followed by three digits
        if re.fullmatch(r"S\d{3}", speaker_id) is None:
            raise InvalidIdentifierError(
                f"Invalid speaker ID on CSV row: {speaker_id!r}. "
                "Expected S followed by exactly three digits, for example S001."
            )

        profile = SpeakerProfile(
            speaker_id = speaker_id,
            usual_pitch = float(row["baseline_pitch"]),
            usual_energy = float(row["baseline_energy"]),
            usual_speech_rate = int(row["baseline_speech_rate"]),
            usual_pause_ratio = float(row["baseline_pause_ratio"]),
            name = row["name"],
        )
        speakers[speaker_id] = profile

    return speakers

# Take in recordings CSV file and group all the recordings with the same ID
def group_recording_rows(file_path: str | Path) -> dict[str, list[dict[str, str]]]:
    # Read the CSV rows first
    rows = read_csv_rows(file_path)
    recordings = {}

    # Put rows with the same recording ID together
    for row in rows:
        recording_id = row["recording_id"]

        # Check that the recording ID matches the right format (e.g., REC-2026-001)
        if re.fullmatch(r"REC-\d{4}-\d{3}", recording_id) is None:
            raise InvalidIdentifierError(
                f"Invalid recording ID: {recording_id!r}. "
                "Expected REC-YYYY-NNN, for example REC-2026-001."
            )
        if recording_id not in recordings:
             recordings[recording_id] = []

        recordings[recording_id].append(row)

    return recordings



