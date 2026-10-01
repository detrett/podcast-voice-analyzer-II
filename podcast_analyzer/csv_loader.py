# This module reads CSV files into a list of dictionaries

import csv
import re

from pathlib import Path
from podcast_analyzer.models.speaker import SpeakerProfile
from podcast_analyzer.models.observation import Observation
from podcast_analyzer.models.recording_session import RecordingSession
from .exceptions import InvalidIdentifierError, InvalidRecordError

SESSION_REQUIRED_FIELDS = (
    "recording_id",
    "speaker_id",
    "timestamp",
    "speech_present",
    "pitch",
    "energy",
    "speech_rate",
    "pause_ratio",
    "background_noise",
    "signal_quality",
)

SPEAKER_REQUIRED_FIELDS = (
    "speaker_id",
    "name",
    "baseline_pitch",
    "baseline_energy",
    "baseline_speech_rate",
    "baseline_pause_ratio",
)

# Take in a csv file path and return the rows
def read_csv_rows(
        file_path: str | Path,
        required_fields: tuple[str, ...] |None = None,
) -> list[dict[str, str]]:

    # Make sure the path is a Path object
    path = Path(file_path)

    # Open the file and read it with csv's DictReader
    with open(path, "r", encoding="utf-8", newline='') as csv_file:
        reader = csv.DictReader(csv_file)

        # Checking for header row or else DictReader cant make dictionaries
        if reader.fieldnames is None:
            raise ValueError(f"{path} is empty or is missing a header row.")

        # Check that the header includes all the required columns
        if required_fields is not None:
            missing_headers = [
                field for field in required_fields if field not in reader.fieldnames
            ]

            if missing_headers:
                missing_text = ", ".join(missing_headers)
                raise ValueError(f"{path} is missing the required column(s): {missing_text}.")

        rows = []
        # Keep the original CSV row number so errors can point to it
        for row_number, row in enumerate(reader, start=2):
            row["__row_number__"] = str(row_number)

            # DictReader uses None as the key when a row has extra values
            if None in row:
                row["__structure_field__"] = "row"
                row["__structure_error__"] = (
                    "This row has more values than the header has columns."
                )

            elif required_fields is not None:
                missing_values = [
                    field for field in required_fields if row.get(field) is None
                ]

                if missing_values:
                    missing_field = missing_values[0]
                    row["__structure_field__"] = missing_field
                    row["__structure_error__"] = (
                        f"This row is missing a value for {missing_field}."
                    )

            rows.append(row)

        return rows


# Take in speakers csv file path and create SPEAKER profiles
def load_speakers (
        file_path: str | Path,
        rejected_records: list[dict] | None = None,
) -> dict[str, SpeakerProfile]:

    if rejected_records is None:
        rejected_records = []

    # Check that the speaker CSV has the columns the loader needs
    rows = read_csv_rows(file_path, SPEAKER_REQUIRED_FIELDS)
    speakers = {}

    # Try each speaker row separately so one bad row does not stop the others
    for row in rows:
        field = "speaker_id"

        try:
            # Reject rows that have too few or too many values
            if "__structure_error__" in row:
                field = row["__structure_field__"]
                raise InvalidRecordError(row["__structure_error__"])

            speaker_id = row.get("speaker_id") or ""

            # Speaker IDs must be S followed by three digits
            if re.fullmatch(r"S\d{3}", speaker_id) is None:
                raise InvalidIdentifierError(
                    f"Invalid speaker ID: {speaker_id!r}. "
                    "Expected S followed by exactly three digits, for example S001."
                )

            field = "name"
            name = (row.get("name") or "").strip()

            if not name:
                raise InvalidRecordError("Speaker name is required.")

            # Convert the baseline values from text into numbers. Validate afterwards
            field = "baseline_pitch"
            usual_pitch = float(row.get("baseline_pitch") or "")

            if usual_pitch < 0:
                raise InvalidRecordError("Baseline pitch cannot be negative.")

            field = "baseline_energy"
            usual_energy = float(row.get("baseline_energy") or "")

            if usual_energy < 0 or usual_energy > 1:
                raise InvalidRecordError(
                    "Baseline energy must be between 0 and 1."
                )

            field = "baseline_speech_rate"
            usual_speech_rate = int(row.get("baseline_speech_rate") or "")

            if usual_speech_rate < 0:
                raise InvalidRecordError(
                    "Baseline speech rate cannot be negative."
                )

            field = "baseline_pause_ratio"
            usual_pause_ratio = float(row.get("baseline_pause_ratio") or "")

            if usual_pause_ratio < 0 or usual_pause_ratio > 1:
                raise InvalidRecordError(
                    "Baseline pause ratio must be between 0 and 1."
                )

            profile = SpeakerProfile(
            speaker_id=speaker_id,
            usual_pitch=usual_pitch,
            usual_energy=usual_energy,
            usual_speech_rate=usual_speech_rate,
            usual_pause_ratio=usual_pause_ratio,
            name=name,
            )
            speakers[speaker_id] = profile

        except (ValueError, TypeError, KeyError, AttributeError) as error:
            # Record the problem and then try the next speaker row
            rejected_records.append({
                "source_file": Path(file_path).name,
                "row_number": row.get("__row_number__", "unknown"),
                "field": field,
                "reason": str(error),
            })

    return speakers

