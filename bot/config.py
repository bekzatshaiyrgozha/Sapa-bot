import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:password@localhost:5432/sapa_bot")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
USE_WEBHOOK = os.getenv("USE_WEBHOOK", "false").lower() == "true"
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# Other settings
DOWNLOADS_DIR = os.getenv("DOWNLOADS_DIR", ".downloads")