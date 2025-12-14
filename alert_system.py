"""
Alert system handling safety notifications, sound cue generation, and logging.
"""

from __future__ import annotations

import datetime as dt
import io
import wave
from typing import Dict, Tuple

import numpy as np

from data_logger import DataLogger


class AlertSystem:
    def __init__(self, data_logger: DataLogger):
        self.data_logger = data_logger
        self._audio_cache = None

    def _generate_beep(self, seconds: float = 0.35, freq: float = 880.0) -> bytes:
        """Generate a short beep sound."""
        if self._audio_cache:
            return self._audio_cache
        rate = 44100
        t = np.linspace(0, seconds, int(rate * seconds), False)
        tone = 0.5 * np.sin(freq * 2 * np.pi * t)
        audio = (tone * 32767).astype(np.int16)
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(rate)
            wav_file.writeframes(audio.tobytes())
        self._audio_cache = buf.getvalue()
        return self._audio_cache

    def should_alert(self, overall_status: str) -> bool:
        return overall_status in {"warning", "emergency"}

    def handle_alert(self, reading: Dict, evaluation_reason: str) -> Tuple[str, bytes]:
        """Persist alert and return message + audio bytes for UI playback."""
        reading_with_overall = dict(reading)
        reading_with_overall["overall"] = evaluation_reason
        self.data_logger.log_alert(reading_with_overall, evaluation_reason)
        timestamp_str = dt.datetime.fromtimestamp(reading["timestamp"]).strftime("%H:%M:%S")
        message = f"{timestamp_str} | Worker {reading['worker_id']} | {evaluation_reason}"
        return message, self._generate_beep()


