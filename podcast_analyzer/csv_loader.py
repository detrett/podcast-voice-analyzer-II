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
    # Rows with an invalid recording ID are already recorded as rejected here
    grouped_rows = group_recording_rows(file_path, rejected_records)
    sessions = {}

    # Each group of rows sharing ID becomes one recording session
    for recording_id, rows in grouped_rows.items():
        speaker_id = None
        observations = []

        for row in rows:
            field = "speaker_id"

            # Try to catch and record any errors row by row so that the program can continue if there is one
            try:
                row_speaker_id = row.get("speaker_id")
                if row_speaker_id not in speakers:
                    raise InvalidRecordError(
                        f"Unknown speaker ID: {row_speaker_id!r}."
                    )

                if speaker_id is None:
                    speaker_id = row_speaker_id
                elif  row_speaker_id != speaker_id:
                    raise InvalidRecordError(
                        f"Recording {recording_id} contains multiple speakers."
                    )

                field = "speech_present"
                speech_text = (row.get("speech_present") or "").strip().lower()

                # The CSV must say true or false for this column
                if speech_text not in ("true", "false"):
                    raise InvalidRecordError(
                        f"Invalid speech_present value: {speech_text!r}. "
                        "Expected value of True or False."
                    )

                speech_present = speech_text == "true"

                # Some speech measurements can be blank when there is no speech
                field = "pitch"
                pitch_text = (row.get("pitch") or "").strip()
                pitch = float(pitch_text) if pitch_text else None

                field = "energy"
                energy_text = (row.get("energy") or "").strip()
                energy = float(energy_text) if energy_text else None

                field = "speech_rate"
                rate_text = (row.get("speech_rate") or "").strip()
                speech_rate = int(rate_text) if rate_text else None

                field = "pause_ratio"
                pause_text = (row.get("pause_ratio") or "").strip()
                pause_ratio = float(pause_text) if pause_text else None

                field = "timestamp"
                timestamp = int(row.get("timestamp"))

                field = "background_noise"
                background_noise = float(row.get("background_noise"))

                field = "signal_quality"
                signal_quality = float(row.get("signal_quality"))

                # Observation checks that the values are in acceptable ranges
                field = "observation"
                observation = Observation(
                    timestamp=timestamp,
                    speech_present=speech_present,
                    pitch=pitch,
                    energy=energy,
                    speech_rate=speech_rate,
                    pause_ratio=pause_ratio,
                    background_noise=background_noise,
                    signal_quality=signal_quality,
                )

                observations.append(observation)

            except (InvalidRecordError, ValueError, TypeError, KeyError, AttributeError) as error:
                # Save the problem details, then move on to the next row
                rejected_records.append({
                    "source_file": Path(file_path).name,
                    "row_number": row.get("__row_number__", "unknown"),
                    "field": field,
                    "reason": str(error),
                })

        # Only make a session if at least one row for it was valid
        if speaker_id is not None and observations:
            sessions[recording_id] = RecordingSession(
                speakers[speaker_id],
                observations,
            )

    return sessions
