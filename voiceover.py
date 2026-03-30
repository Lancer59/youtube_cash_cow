"""
voiceover.py
Converts script text to a WAV voiceover using Kokoro ONNX (free, local, sounds great).
"""

import os
import soundfile as sf
import logger
from config import get


def generate_voiceover(script: str, output_path: str = "output/voiceover.wav"):
    os.makedirs("output", exist_ok=True)
    cfg = get()["voiceover"]

    try:
        from kokoro_onnx import Kokoro
    except ImportError:
        logger.error("kokoro-onnx not installed. Run: pip install kokoro-onnx soundfile")
        raise

    logger.info(f"Loading Kokoro TTS model ({cfg['model_file']})...")
    kokoro = Kokoro(cfg["model_file"], cfg["voices_file"])

    logger.info(f"Synthesizing speech — voice: {cfg['voice']}, speed: {cfg['speed']}x...")
    samples, sample_rate = kokoro.create(
        script,
        voice=cfg["voice"],
        speed=cfg["speed"],
        lang=cfg["lang"]
    )

    sf.write(output_path, samples, sample_rate)
    logger.success(f"Voiceover saved → {output_path}")
    return output_path


if __name__ == "__main__":
    test = "Did you know that ancient Romans used crushed mouse brains as toothpaste? Follow for more history facts!"
    generate_voiceover(test)
