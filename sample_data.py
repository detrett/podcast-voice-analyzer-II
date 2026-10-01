from data_generator import generate_recording_data
from podcast_analyzer.models.speaker import SpeakerProfile
from podcast_analyzer.models.observation import Observation
from podcast_analyzer.models.recording_session import RecordingSession

# This function converts the generator's data (dictionaries/lists) into the classes used by the rest of the application
def create_recording_session(scenario, seed=42, number_of_windows=12):
    profile_data, observation_data = generate_recording_data(
            scenario=scenario,
            seed=seed,
            number_of_windows=number_of_windows
        )
    
    speaker_profile = SpeakerProfile(
        profile_data["speaker_id"],
        profile_data["usual_pitch"],
        profile_data["usual_energy"],
        profile_data["usual_speech_rate"],
        profile_data["usual_pause_ratio"]
    )

    observations = []

    for data in observation_data:
        try:
            observation = Observation(
                data["timestamp"],
                data["speech_present"],
                data["pitch"],
                data["energy"],
                data["speech_rate"],
                data["pause_ratio"],
                data["background_noise"],
                data["signal_quality"]
            )

            observations.append(observation)
        # Invalid observation data is excluded from the recording without stopping the analysis
        except ValueError:
            continue

    return RecordingSession(speaker_profile, observations)