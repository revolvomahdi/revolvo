# Automation/uploader/config.py
# Configuration settings for the YouTube Uploader module.

from pathlib import Path

# --- Upload Scheduling (disabled, videos will be uploaded instantly as private) ---

START_HOUR = 10  # Not used
INTERVAL_MINUTES = 30  # Not used
DAILY_VIDEO_LIMIT = 20

# --- Channel Configuration ---

UPLOADER_DIR = Path(__file__).parent

CHANNEL_CONFIGS = {
    "en": {
        "channel_name": "Revolvo English",
        "token_file": str(UPLOADER_DIR / "token_en.pickle")
    },
    "de": {
        "channel_name": "Revolvo Deutsch",
        "token_file": str(UPLOADER_DIR / "token_de.pickle")
    },
    "fr": {
        "channel_name": "Revolvo Français",
        "token_file": str(UPLOADER_DIR / "token_fr.pickle")
    },
    "es": {
        "channel_name": "Revolvo Español",
        "token_file": str(UPLOADER_DIR / "token_es.pickle")
    },
    "ru": {
        "channel_name": "Revolvo Русский",
        "token_file": str(UPLOADER_DIR / "token_ru.pickle")
    },
    "it": {
        "channel_name": "Revolvo Italiano",
        "token_file": str(UPLOADER_DIR / "token_it.pickle")
    },
    "tr": {
        "channel_name": "Revolvo Türkçe",
        "token_file": str(UPLOADER_DIR / "token_tr.pickle")
    }
}
