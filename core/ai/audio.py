import numpy as np

def detect_audio_cheating(audio_level):
    """
    audio_level: float (0–1)
    """
    if audio_level > 0.6:
        return True
    return False
