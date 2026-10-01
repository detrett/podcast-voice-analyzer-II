from utils import calculate_average, calculate_difference

# Arbitrary values with which to measure small differences from the speaker's usual style
PITCH_TOLERANCE = 10
ENERGY_TOLERANCE = 0.05
SPEECH_RATE_TOLERANCE = 10
PAUSE_RATIO_TOLERANCE = 0.05

class Analyzer:
    # The analyzer requires a full recording session
    def __init__(self, session):
        self.session = session

    # Simple function that returns the number of observations in a session
    def count_observations(self):
        return len(self.session.observations)

    # Calculates how much of a recording can be analyzed
    def usable_speech_count(self):
        count = 0

        for observation in self.session.observations:
            if observation.speech_present:
                count += 1

        return count
    
    ## AVERAGES

    # Function to calculate the average pitch
    def average_pitch(self):
        pitches = []

        # Only adding observations where speech was detected
        for observation in self.session.observations:
            if observation.speech_present:
                pitches.append(observation.pitch)

        # Return nothing if no pitches were detected
        if not pitches:
            return None

        # Return the average pitch otherwise
        return calculate_average(pitches)

    # Calculates the average energy, counting only observations with speech detected
    def average_energy(self):
        energies = []

        for observation in self.session.observations:
            if observation.speech_present:
                energies.append(observation.energy)

        if not energies:
            return None

        return calculate_average(energies)

    # Calculates the average speech rate, counting only observations with speech detected
    def average_speech_rate(self):
        speech_rates = []

        for observation in self.session.observations:
            if observation.speech_present:
                speech_rates.append(observation.speech_rate)

        if not speech_rates:
            return None

        return calculate_average(speech_rates)

    # Calculate average pause ratio, counting only observations where speech is detected
    def average_pause_ratio(self):
            pause_ratios = []
    
            for observation in self.session.observations:
                if observation.speech_present:
                    pause_ratios.append(observation.pause_ratio)
    
            if not pause_ratios:
                return None
    
            return calculate_average(pause_ratios)
    
    # Calculate average bg noise levels, counting only observations where speech is detected
    def average_background_noise(self):
        noise_levels = []

        for observation in self.session.observations:
            if observation.speech_present:
                noise_levels.append(observation.background_noise)

        if not noise_levels:
            return None

        return calculate_average(noise_levels)

    # Calculate average signal quality, counting only observations where speech is detected
    def average_signal_quality(self):
        signal_qualities = []

        for observation in self.session.observations:
            if observation.speech_present:
                signal_qualities.append(observation.signal_quality)

        if not signal_qualities:
            return None

        return calculate_average(signal_qualities)


    ## DIFERENCES

    # Tells us how much a recording differs from the average pitch
    def pitch_difference(self):
        average_pitch = self.average_pitch()

        if average_pitch is None:
            return None

        return calculate_difference(
            average_pitch,
            self.session.speaker_profile.usual_pitch
        )

    # Tells us how much a recording differs from their usual energy
    def energy_difference(self):
        average_energy = self.average_energy()

        if average_energy is None:
            return None

        return calculate_difference(
            average_energy,
            self.session.speaker_profile.usual_energy
        )

    # Tells us how much a recording differs from their usual speech rate
    # A positive value means faster than usual, a negative value means slower
    def speech_rate_difference(self):
        average_speech_rate = self.average_speech_rate()

        if average_speech_rate is None:
            return None

        return calculate_difference(
            average_speech_rate,
            self.session.speaker_profile.usual_speech_rate
        )


    # Tells us how much a recording differs from their usual pause ratio
    def pause_ratio_difference(self):
        average_pause_ratio = self.average_pause_ratio()

        if average_pause_ratio is None:
            return None

        return calculate_difference(
            average_pause_ratio,
            self.session.speaker_profile.usual_pause_ratio
        )


    ## CLASSIFICATION
    
    # General utility function for the class to calculate if a value is within the tolerance levels
    @staticmethod
    def is_within_tolerance(value, tolerance):
        if value is None:
            return False
        return abs(value) <= tolerance

    # Checks that a recording has at least half of its observation windows for reliable classification
    def has_sufficient_speech(self):
        total_windows = len(self.session.observations)
        if total_windows == 0:
            return False

        usable_windows = self.usable_speech_count()

        return usable_windows / total_windows >= 0.50

    def classify_delivery(self):
        # Not enough information if there is no usable speech
        if not self.has_sufficient_speech():
            return "insufficient data"

        # For scenarios with high background noise
        average_noise = self.average_background_noise()
        if average_noise > 0.70:
            return "noise affected"

        pitch_difference = self.pitch_difference()
        energy_difference = self.energy_difference()
        speech_rate_difference = self.speech_rate_difference()
        pause_ratio_difference = self.pause_ratio_difference()

        # A recording is considered energetic when the speaker's energy is noticeably higher than their usual level
        if energy_difference > ENERGY_TOLERANCE:
            return "energetic"

        # A recording is considered deliberate when the speaker talks slower and uses more pauses than usual
        if (speech_rate_difference < -SPEECH_RATE_TOLERANCE and pause_ratio_difference > PAUSE_RATIO_TOLERANCE):
            return "deliberate"  

        # A recording is consistent when the delivery matches the speaker's usual profile
        if (self.is_within_tolerance(pitch_difference, PITCH_TOLERANCE)
                and self.is_within_tolerance(energy_difference, ENERGY_TOLERANCE)
                and self.is_within_tolerance(speech_rate_difference, SPEECH_RATE_TOLERANCE)
                and self.is_within_tolerance(pause_ratio_difference, PAUSE_RATIO_TOLERANCE)):
            return "consistent"

        return "temporarily varied"


    ## QUALITY
    # Function to measure how trustworthy a recording is
    def evaluate_quality (self):
        usable_count = self.usable_speech_count()

        if not self.has_sufficient_speech():
            return {
                "label": "insufficient",
                "reason": "Too little usable speech was detected."
            }

        average_noise = self.average_background_noise()
        average_signal_quality = self.average_signal_quality()
        # Measuring noise levels and signal quality
        if average_noise > 0.70:
            return {
                "label": "poor",
                "reason": "Background noise is too high"
            }

        if average_signal_quality < 0.50:
            return {
                "label": "poor",
                "reason": "Signal quality is too low"
            }

        return {
            "label": "good",
            "reason": "The recording has usable speech, low background noise, and good signal quality"
        }

    # Main analysis, stores the results in one dictionary for reusability
    def analyze(self):
        result = {
            "speaker_id": self.session.speaker_profile.speaker_id,
            "usable_speech_windows": self.usable_speech_count(),
            "classification": self.classify_delivery(),
            "quality": self.evaluate_quality(),
            "average_pitch": self.average_pitch(),
            "average_energy": self.average_energy(),
            "average_speech_rate": self.average_speech_rate(),
            "average_pause_ratio": self.average_pause_ratio(),
            "average_background_noise": self.average_background_noise(),
            "average_signal_quality": self.average_signal_quality(),
            "pitch_difference": self.pitch_difference(),
            "energy_difference": self.energy_difference(),
            "speech_rate_difference": self.speech_rate_difference(),
            "pause_ratio_difference": self.pause_ratio_difference()
        }

        return result