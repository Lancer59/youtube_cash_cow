"""
tests/test_upload.py
--------------------
Live integration test for the YouTube upload pipeline.
This hits the REAL YouTube API — it will consume quota and create an actual video.

Usage (from the youtube_cash_cow/ directory):
    python tests/test_upload.py                     # scheduled (private → public tomorrow 18:00 UTC)
    python tests/test_upload.py --public            # upload as public immediately
    python tests/test_upload.py --dry-run           # validate everything EXCEPT the actual API call

Requirements:
    - token.pickle must exist (run main.py once to authenticate), OR
    - client_secrets.json must exist (OAuth flow will open in browser on first run)
    - The video file below must exist on disk
"""

import sys
import os
import argparse
from datetime import datetime, timezone, timedelta

# ---------------------------------------------------------------------------
# Allow imports from the parent directory (youtube_cash_cow/)
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logger
from uploader import upload_video, next_publish_time, get_youtube_client

# ---------------------------------------------------------------------------
# Test configuration — edit these as needed
# ---------------------------------------------------------------------------
TEST_VIDEO_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "output", "final_20260621_180830_captioned.mp4"
)

TEST_TITLE       = "[TEST] History Short Upload Check"
TEST_DESCRIPTION = "This is an automated upload test. #Shorts #History #Test"
TEST_TAGS        = ["test", "history", "shorts", "automation", "upload"]
# ---------------------------------------------------------------------------


def print_separator():
    logger.info("─" * 60)


def validate_environment():
    """Check all prerequisites before touching the API."""
    print_separator()
    logger.info("PRE-FLIGHT CHECKS")
    print_separator()

    all_ok = True

    # 1. Video file
    if os.path.exists(TEST_VIDEO_PATH):
        size_mb = os.path.getsize(TEST_VIDEO_PATH) / (1024 * 1024)
        logger.success(f"Video file found: {TEST_VIDEO_PATH} ({size_mb:.1f} MB)")
    else:
        logger.error(f"Video file NOT found: {TEST_VIDEO_PATH}")
        all_ok = False

    # 2. Credentials
    token_file   = "token.pickle"
    secrets_file = os.getenv("YOUTUBE_CLIENT_SECRETS", "client_secrets.json")

    if os.path.exists(token_file):
        logger.success(f"Token file found: {token_file}")
    else:
        logger.warning(f"No token file at '{token_file}' — OAuth browser flow will be triggered")

    if os.path.exists(secrets_file):
        logger.success(f"Client secrets found: {secrets_file}")
    else:
        logger.error(
            f"Client secrets NOT found: '{secrets_file}'. "
            "Download from Google Cloud Console → APIs & Services → Credentials."
        )
        all_ok = False

    # 3. GROQ_API_KEY is not needed for upload, but warn if missing
    if not os.getenv("GROQ_API_KEY"):
        logger.warning("GROQ_API_KEY not set (not needed for upload test, just FYI)")

    print_separator()
    return all_ok


def test_auth_only():
    """Verify OAuth credentials are valid without uploading anything."""
    print_separator()
    logger.info("AUTH CHECK — verifying credentials (no upload)")
    print_separator()
    try:
        youtube = get_youtube_client()
        logger.success("YouTube client built successfully — credentials are valid")
        return True
    except FileNotFoundError as e:
        logger.error(str(e))
        return False
    except Exception as e:
        logger.error(f"Auth failed: {e}")
        return False


def test_upload(public: bool = False):
    """Run the actual upload with the test video."""
    publish_at = None if public else next_publish_time(hour=18)

    print_separator()
    if public:
        logger.info("UPLOAD TEST — mode: PUBLIC (live immediately)")
    else:
        logger.info(
            f"UPLOAD TEST — mode: SCHEDULED PRIVATE "
            f"(goes public at {publish_at.strftime('%Y-%m-%d %H:%M:%S UTC')})"
        )
    print_separator()

    start = datetime.now(timezone.utc)

    video_id = upload_video(
        video_path=TEST_VIDEO_PATH,
        title=TEST_TITLE,
        description=TEST_DESCRIPTION,
        tags=TEST_TAGS,
        publish_at=publish_at,
    )

    elapsed = (datetime.now(timezone.utc) - start).total_seconds()

    print_separator()
    if video_id:
        logger.success(f"TEST PASSED in {elapsed:.1f}s")
        logger.success(f"Video ID : {video_id}")
        logger.success(f"URL      : https://youtube.com/shorts/{video_id}")
        if publish_at:
            logger.info(
                f"Scheduled: private until "
                f"{publish_at.strftime('%Y-%m-%d %H:%M:%S UTC')}"
            )
        else:
            logger.success("Status: PUBLIC — check your YouTube Studio now")
    else:
        logger.error(f"TEST FAILED after {elapsed:.1f}s — upload_video returned None")
        logger.info("Check the log output above for the specific error")
    print_separator()

    return video_id is not None


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Live YouTube upload test for youtube_cash_cow"
    )
    parser.add_argument(
        "--public",
        action="store_true",
        help="Upload as public immediately (default: scheduled private)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run pre-flight checks and auth only — no upload"
    )
    args = parser.parse_args()

    logger.banner()
    logger.info("YouTube Upload Integration Test")

    # Step 1: Pre-flight
    env_ok = validate_environment()
    if not env_ok:
        logger.error("Pre-flight failed — fix the errors above before uploading")
        sys.exit(1)

    # Step 2: Auth check
    auth_ok = test_auth_only()
    if not auth_ok:
        logger.error("Auth check failed — cannot proceed")
        sys.exit(1)

    # Step 3: Upload (unless --dry-run)
    if args.dry_run:
        logger.success("DRY RUN complete — all checks passed, no upload performed")
        sys.exit(0)

    success = test_upload(public=args.public)
    sys.exit(0 if success else 1)