# Take in recordings CSV file and group all the recordings with the same ID
def group_recording_rows(
        file_path: str | Path,
        rejected_records: list[dict] | None = None,
) -> dict[str, list[dict[str, str]]]:

    if rejected_records is None:
        rejected_records = []

    # Read the CSV rows first
    rows = read_csv_rows(file_path, SESSION_REQUIRED_FIELDS)
    recordings = {}

    # Put rows with the same recording ID together
    for row in rows:

        # Record rows with the wrong number of values and skip them
        if "__structure_error__" in row:
            rejected_records.append({
                "source_file": Path(file_path).name,
                "row_number": row["__row_number__"],
                "field": row["__structure_field__"],
                "reason": row["__structure_error__"],
            })
            continue

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

                if timestamp < 0:
                    raise InvalidRecordError("Timestamp cannot be negative.")

                field = "background_noise"
                background_noise = float(row.get("background_noise"))

                field = "signal_quality"
                signal_quality = float(row.get("signal_quality"))

                # Check missing speech values here so the report can name the column
                if speech_present and pitch is None:
                    field = "pitch"
                    raise InvalidRecordError("Pitch is required when speech is present.")

                if speech_present and energy is None:
                    field = "energy"
                    raise InvalidRecordError("Energy is required when speech is present.")

                if speech_present and speech_rate is None:
                    field = "speech_rate"
                    raise InvalidRecordError("Speech rate is required when speech is present.")

                if speech_present and pause_ratio is None:
                    field = "pause_ratio"
                    raise InvalidRecordError("Pause ratio is required when speech is present.")

                # Check the value ranges so the rejected file names the right column
                field = "pitch"
                if pitch is not None and pitch < 0:
                    raise InvalidRecordError("Pitch cannot be negative.")

                field = "energy"
                if energy is not None and (energy < 0 or energy > 1):
                    raise InvalidRecordError("Energy must be between 0 and 1.")

                field = "speech_rate"
                if speech_rate is not None and speech_rate < 0:
                    raise InvalidRecordError("Speech rate cannot be negative.")

                field = "pause_ratio"
                if pause_ratio is not None and (pause_ratio < 0 or pause_ratio > 1):
                    raise InvalidRecordError("Pause ratio must be between 0 and 1.")

                field = "background_noise"
                if background_noise < 0 or background_noise > 1:
                    raise InvalidRecordError("Background noise must be between 0 and 1.")

                field = "signal_quality"
                if signal_quality < 0 or signal_quality > 1:
                    raise InvalidRecordError("Signal quality must be between 0 and 1.")


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
