import logging
import os
from pathlib import Path

from itee_hub.db_handler import DBHandler

logging.basicConfig(
    format="%(asctime)s - %(levelname)s: %(message)s",
    handlers=[logging.FileHandler("itee_hub.log"), logging.StreamHandler()],
    level=logging.INFO,
)

LOGGER = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

data_dir = Path.cwd() / "data"
data_dir.mkdir(parents=True, exist_ok=True)

db_file = data_dir / "data.db"
db = DBHandler(LOGGER, db_file)
db.init_db()
