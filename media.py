"""
media.py
Handles video assembly for all three modes.

Each mode block in config.json has a "video_source" field:
  "dynamic" — fetch/stream clips from Pexels API at runtime
  "static"  — use a local video file (looped to match voiceover length)

Mode 0 dynamic  → Pexels stock clips matched to script keywords
Mode 0 static   → loop a local file (e.g. a pre-downloaded b-roll pack)
Mode 1 dynamic  → Pexels gameplay-style search ("minecraft parkour", etc.)
Mode 1 static   → loop a local gameplay file
Mode 2 dynamic  → same as mode 1 dynamic
Mode 2 static   → loop a local gameplay file
"""

import os
import requests
from datetime import datetime
from dotenv import load_dotenv
from moviepy import VideoFileClip, AudioFileClip, concatenate_videoclips
import logger
from config import get, mode_config, active_mode

load_dotenv()
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")

# Keywords used when fetching dynamic clips for modes that don't have
# script-generated keywords (modes 1 & 2 with video_source = "dynamic")
_GAMEPLAY_SEARCH_KEYWORDS = ["minecraft parkour", "subway surfers", "satisfying gameplay"]


# ---------------------------------------------------------------------------
# Public entry point — called by main.py for all modes
# ---------------------------------------------------------------------------

def get_background_clips(voiceover_path: str, keywords: list = None) -> list:
    """
    Returns a list of clip paths to use as the video background.

    Reads video_source from the active mode's config block:
      "dynamic" → fetch from Pexels (uses keywords if provided, else gameplay defaults)
      "static"  → loop the local static_video_path to match voiceover length

    Args:
        voiceover_path: path to the generated voiceover WAV, used to get duration for static loops.
        keywords: list of search keywords (passed in for mode 0 dynamic; ignored for static).
    """
    mcfg = mode_config()
    video_source = mcfg.get("video_source", "static")

    if video_source == "dynamic":
        search_keywords = keywords if keywords else _GAMEPLAY_SEARCH_KEYWORDS
        logger.info(f"Video source: dynamic — fetching from Pexels (keywords: {search_keywords})")
        return fetch_clips(search_keywords)

    elif video_source == "static":
        static_path = mcfg.get("static_video_path", "assets/gameplay.mp4")
        logger.info(f"Video source: static — using local file: {static_path}")
        audio_duration = AudioFileClip(voiceover_path).duration
        loop_path = _loop_static_video(static_path, audio_duration)
        return [loop_path]

    else:
        raise ValueError(
            f"Unknown video_source '{video_source}' in config. "
            "Must be 'dynamic' or 'static'."
        )


# ---------------------------------------------------------------------------
# Dynamic — Pexels stock footage
# ---------------------------------------------------------------------------

def fetch_clips(keywords: list) -> list:
    """Download portrait stock clips from Pexels matching the given keywords."""
    cfg = get()["video"]
    total_duration = cfg["target_duration"]
    per_page = mode_config().get("clips_per_keyword", 5)

    os.makedirs("output/clips", exist_ok=True)
    downloaded = []

    for keyword in keywords:
        if sum(c[1] for c in downloaded) >= total_duration:
            break

        url = "https://api.pexels.com/videos/search"
        headers = {"Authorization": PEXELS_API_KEY}
        params = {"query": keyword, "per_page": per_page, "orientation": "portrait"}

        res = requests.get(url, headers=headers, params=params)
        if res.status_code != 200:
            logger.warning(f"Pexels API error {res.status_code} for keyword '{keyword}', skipping.")
            continue

        videos = res.json().get("videos", [])

        for video in videos:
            if sum(c[1] for c in downloaded) >= total_duration:
                break

            duration = video.get("duration", 0)
            if duration < 3:
                continue

            files = sorted(video["video_files"], key=lambda x: x.get("width", 0), reverse=True)
            video_url = files[0]["link"]

            logger.info(f"Downloading clip {video['id']} ({duration}s)...")
            path = f"output/clips/{video['id']}.mp4"
            if not os.path.exists(path):
                r = requests.get(video_url, stream=True)
                with open(path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)

            downloaded.append((path, duration))

    if not downloaded:
        raise RuntimeError(
            "No clips downloaded from Pexels. "
            "Check your PEXELS_API_KEY and keywords."
        )

    return [c[0] for c in downloaded]


# ---------------------------------------------------------------------------
# Static — loop a local video file to match voiceover duration
# ---------------------------------------------------------------------------

def _loop_static_video(video_path: str, target_duration: float) -> str:
    """
    Loop video_path until it covers target_duration seconds.
    Returns path to the looped output clip in output/clips/.
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(
            f"Static video not found at: {video_path}\n"
            "Download a free looping clip (Minecraft, Subway Surfers, b-roll, etc.) from:\n"
            "  https://pixabay.com/videos/search/minecraft%20gameplay/\n"
            "  https://pixabay.com/videos/search/subway%20surfers/\n"
            f"Then place it at: {video_path}\n"
            "Or update 'static_video_path' in config.json for the active mode."
        )

    os.makedirs("output/clips", exist_ok=True)
    # Use a stable name so re-runs for the same mode reuse the loop
    safe_name = os.path.splitext(os.path.basename(video_path))[0]
    out_path = f"output/clips/{safe_name}_loop.mp4"

    logger.info(f"Looping '{video_path}' to {target_duration:.1f}s...")
    clip = VideoFileClip(video_path).without_audio()

    clips = []
    total = 0.0
    while total < target_duration:
        clips.append(clip)
        total += clip.duration

    looped = concatenate_videoclips(clips)
    looped = looped.subclipped(0, target_duration)
    looped.write_videofile(out_path, fps=get()["video"]["fps"], codec="libx264", logger=None)
    logger.success(f"Static loop ready → {out_path}")
    return out_path


# ---------------------------------------------------------------------------
# Shared assembly — same for all modes
# ---------------------------------------------------------------------------

def assemble_video(clip_paths: list, voiceover_path: str, output_path: str = None) -> str:
    """
    Resize, crop, concatenate clip_paths and overlay voiceover_path as audio.
    Trims final video to voiceover duration.
    """
    cfg = get()["video"]
    VIDEO_W = cfg["width"]
    VIDEO_H = cfg["height"]
    FPS = cfg["fps"]

    os.makedirs("output", exist_ok=True)
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"output/final_{timestamp}.mp4"

    clips = []
    for path in clip_paths:
        clip = VideoFileClip(path).without_audio()
        clip = clip.resized(height=VIDEO_H)
        if clip.w < VIDEO_W:
            clip = clip.resized(width=VIDEO_W)
        clip = clip.cropped(x_center=clip.w / 2, y_center=clip.h / 2, width=VIDEO_W, height=VIDEO_H)
        clips.append(clip)

    audio = AudioFileClip(voiceover_path)
    total_duration = audio.duration

    video = concatenate_videoclips(clips, method="compose")
    video = video.subclipped(0, min(total_duration, video.duration))
    video = video.with_audio(audio)

    video.write_videofile(output_path, fps=FPS, codec="libx264", audio_codec="aac", logger=None)
    logger.success(f"Video saved → {output_path}")
    return output_path


if __name__ == "__main__":
    mode = active_mode()
    test_keywords = ["ancient rome", "history", "war"] if mode == 0 else None
    paths = get_background_clips("output/voiceover.wav", keywords=test_keywords)
    assemble_video(paths, "output/voiceover.wav")
