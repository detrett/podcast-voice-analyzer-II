import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from analyzer import Analyzer
from observation import Observation
from podcast_analyzer.csv_loader import load_recording_sessions, load_speakers, read_csv_rows
from sample_data import create_recording_session


class TestObservation(unittest.TestCase):
    # This test checks that an impossible energy value is rejected
    def test_invalid_energy_is_rejected(self):
        with self.assertRaises(ValueError):
            Observation(
                timestamp=0,
                speech_present=True,
                pitch=170,
                energy=1.5,
                speech_rate=110,
                pause_ratio=0.2,
                background_noise=0.1,
                signal_quality=0.9
            )
    # An observation without speech cant have meaningful speech measurements, so those values are allowed to be None
    def test_missing_speech_values_are_allowed_without_speech(self):
        observation = Observation(
            timestamp=0,
            speech_present=False,
            pitch=None,
            energy=None,
            speech_rate=None,
            pause_ratio=None,
            background_noise=0.3,
            signal_quality=0.4
        )

        self.assertFalse(observation.speech_present)


class TestAnalyzer(unittest.TestCase):
    # The generated consistent scenario should stay close enough to the speaker's usual profile to be classified as consistent
    def test_consistent_scenario(self):
        session = create_recording_session("consistent", seed=42)
        analyzer = Analyzer(session)

        self.assertEqual(
            analyzer.classify_delivery(),
            "consistent"
        )
    # The energetic scenario increases the speaker's energy and speech rate, so it should be detected as energetic
    def test_energetic_scenario(self):
        session = create_recording_session("energetic", seed=42)
        analyzer = Analyzer(session)

        self.assertEqual(
            analyzer.classify_delivery(),
            "energetic"
        )
    # The deliberate scenario has a lower speech rate and higher pause ratio than the speaker's usual profile
    def test_deliberate_scenario(self):
        session = create_recording_session("deliberate", seed=42)
        analyzer = Analyzer(session)

        self.assertEqual(
            analyzer.classify_delivery(),
            "deliberate"
        )
    # High background noise should be identified separately
    def test_noise_scenario(self):
        session = create_recording_session("noise_affected", seed=42)
        analyzer = Analyzer(session)

        self.assertEqual(
            analyzer.classify_delivery(),
            "noise affected"
        )
    # Most of the windows in this scenario do not contain speech so the analyzer should classify it accordingly
    def test_insufficient_data_scenario(self):
        session = create_recording_session("insufficient_data", seed=42)
        analyzer = Analyzer(session)

        self.assertEqual(
            analyzer.classify_delivery(),
            "insufficient data"
        )
    # The analysis must return a structured dictionary to be used by other parts of the application
    def test_analysis_returns_dictionary(self):
        session = create_recording_session("consistent", seed=42)
        analyzer = Analyzer(session)

        result = analyzer.analyze()

        self.assertIsInstance(result, dict)
        self.assertIn("classification", result)
        self.assertIn("quality", result)
    # Values within the tolerance should return True, while values outside the tolerance should return False.
    def test_static_tolerance_method(self):
        self.assertTrue(
            Analyzer.is_within_tolerance(8, 10)
        )

        self.assertFalse(
            Analyzer.is_within_tolerance(15, 10)
        )


class TestCsvLoader(unittest.TestCase):
    def setUp(self):
        # Temporary folder for CSV files at the start of each test
        self.temp_dir = TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.folder = Path(self.temp_dir.name)

        # All the tests will use this speaker
        self.speakers_path = self.folder / "speakers.csv"
        self.speakers_path.write_text(
            "speaker_id,name,baseline_pitch,baseline_energy,"
            "baseline_speech_rate,baseline_pause_ratio\n"
            "S001,Test Speaker,150,0.4,120,0.2\n",
            encoding="utf-8",
        )
        self.speakers = load_speakers(self.speakers_path)

    def write_sessions_file(self, csv_text):
        sessions_path = self.folder / "recording_sessions.csv"
        sessions_path.write_text(csv_text, encoding="utf-8")
        return sessions_path

    def test_valid_csv_loads_a_session(self):
        sessions_path = self.write_sessions_file(
            "recording_id,speaker_id,timestamp,speech_present,pitch,energy,"
            "speech_rate,pause_ratio,background_noise,signal_quality\n"
            "REC-2026-001,S001,0,true,150,0.4,120,0.2,0.1,0.9\n"
        )
        rejected_records = []

        sessions = load_recording_sessions(sessions_path, self.speakers, rejected_records)

        self.assertIn("REC-2026-001", sessions)
        self.assertEqual(len(sessions["REC-2026-001"].observations), 1)
        self.assertEqual(rejected_records, [])

    # Testing that a bad row does not stop the program, but is instead recorded separately
    def test_bad_row_is_rejected_but_valid_rows_are_kept(self):
        sessions_path = self.write_sessions_file(
            "recording_id,speaker_id,timestamp,speech_present,pitch,energy,"
            "speech_rate,pause_ratio,background_noise,signal_quality\n"
            "REC-2026-001,S001,0,true,150,0.4,120,0.2,0.1,0.9\n"
            "REC-2026-001,S001,1,true,high,0.4,120,0.2,0.1,0.9\n"
            "REC-2026-001,S001,2,true,151,0.4,120,0.2,0.1,0.9\n"
        )
        rejected_records = []

        sessions = load_recording_sessions(sessions_path, self.speakers, rejected_records)

        # The first and third rows are valid but the second is not
        self.assertEqual(len(sessions["REC-2026-001"].observations), 2)
        self.assertEqual(len(rejected_records), 1)
        self.assertEqual(rejected_records[0]["row_number"], "3")
        self.assertEqual(rejected_records[0]["field"], "pitch")

    # Testing for boundary cases
    def test_values_at_limits_are_accepted(self):
        sessions_path = self.write_sessions_file(
            "recording_id,speaker_id,timestamp,speech_present,pitch,energy,"
            "speech_rate,pause_ratio,background_noise,signal_quality\n"
            "REC-2026-001,S001,0,true,0,0,0,0,0,1\n"
        )
        rejected_records = []

        sessions = load_recording_sessions(sessions_path, self.speakers, rejected_records)

        self.assertEqual(len(sessions["REC-2026-001"].observations), 1)
        self.assertEqual(rejected_records, [])

    # Testing for cases where a value is missing
    def test_missing_value_is_rejected(self):
        sessions_path = self.write_sessions_file(
            "recording_id,speaker_id,timestamp,speech_present,pitch,energy,"
            "speech_rate,pause_ratio,background_noise,signal_quality\n"
            "REC-2026-001,S001,0,true,150,0.4,120,0.2,0.1,\n"
        )
        rejected_records = []

        sessions = load_recording_sessions(sessions_path, self.speakers, rejected_records)

        self.assertNotIn("REC-2026-001", sessions)
        self.assertEqual(len(rejected_records), 1)
        self.assertEqual(rejected_records[0]["field"], "signal_quality")

    # Testing for missing file cases
    def test_missing_file_raises_error(self):
        missing_path = self.folder / "missing.csv"

        with self.assertRaises(FileNotFoundError):
            read_csv_rows(missing_path)

if __name__ == "__main__":
    unittest.main()