#!/usr/bin/env python3
"""
TTS Engine Wrapper for V-TTS
Handles model loading, inference, sentence chunking, and zero-shot voice cloning.
"""

import os
import sys
import re
import time
import tempfile
from pathlib import Path
from typing import Callable, Optional, Tuple, List
import numpy as np
import soundfile as sf

# Add engine directory to sys.path
ENGINE_DIR = Path(__file__).parent.parent / "engine"
if str(ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(ENGINE_DIR))


class TTSEngine:
    def __init__(self):
        self.tts = None
        self.zeroshot_tts = None
        self.device = "cpu"
        self._is_loading = False
        self._is_ready = False
        self.cancel_requested = False

        # Human-readable speaker names
        self.speaker_meta = {
            "NF": {
                "name": "Nữ miền Bắc (Hà Nội)",
                "desc": "Thanh lịch, chuẩn ngữ điệu thủ đô",
                "gender": "female",
                "region": "Bắc"
            },
            "SF": {
                "name": "Nữ miền Nam (Sài Gòn)",
                "desc": "Ngọt ngào, truyền cảm và tự nhiên",
                "gender": "female",
                "region": "Nam"
            },
            "NM1": {
                "name": "Nam miền Bắc 1 (Hà Nội)",
                "desc": "Trầm ấm, chững chạc và trang trọng",
                "gender": "male",
                "region": "Bắc"
            },
            "NM2": {
                "name": "Nam miền Bắc 2 (Hà Nội)",
                "desc": "Trẻ trung, tươi sáng và năng động",
                "gender": "male",
                "region": "Bắc"
            },
            "SM": {
                "name": "Nam miền Nam (Sài Gòn)",
                "desc": "Rõ ràng, phóng khoáng và hiện đại",
                "gender": "male",
                "region": "Nam"
            }
        }

    def load_models(self, on_progress: Optional[Callable[[str], None]] = None) -> bool:
        """Load the primary TTS model in background."""
        self._is_loading = True
        try:
            if on_progress:
                on_progress("Đang khởi động bộ máy đọc V-TTS...")
            
            from v_tts import TTS
            self.tts = TTS(device=self.device)
            self._is_ready = True
            
            if on_progress:
                on_progress("Hệ thống đã sẵn sàng!")
            return True
        except Exception as e:
            print(f"[TTSEngine] Error loading TTS model: {e}")
            if on_progress:
                on_progress(f"Lỗi khởi tạo: {e}")
            return False
        finally:
            self._is_loading = False

    def load_zeroshot_model(self, on_progress: Optional[Callable[[str], None]] = None) -> bool:
        """Load the zero-shot voice cloning model on demand."""
        if self.zeroshot_tts is not None:
            return True
        try:
            if on_progress:
                on_progress("Đang tải mô hình nhân bản giọng nói...")
            from v_tts import ZeroShotTTS
            self.zeroshot_tts = ZeroShotTTS(device=self.device)
            if on_progress:
                on_progress("Mô hình nhân bản giọng nói đã sẵn sàng!")
            return True
        except Exception as e:
            print(f"[TTSEngine] Error loading ZeroShot model: {e}")
            if on_progress:
                on_progress(f"Lỗi tải mô hình nhân bản: {e}")
            return False

    def get_speakers(self) -> List[dict]:
        """Return list of speakers with metadata."""
        if not self.tts:
            keys = ["NF", "SF", "NM1", "NM2", "SM"]
        else:
            keys = self.tts.list_speakers()
        
        result = []
        for k in keys:
            info = self.speaker_meta.get(k, {
                "name": f"Giọng đọc {k}",
                "desc": "",
                "gender": "other",
                "region": ""
            })
            result.append({
                "id": k,
                "name": info["name"],
                "desc": info["desc"]
            })
        return result

    @staticmethod
    def split_sentences(text: str) -> List[str]:
        """Split text cleanly into sentences for optimal prosody and chunking."""
        raw_paragraphs = [p.strip() for p in text.splitlines() if p.strip()]
        sentences = []
        
        for para in raw_paragraphs:
            # Match sentence endings: . ? ! ; followed by space or end of string
            parts = re.split(r'([.?!;]+(?:\s+|$))', para)
            current = ""
            for i in range(0, len(parts) - 1, 2):
                sent = (parts[i] + parts[i + 1]).strip()
                if sent:
                    sentences.append(sent)
            # Trailing remainder
            if len(parts) % 2 == 1 and parts[-1].strip():
                sentences.append(parts[-1].strip())
        
        # If no punctuation was found, split by commas or words if excessively long (> 150 chars)
        refined = []
        for s in (sentences or [text]):
            if len(s) > 200:
                # Split by commas or semicolons
                sub_parts = re.split(r'([,;]\s+)', s)
                sub_buf = ""
                for part in sub_parts:
                    if len(sub_buf) + len(part) < 180:
                        sub_buf += part
                    else:
                        if sub_buf.strip():
                            refined.append(sub_buf.strip())
                        sub_buf = part
                if sub_buf.strip():
                    refined.append(sub_buf.strip())
            else:
                refined.append(s)

        return [s for s in refined if s.strip()]

    def cancel(self):
        """Request cancellation of the current generation task."""
        self.cancel_requested = True

    def synthesize(
        self,
        text: str,
        speaker: str = "NF",
        speed: float = 1.0,
        noise_scale: float = 0.55,
        noise_scale_w: float = 0.7,
        sdp_ratio: float = 0.25,
        pause_duration: float = 0.15,
        on_progress: Optional[Callable[[int, int, str], None]] = None
    ) -> Optional[Tuple[np.ndarray, int]]:
        """
        Synthesize text using the multi-speaker model.
        Chunks long texts automatically for best prosody and responsiveness.
        """
        if not self.tts:
            raise RuntimeError("TTS model is not loaded yet")

        self.cancel_requested = False
        sentences = self.split_sentences(text)
        total = len(sentences)
        
        if total == 0:
            return None

        audio_chunks = []
        sample_rate = 24000
        silence = np.zeros(int(sample_rate * pause_duration), dtype=np.float32)

        for idx, sentence in enumerate(sentences, start=1):
            if self.cancel_requested:
                print("[TTSEngine] Synthesis cancelled by user")
                return None

            if on_progress:
                on_progress(idx, total, f"Đang đọc câu {idx}/{total}: {sentence[:35]}...")

            try:
                chunk, sr = self.tts.synthesize(
                    sentence,
                    speaker=speaker,
                    speed=speed,
                    noise_scale=noise_scale,
                    noise_scale_w=noise_scale_w,
                    sdp_ratio=sdp_ratio
                )
                sample_rate = sr
                audio_chunks.append(chunk)
                if idx < total:
                    audio_chunks.append(silence)
            except Exception as e:
                print(f"[TTSEngine] Error synthesizing chunk '{sentence}': {e}")
                continue

        if not audio_chunks:
            return None

        full_audio = np.concatenate(audio_chunks)
        return full_audio, sample_rate

    def clone_voice(
        self,
        text: str,
        reference_audio_path: str,
        reference_text: Optional[str] = None,
        speed: float = 1.0,
        pause_duration: float = 0.15,
        on_progress: Optional[Callable[[int, int, str], None]] = None
    ) -> Optional[Tuple[np.ndarray, int]]:
        """
        Synthesize text using zero-shot voice cloning from reference audio.
        """
        if not self.load_zeroshot_model(lambda msg: on_progress(0, 1, msg) if on_progress else None):
            raise RuntimeError("Could not load Zero-Shot voice cloning model")

        self.cancel_requested = False
        sentences = self.split_sentences(text)
        total = len(sentences)

        if total == 0:
            return None

        audio_chunks = []
        sample_rate = 24000
        silence = np.zeros(int(sample_rate * pause_duration), dtype=np.float32)

        for idx, sentence in enumerate(sentences, start=1):
            if self.cancel_requested:
                print("[TTSEngine] Voice cloning cancelled by user")
                return None

            if on_progress:
                on_progress(idx, total, f"Đang nhân bản giọng đọc câu {idx}/{total}...")

            try:
                chunk, sr = self.zeroshot_tts.synthesize(
                    text=sentence,
                    reference_audio=reference_audio_path,
                    reference_text=reference_text
                )
                sample_rate = sr
                audio_chunks.append(chunk)
                if idx < total:
                    audio_chunks.append(silence)
            except Exception as e:
                print(f"[TTSEngine] Error cloning voice for chunk '{sentence}': {e}")
                continue

        if not audio_chunks:
            return None

        full_audio = np.concatenate(audio_chunks)
        return full_audio, sample_rate

    @staticmethod
    def save_audio(audio: np.ndarray, sample_rate: int, output_path: str) -> str:
        """Save numpy audio array to file."""
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(out), audio, sample_rate)
        return str(out)
