"""
main.py
Runs the full pipeline. Mode is controlled by config.json → mode → active:

  0 = Stock Footage  — Pexels clips + history narration  (original)
  1 = Reddit Story   — r/TIFU/AITA scrape + gameplay background
  2 = Did You Know   — LLM shocking facts + gameplay background

Upgraded captions (chunked, yellow highlight) are applied to ALL modes
when config.json → mode → upgraded_subtitles is true.
"""

import schedule
import time
import logger
from config import get, active_mode, mode_config, upgraded_subtitles
from voiceover import generate_voiceover
from subtitles import transcribe, burn_subtitles
from uploader import upload_video, next_publish_time


def run_pipeline():
    logger.banner()
    mode = active_mode()
    TOTAL_STEPS = 6

    logger.info(f"Active mode: {mode}  |  Upgraded subtitles: {upgraded_subtitles()}")

    # ------------------------------------------------------------------
    # Step 1: Generate script (mode-dependent)
    # ------------------------------------------------------------------
    logger.step(1, TOTAL_STEPS, "Generating script...")

    if mode == 0:
        from generator import generate_script
        data = generate_script()

    elif mode == 1:
        from reddit_story import generate_reddit_script
        data = generate_reddit_script()

    elif mode == 2:
        from generator import generate_did_you_know_script
        data = generate_did_you_know_script()

    else:
        raise ValueError(f"Unknown mode {mode}. Set config.json → mode → active to 0, 1, or 2.")

    logger.info(f"Title: {data['title']}")
    logger.success("Script ready")

    # ------------------------------------------------------------------
    # Step 2: Generate voiceover
    # ------------------------------------------------------------------
    logger.step(2, TOTAL_STEPS, "Converting script to voiceover...")
    voiceover_path = generate_voiceover(data["script"])
    logger.success(f"Voiceover saved → {voiceover_path}")

    # ------------------------------------------------------------------
    # Step 3: Get background video
    # ------------------------------------------------------------------
    logger.step(3, TOTAL_STEPS, "Preparing background video...")

    if mode == 0:
        # Pexels stock footage
        from media import fetch_clips, assemble_video
        logger.info(f"Fetching stock footage for keywords: {data['keywords']}")
        clip_paths = fetch_clips(data["keywords"])
        logger.info(f"Downloaded {len(clip_paths)} clip(s)")

    else:
        # Gameplay loop (modes 1 & 2)
        from media import prepare_gameplay_background, assemble_video
        from moviepy import AudioFileClip
        audio_duration = AudioFileClip(voiceover_path).duration
        loop_path = prepare_gameplay_background(audio_duration)
        clip_paths = [loop_path]

    logger.info("Assembling video...")
    from media import assemble_video
    video_path = assemble_video(clip_paths, voiceover_path)
    logger.success(f"Raw video assembled → {video_path}")

    # ------------------------------------------------------------------
    # Step 4: Burn subtitles
    # ------------------------------------------------------------------
    logger.step(4, TOTAL_STEPS, "Transcribing voiceover and burning subtitles...")
    words = transcribe(voiceover_path)
    logger.info(f"Transcribed {len(words)} word(s)")
    video_path = burn_subtitles(video_path, words)
    logger.success(f"Captioned video saved → {video_path}")

    # ------------------------------------------------------------------
    # Step 5: Finalize locally
    # ------------------------------------------------------------------
    logger.step(5, TOTAL_STEPS, "Finalizing...")
    logger.done(video_path)

    # ------------------------------------------------------------------
    # Step 6: Upload to YouTube
    # ------------------------------------------------------------------
    logger.step(6, TOTAL_STEPS, "Uploading to YouTube...")

    run_mode = get()["scheduler"].get("run_mode", "scheduled")

    if run_mode == "continuous":
        # Continuous mode → publish immediately as public, no scheduling
        publish_time = None
        logger.info("Continuous mode — uploading as PUBLIC immediately")
    else:
        # Scheduled mode → set future publish time
        publish_time = next_publish_time(hour=get()["scheduler"]["publish_hour_utc"])
        logger.info(f"Scheduled mode — video will go public at {publish_time.strftime('%Y-%m-%d %H:%M UTC')}")

    video_id = upload_video(
        video_path=video_path,
        title=data["title"],
        description=data["description"],
        tags=data["tags"],
        publish_at=publish_time
    )

    if video_id:
        logger.success(f"Pipeline fully complete — video live at https://youtube.com/shorts/{video_id}")
    else:
        logger.error("Upload failed — video saved locally but NOT published to YouTube")
        logger.info(f"Manual upload path: {video_path}")



if __name__ == "__main__":
    cfg = get()["scheduler"]
    run_mode = cfg.get("run_mode", "scheduled")

    if run_mode == "continuous":
        # Run back-to-back with no gap — as fast as the pipeline completes
        logger.info("Run mode: CONTINUOUS — generating videos back-to-back. Press Ctrl+C to stop.")
        while True:
            try:
                run_pipeline()
            except Exception as e:
                logger.error(f"Pipeline failed: {e} — waiting 60s before retrying...")
                time.sleep(60)

    else:
        # Scheduled mode — run immediately then repeat every N hours
        run_pipeline()
        interval = cfg.get("run_every_hours", 24)
        schedule.every(interval).hours.do(run_pipeline)
        logger.info(f"Run mode: SCHEDULED — next run in {interval}h. Press Ctrl+C to stop.")
        while True:
            schedule.run_pending()
            time.sleep(60)
