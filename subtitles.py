"""
subtitles.py
Transcribes voiceover and burns captions into the video.

Two subtitle styles, controlled by config.json → mode → upgraded_subtitles:

  Classic  (upgraded_subtitles: false)
    - Word-by-word pop-in, white text, black stroke

  Upgraded (upgraded_subtitles: true)  ← Mode 3 style, works for ALL modes
    - 2-3 word chunks, one chunk at a time (no overlap)
    - Chunks alternate between white and yellow so color always changes
    - Single TextClip per chunk — no pixel math, no overlapping, no crashes
"""

import whisper
import os
from moviepy import VideoFileClip, TextClip, CompositeVideoClip
import logger
from config import get, subtitle_style, upgraded_subtitles


# ---------------------------------------------------------------------------
# Transcription (shared)
# ---------------------------------------------------------------------------

def transcribe(voiceover_path: str) -> list:
    """Run Whisper word-level transcription. Returns list of word dicts."""
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


# ---------------------------------------------------------------------------
# Classic subtitle renderer
# ---------------------------------------------------------------------------

def _burn_classic(video: VideoFileClip, words: list, cfg: dict) -> CompositeVideoClip:
    """Word-by-word white captions — original pipeline style."""
    clips = [video]

    for w in words:
        duration = (w["end"] - w["start"]) - 0.01
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

    return CompositeVideoClip(clips)


# ---------------------------------------------------------------------------
# Upgraded subtitle renderer (Mode 3 style)
# ---------------------------------------------------------------------------

def _group_into_chunks(words: list, words_per_chunk: int) -> list:
    """Group word-level timestamps into N-word chunks."""
    chunks = []
    for i in range(0, len(words), words_per_chunk):
        group = words[i:i + words_per_chunk]
        chunks.append({
            "text":  " ".join(w["word"] for w in group),
            "start": group[0]["start"],
            "end":   group[-1]["end"],
        })
    return chunks


def _burn_upgraded(video: VideoFileClip, words: list, cfg: dict) -> CompositeVideoClip:
    """
    One TextClip per chunk. Wraps long lines. No overlaps. No crashes.

    - method="caption" + size=(VIDEO_W, None) → MoviePy wraps text that is
      wider than the frame onto a second line automatically.
    - duration trimmed by 0.01s to prevent adjacent chunks sharing a frame.
    - Color cycles: white → yellow → cyan → yellow → white ...
    """
    clips = [video]
    words_per_chunk = cfg.get("words_per_chunk", 3)
    chunks = _group_into_chunks(words, words_per_chunk)

    VIDEO_W         = video.w
    pos_y           = cfg["position_y"]
    font_size       = cfg["font_size"]
    highlight_color = cfg.get("highlight_color", "yellow")
    base_color      = cfg.get("base_color", "white")
    stroke_color    = cfg.get("stroke_color", "black")
    stroke_width    = cfg.get("stroke_width", 4)
    font_path       = cfg["font_path"]

    color_cycle = [base_color, highlight_color, "cyan", highlight_color]

    for idx, chunk in enumerate(chunks):
        duration = (chunk["end"] - chunk["start"]) - 0.01
        if duration <= 0:
            continue

        color = color_cycle[idx % len(color_cycle)]

        try:
            clip = (
                TextClip(
                    text=chunk["text"],
                    font_size=font_size,
                    font=font_path,
                    color=color,
                    stroke_color=stroke_color,
                    stroke_width=stroke_width,
                    method="caption",        # ← wraps onto next line if too wide
                    size=(VIDEO_W, None),    # ← max width = full frame width
                    text_align="center",
                )
                .with_start(chunk["start"])
                .with_duration(duration)
                .with_position(("center", pos_y), relative=True)
            )
            clips.append(clip)

        except Exception as e:
            logger.warning(f"Subtitle chunk '{chunk['text']}' failed ({e}), skipping.")

    return CompositeVideoClip(clips)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def burn_subtitles(video_path: str, words: list, output_path: str = None) -> str:
    """
    Burn captions into video_path.
    Automatically uses Classic or Upgraded style based on config.
    """
    cfg = subtitle_style()

    if not cfg.get("enabled", True):
        logger.warning("Subtitles disabled in config, skipping.")
        return video_path

    if output_path is None:
        base, ext = os.path.splitext(video_path)
        output_path = f"{base}_captioned{ext}"

    video = VideoFileClip(video_path)

    if upgraded_subtitles():
        logger.info("Using upgraded subtitle style (chunked alternating color)...")
        final = _burn_upgraded(video, words, cfg)
    else:
        logger.info("Using classic subtitle style (word-by-word)...")
        final = _burn_classic(video, words, cfg)

    logger.info("Rendering captioned video...")
    final.write_videofile(output_path, fps=30, codec="libx264", audio_codec="aac", logger=None)
    logger.success(f"Captioned video → {output_path}")
    return output_path


if __name__ == "__main__":
    words = transcribe("output/voiceover.wav")
    burn_subtitles("output/final_test.mp4", words)
