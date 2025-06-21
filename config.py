import re
from os import getenv
from dotenv import load_dotenv
from pyrogram import filters

load_dotenv()

# --- API Credentials ---
API_ID = int(getenv("API_ID"))
API_HASH = getenv("API_HASH")
BOT_TOKEN = getenv("BOT_TOKEN")

# --- Database ---
MONGO_DB_URI = getenv("MONGO_DB_URI", None)

# --- YouTube / YTDL / Proxy ---
YTPROXY_URL = getenv("YTPROXY_URL", 'https://tgapi.xbitcode.com')
YT_API_KEY = getenv("YT_API_KEY", None)

# --- Limits ---
DURATION_LIMIT = int(getenv("DURATION_LIMIT", 14400))  # in seconds
VIDEO_DURATION_LIMIT = int(getenv("VIDEO_DURATION_LIMIT", 14400))

# --- Logger ---
LOGGER_ID = int(getenv("LOGGER_ID", -1002715747653))

# --- Ownership ---
OWNER_ID = int(getenv("OWNER_ID", 6221699441))
SUDO_USERS = list(map(int, getenv("SUDO_USERS", str(OWNER_ID)).split()))

# --- Heroku (optional) ---
HEROKU_APP_NAME = getenv("HEROKU_APP_NAME")
HEROKU_API_KEY = getenv("HEROKU_API_KEY")

# --- GitHub Auto-Updater ---
UPSTREAM_REPO = getenv("UPSTREAM_REPO", "https://github.com/strad-dev131/TeamXmusic2.0")
UPSTREAM_BRANCH = getenv("UPSTREAM_BRANCH", "main")
GIT_TOKEN = getenv("GIT_TOKEN", None)

# --- Support Links ---
SUPPORT_CHANNEL = getenv("SUPPORT_CHANNEL", "https://t.me/TeamXUpdate")
SUPPORT_CHAT = getenv("SUPPORT_CHAT", "https://t.me/TeamsXchat")

# Validate links
if SUPPORT_CHANNEL and not re.match(r"(?:http|https)://", SUPPORT_CHANNEL):
    raise SystemExit("[ERROR] - SUPPORT_CHANNEL must start with https://")
if SUPPORT_CHAT and not re.match(r"(?:http|https)://", SUPPORT_CHAT):
    raise SystemExit("[ERROR] - SUPPORT_CHAT must start with https://")

# --- Assistant Auto-Leave ---
AUTO_LEAVING_ASSISTANT = bool(getenv("AUTO_LEAVING_ASSISTANT", True))
ASSISTANT_LEAVE_TIME = int(getenv("ASSISTANT_LEAVE_TIME", 6400))

# --- Spotify Integration ---
SPOTIFY_CLIENT_ID = getenv("SPOTIFY_CLIENT_ID", "1c21247d714244ddbb09925dac565aed")
SPOTIFY_CLIENT_SECRET = getenv("SPOTIFY_CLIENT_SECRET", "709e1a2969664491b58200860623ef19")

# --- Playlist Fetch Limits ---
PLAYLIST_FETCH_LIMIT = int(getenv("PLAYLIST_FETCH_LIMIT", 25))

# --- File Upload Limits ---
TG_AUDIO_FILESIZE_LIMIT = int(getenv("TG_AUDIO_FILESIZE_LIMIT", 52428800))
TG_VIDEO_FILESIZE_LIMIT = int(getenv("TG_VIDEO_FILESIZE_LIMIT", 2097152099999))

# --- Pyrogram Session Strings ---
STRING1 = getenv("STRING_SESSION", None)
STRING2 = getenv("STRING_SESSION2", None)
STRING3 = getenv("STRING_SESSION3", None)
STRING4 = getenv("STRING_SESSION4", None)
STRING5 = getenv("STRING_SESSION5", None)

# --- Filters and State Holders ---
BANNED_USERS = filters.user()
adminlist = {}
lyrical = {}
votemode = {}
confirmer = {}

# --- Auto Clean & Cache ---
CACHE_DURATION = 3600  # 1 hour
CACHE_SLEEP = 300      # every 5 minutes
file_cache = {}
autoclean = set()

# --- Optional UI Image URLs ---
START_IMG_URL = [
    "https://files.catbox.moe/uxcm48.jpg",
    "https://files.catbox.moe/uxcm48.jpg",
    "https://files.catbox.moe/uxcm48.jpg",
]
PING_IMG_URL = getenv("PING_IMG_URL", "https://files.catbox.moe/uxcm48.jpg")
PLAYLIST_IMG_URL = "https://files.catbox.moe/uxcm48.jpg"
STATS_IMG_URL = "https://files.catbox.moe/pguloz.jpg"
TELEGRAM_AUDIO_URL = "https://files.catbox.moe/timwpo.jpg"
TELEGRAM_VIDEO_URL = "https://files.catbox.moe/timwpo.jpg"
STREAM_IMG_URL = "https://files.catbox.moe/timwpo.jpg"
SOUNCLOUD_IMG_URL = "https://graph.org/file/c95a687e777b55be1c792.jpg"
YOUTUBE_IMG_URL = "https://graph.org/file/e8730fdece86a1166f608.jpg"
SPOTIFY_ARTIST_IMG_URL = "https://strad-dev131.github.io/TeamXsrc/img/sp_artist.jpg"
SPOTIFY_ALBUM_IMG_URL = "https://strad-dev131.github.io/TeamXsrc/img/sp_album.jpg"
SPOTIFY_PLAYLIST_IMG_URL = "https://strad-dev131.github.io/TeamXsrc/img/sp_playlist.jpg"

# --- Private Bot Memory Mode (Optional) ---
PRIVATE_BOT_MODE_MEM = int(getenv("PRIVATE_BOT_MODE_MEM", 5))
