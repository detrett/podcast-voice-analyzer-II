import csv
from pathlib import Path
from utils import format_metric

# To set the CSV headings
SUMMARY_FIELDS = [
    "recording_id",
    "speaker_id",
    "usable_speech_windows",
    "classification",
    "quality",
    "quality_reason",
    "average_pitch",
    "average_energy",
    "average_speech_rate",
    "average_pause_ratio",
    "average_background_noise",
    "average_signal_quality",
    "pitch_difference",
    "energy_difference",
    "speech_rate_difference",
    "pause_ratio_difference",
]


# Creates the analysis_summary.csv file
def write_analysis_summary(
    results: dict[str, dict],
    output_directory: str | Path,
) -> Path:

    # Create an output directory if it does not exist yet
    output_dir = Path(output_directory)
    output_dir.mkdir(parents=True, exist_ok=True)

    summary_path = output_dir / "analysis_summary.csv"

    # One summary row per recording
    with open(summary_path, "w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=SUMMARY_FIELDS)
        writer.writeheader()

        for recording_id, result in results.items():
            writer.writerow({
                "recording_id": recording_id,
                "speaker_id": result["speaker_id"],
                "usable_speech_windows": result["usable_speech_windows"],
                "classification": result["classification"],
                "quality": result["quality"]["label"],
                "quality_reason": result["quality"]["reason"],
                "average_pitch": result["average_pitch"],
                "average_energy": result["average_energy"],
                "average_speech_rate": result["average_speech_rate"],
                "average_pause_ratio": result["average_pause_ratio"],
                "average_background_noise": result["average_background_noise"],
                "average_signal_quality": result["average_signal_quality"],
                "pitch_difference": result["pitch_difference"],
                "energy_difference": result["energy_difference"],
                "speech_rate_difference": result["speech_rate_difference"],
                "pause_ratio_difference": result["pause_ratio_difference"],
            })

        return summary_path


# Creates the analysis_report.txt file
def write_analysis_report(
        results: dict[str, dict],
        output_directory: str | Path,
) -> Path:

    output_dir = Path(output_directory)
    output_dir.mkdir(parents=True, exist_ok=True)

    report_path = output_dir / "analysis_report.txt"

    # Write a readable explanation for each recording
    with open(report_path, "w", encoding="utf-8") as report_file:
        for recording_id, result in results.items():
            quality = result["quality"]

            report_file.write(f"Recording: {recording_id}\n")
            report_file.write("-" * 50 + "\n")
            report_file.write(f"Speaker: {result['speaker_id']}\n")
            report_file.write(
                f"Usable speech windows: {result['usable_speech_windows']}\n"
            )
            report_file.write(
                f"Delivery classification: {result['classification']}\n"
            )
            report_file.write(f"Recording quality: {quality['label']}\n")
            report_file.write(f"Quality explanation: {quality['reason']}\n")

            report_file.write("\nAcoustic measurements\n")
            report_file.write(
                f"Average pitch: {format_metric(result['average_pitch'])}\n"
            )
            report_file.write(
                f"Average energy: {format_metric(result['average_energy'])}\n"
            )
            report_file.write(
                "Average speech rate: "
                f"{format_metric(result['average_speech_rate'])}\n"
            )
            report_file.write(
                "Average pause ratio: "
                f"{format_metric(result['average_pause_ratio'])}\n"
            )
            report_file.write(
                "Average background noise: "
                f"{format_metric(result['average_background_noise'])}\n"
            )
            report_file.write(
                "Average signal quality: "
                f"{format_metric(result['average_signal_quality'])}\n"
            )

            report_file.write("\n\n")

    return report_path