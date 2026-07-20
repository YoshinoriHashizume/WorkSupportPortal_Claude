"""互換用。本番・開発の切替は DJANGO_SETTINGS_MODULE を使う。"""

from config.settings.base import load_dotenv
from config.settings.development import *  # noqa: F401,F403
