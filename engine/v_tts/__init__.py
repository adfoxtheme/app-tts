"""
V-TTS - Text to Speech for Vietnamese

Simple usage:
    from v_tts import TTS
    
    tts = TTS()
    tts.speak("Xin chào các bạn", output_path="output.wav")
"""

__version__ = "1.0.0"
__author__ = "V-TTS"

from .tts import TTS
from .zeroshot import ZeroShotTTS

__all__ = ["TTS", "ZeroShotTTS", "__version__"]
