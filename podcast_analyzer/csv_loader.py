# This module reads CSV files into a list of dictionaries

import csv
from pathlib import Path
from speaker import SpeakerProfile

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


# Take in a csv file path and create speaker profiles
def load_speakers (file_path: str | Path) -> dict[str, SpeakerProfile]:
    # Read the CSV rows first
    rows = read_csv_rows(file_path)
    speakers = {}

    # Make a SpeakerProfile for each row, transforming strings into adequate types
    for row in rows:
        speaker_id = row["speaker_id"]
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