import re
from datetime import datetime, timezone
from time import sleep

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import FSInputFile

from itee_hub import LOGGER
from itee_hub.utils import get_file_path_from_link_info, get_info_from_link

TAG = "Telegram"


class TelegramBot:
    def __init__(self, bot, db):
        self.bot = bot
        self.db = db
        self.init_db()

    def init_db(self):
        self.db.cur.execute(
            """
            CREATE TABLE IF NOT EXISTS telegram_msgs(
                chat_id TEXT,
                md5 TEXT
            )
            """
        )
        self.db.commit()

    def get_pendings(self, chat_id: str) -> list:
        """
        Retrieves a list of pending files that have not been sent in the specified chat.

        Args:
            chat_id (str): The chat ID to check for pending files.

        Returns:
            list: A list of tuples, each tuple containing the 
                link, last modified timestamp, MD5 hash, year-month 
                of the pending files then ordered by  
                the last modified time in ascending order.
        """        

        self.db.cur.execute(
            """
            SELECT f.link, f.last_modified, f.md5, f.year_month
            FROM files AS f
            LEFT JOIN telegram_msgs AS msg ON f.md5 = msg.md5 AND msg.chat_id = :chat_id
            WHERE msg.md5 IS NULL
            ORDER by f.last_modified ASC;
            """,
            {
                "chat_id": chat_id,
            },
        )

        return self.db.cur.fetchall()

    def add_record(self, chat_id: str, md5: str):
        self.db.cur.execute(
            """
            INSERT INTO telegram_msgs(
               chat_id,  md5
            ) 
            VALUES 
            (
              :chat_id, :md5
            )
            """,
            {"chat_id": chat_id, "md5": md5},
        )

    def prepare_msg(self, record: tuple):
        """
        Prepares a formatted message and file path from a record tuple.

        Generates a formatted message, including a link to the file and tags for 
        categorization. It also retrieves the file path based on the link information.

        Args:
            record (tuple): A tuple containing the file link, last modified timestamp, 
                            MD5 hash, and year-month associated with the file.

        Returns:
            tuple: A tuple containing:
                - str: The formatted message with an HTML link to the file, last modified 
                    information, and associated tags.
                - Path: The file path derived from the link information.
        """

        link = record[0]
        last_modified = datetime.fromtimestamp(int(record[1]), tz=timezone.utc)

        year_month_text = record[3]

        link_info = get_info_from_link(link)
        file_path = get_file_path_from_link_info(link_info)

        link_type = link_info["type"].capitalize()
        exam_level = link_info["level"].upper()
        tags = f'#{exam_level} #{exam_level}_{link_info["year"]}'

        exam_session = re.search((r"(\d{4}[AS])"), file_path.name, re.IGNORECASE)
        if exam_session:
            exam_session = exam_session.group(1)
            tags += f" #{exam_level}_{exam_session}"

        tags += f" #{link_info['type']}"

        if link_info.get("country"):
            tags += f' #{link_info["country"]}'
            msg = f"{link_type} of {link_info['country']}'s"
        else:
            msg = f"{link_type} of"

        msg = f"<a href='{link}'>{msg} {exam_level} {year_month_text}</a>"
        msg += f"\n<b>last modified: </b> {last_modified}"
        msg += f"\n\n{tags}"

        return (msg, file_path)

    async def update(self, chat_id):
        pending_files = self.get_pendings(chat_id)

        if not pending_files:
            LOGGER.info("[%s] found no pending files.", TAG)
            return

        LOGGER.info("[%s] found %s pending files.", TAG, len(pending_files))

        for i in pending_files:
            prepared_msg = self.prepare_msg(i)
            try:
                await self.bot.send_document(
                    chat_id=chat_id,
                    caption=prepared_msg[0],
                    document=FSInputFile(prepared_msg[1]),
                    parse_mode="HTML",
                )
                self.add_record(chat_id=chat_id, md5=i[2])
                LOGGER.info("[%s] [%s] sent '%s'", TAG, chat_id, prepared_msg[1].name)
            except TelegramBadRequest:
                LOGGER.info(
                    "[%s] [%s] failed to send message. (%s)", TAG, chat_id, prepared_msg
                )

            sleep(3)  # 20msgs ~ 60s
