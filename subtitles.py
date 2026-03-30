"""
subtitles.py
Uses OpenAI Whisper (local, free) to transcribe the voiceover
and burns word-by-word captions into the video.
"""

import whisper
import os
from moviepy import VideoFileClip, TextClip, CompositeVideoClip
import logger
from config import get


def transcribe(voiceover_path: str):
    cfg = get()["subtitles"]
    logger.info(f"Loading Whisper model ({cfg['whisper_model']})...")
    model = whisper.load_model(cfg["whisper_model"])
    logger.info("Running transcription...")
    result = model.transcribe(voiceover_path, word_timestamps=True)

    words = []
    for segment in result["segments"]:
        for w in segment.get("words", []):
            words.append({
                "word": w["word"].strip().upper(),
                "start": w["start"],
                "end": w["end"]
            })
    return words


def burn_subtitles(video_path: str, words: list, output_path: str = None):
    cfg = get()["subtitles"]

    if not cfg["enabled"]:
        logger.warning("Subtitles disabled in config, skipping.")
        return video_path

    if output_path is None:
        base, ext = os.path.splitext(video_path)
        output_path = f"{base}_captioned{ext}"

    video = VideoFileClip(video_path)
    clips = [video]

    for w in words:
        duration = w["end"] - w["start"]
        if duration <= 0:
            continue

        txt = (
            TextClip(
                text=w["word"],
                font_size=cfg["font_size"],
                font=cfg["font_path"],
                color=cfg["color"],
                stroke_color=cfg["stroke_color"],
                stroke_width=cfg["stroke_width"],
                method="label"
            )
            .with_start(w["start"])
            .with_duration(duration)
            .with_position(("center", cfg["position_y"]), relative=True)
        )
        clips.append(txt)

    final = CompositeVideoClip(clips)
    logger.info("Rendering captioned video...")
    final.write_videofile(output_path, fps=30, codec="libx264", audio_codec="aac", logger=None)
    logger.success(f"Captioned video → {output_path}")
    return output_path


if __name__ == "__main__":
    words = transcribe("output/voiceover.wav")
    burn_subtitles("output/final_test.mp4", words)
