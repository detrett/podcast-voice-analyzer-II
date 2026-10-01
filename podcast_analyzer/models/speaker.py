class SpeakerProfile:
    # This class stores the values that are considered normal for the speaker
    def __init__(self, speaker_id, usual_pitch, usual_energy,
                 usual_speech_rate, usual_pause_ratio, name=None):
        self.speaker_id = speaker_id
        self.usual_pitch = usual_pitch
        self.usual_energy = usual_energy
        self.usual_speech_rate = usual_speech_rate
        self.usual_pause_ratio = usual_pause_ratio
        self.name = name