# This module reads CSV files into a list of dictionaries

import csv
import re

from pathlib import Path
from speaker import SpeakerProfile
from observation import Observation
from recording_session import RecordingSession
from .exceptions import InvalidIdentifierError, InvalidRecordError


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

        rows = []
        # Keep the original CSV row number so errors can point to it
        for row_number, row in enumerate(reader, start=2):
            row["__row_number__"] = str(row_number)
            rows.append(row)

        return rows


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
def group_recording_rows(
        file_path: str | Path,
        rejected_records: list[dict] | None = None,
) -> dict[str, list[dict[str, str]]]:

    if rejected_records is None:
        rejected_records = []

    # Read the CSV rows first
    rows = read_csv_rows(file_path)
    recordings = {}

    # Put rows with the same recording ID together
    for row in rows:
        recording_id = row.get("recording_id")

        # Raise InvalidIdentifierError when the ID is wrong
        # Use Except to catch the error and record the info before moving onto the next row
        try:
            if re.fullmatch(r"REC-\d{4}-\d{3}", recording_id or "") is None:
                raise InvalidIdentifierError(
                    f"Invalid recording ID: {recording_id!r}. "
                    "Expected REC-YYYY-NNN, for example REC-2026-001."
                )
        except InvalidIdentifierError as error:
            rejected_records.append({
                "source_file": Path(file_path).name,
                "row_number": row["__row_number__"],
                "field": "recording_id",
                "reason": str(error),
            })
            continue

        if recording_id not in recordings:
             recordings[recording_id] = []

        recordings[recording_id].append(row)

    return recordings

# Take CSV data, organize it by recording, and turn each row into an Observation object. Return a RecordingSession dict
def load_recording_sessions(
        file_path: str | Path,
        speakers: dict[str, SpeakerProfile],
        rejected_records: list[dict] | None = None,
) -> dict[str, RecordingSession]:

    if rejected_records is None:
        rejected_records = []

    # First group the CSV rows by recording ID
    grouped_rows = group_recording_rows(file_path, rejected_records)
    sessions = {}

    # Each group becomes one recording session
    for recording_id, rows in grouped_rows.items():
        # Finding the speaker of the group
        speaker_id = rows[0]["speaker_id"]

        # Missing speaker error
        if speaker_id not in speakers:
            raise InvalidRecordError(
                f"Recording {recording_id} refers to unknown speaker {speaker_id!r}."
            )

        observations = []

        # Turn each CSV row into an Observation object
        for row in rows:
            # Multiple speakers error
            if row["speaker_id"] != speaker_id:
                raise InvalidRecordError(
                    f"Recording {recording_id} contains more than one speaker. "
                )

            speech_text = row["speech_present"].strip().lower()
            # speech present must be True or False
            if speech_text not in ("true", "false"):
                raise InvalidRecordError(
                    f"Invalid speech_present value: {row['speech_present']!r}. "
                    "Expected value of True or False."
                )

            # Convert to boolean
            speech_present = speech_text == "true"

            # Converting values
            # Empty values are accepted here since sometimes there is no speech
            pitch_text = row["pitch"].strip()
            pitch = float(pitch_text) if pitch_text else None

            energy_text = row["energy"].strip()
            energy = float(energy_text) if energy_text else None

            rate_text = row["speech_rate"].strip()
            speech_rate = int(rate_text) if rate_text else None

            pause_text = row["pause_ratio"].strip()
            pause_ratio = float(pause_text) if pause_text else None

            observation = Observation(
                timestamp = int(row["timestamp"]),
                speech_present = speech_present,
                pitch = pitch,
                energy = energy,
                speech_rate = speech_rate,
                pause_ratio = pause_ratio,
                background_noise = float(row["background_noise"]),
                signal_quality = float(row["signal_quality"]),
            )

            observations.append(observation)
        
        sessions[recording_id] = RecordingSession(
            speakers[speaker_id],
            observations,
        )

    return sessions
