import argparse
from pathlib import Path

from podcast_analyzer.analyzer import Analyzer
from data_generator import available_scenarios
from podcast_analyzer.csv_loader import load_recording_sessions, load_speakers
from podcast_analyzer.output_writer import write_analysis_summary, write_analysis_report, write_rejected_records
from report import print_report
from sample_data import create_recording_session

# Run the assignment 1 scenario
def run_scenario(scenario):
    session = create_recording_session(
        scenario,
        seed=42
    )

    analyzer = Analyzer(session)
    result = analyzer.analyze()

    print("\nScenario:", scenario)
    print_report(result)

def run_csv_files(
        profiles_path: Path,
        sessions_path: Path,
        output_directory: Path,
):

    # Keeping track of rejected rows from both CSV files
    rejected_records = []

    # Load speaker profiles first so each recording can find its speaker
    speakers = load_speakers(profiles_path, rejected_records)
    sessions = load_recording_sessions(sessions_path, speakers, rejected_records)
    results = {}

    # Analyze the recordings
    for recording_id, session in sessions.items():
        analyzer = Analyzer(session)
        results[recording_id] = analyzer.analyze()

    # Save the analysis results and rejected rows
    summary_path = write_analysis_summary(results, output_directory)
    report_path = write_analysis_report(results, output_directory)
    rejected_path = write_rejected_records(rejected_records, output_directory)

    # Count the valid recording rows that became observations
    accepted_recording_rows = sum(
        len(session.observations)
        for session in sessions.values()
    )

    # Display a summary when the run is finished
    print("\n---Analysis complete---")
    print(f"Accepted speaker profiles: {len(speakers)}")
    print(f"Accepted recording rows: {accepted_recording_rows}")
    print(f"Rejected rows: {len(rejected_records)}")
    print("\n---Created files---")
    print(f"Summary: {summary_path}")
    print(f"Readable report: {report_path}")
    print(f"Rejected records: {rejected_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Analyze podcast voice and recording data."
    )
    parser.add_argument("--profiles", type=Path, help="Path to the speakers CSV file")
    parser.add_argument("--sessions", type=Path, help="Path to the recording sessions CSV file")
    parser.add_argument("--output", type=Path, default=Path("output"), help="Folder for reports "
                                                                            "(default: output)",
    )
    args = parser.parse_args()

    print("Podcast Voice and Recording Analyzer")

    # CSV mode needs both files
    if args.profiles is not None or args.sessions is not None:
        if args.profiles is None or args.sessions is None:
            parser.error("Please provide both --profiles and --sessions.")

        run_csv_files(args.profiles, args.sessions, args.output)
        return

    # Run the original generated scenarios if no CSV arguments are provided
    scenarios = available_scenarios()

    for scenario in scenarios:
        run_scenario(scenario)


if __name__ == "__main__":
    main()