from TeamXmusic.core.bot import Siddu
from TeamXmusic.core.dir import dirr
from TeamXmusic.core.git import git
from TeamXmusic.core.userbot import Userbot
from TeamXmusic.misc import dbb, heroku

from .logging import LOGGER

dirr()
git()
dbb()
heroku()

app = Siddu()
userbot = Userbot()


from .platforms import *

Apple = AppleAPI()
Carbon = CarbonAPI()
SoundCloud = SoundAPI()
Spotify = SpotifyAPI()
Resso = RessoAPI()
Telegram = TeleAPI()
YouTube = YouTubeAPI()
