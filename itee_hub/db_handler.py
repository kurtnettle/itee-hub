import sqlite3

TAG = "DB"


class DBHandler:
    def __init__(self, logger, db_file):
        self.logger = logger
        self.db_file = db_file
        self.connect()

    def connect(self):
        try:
            self.logger.info("[%s] opening database", TAG)
            self.conn = sqlite3.connect(self.db_file)
            self.cur = self.conn.cursor()
        except sqlite3.OperationalError as error:
            self.logger.error("[%s] error in DB connection: %s", TAG, error)

    def commit(self):
        try:
            self.conn.commit()
        except sqlite3.OperationalError as e:
            self.logger.info("[%s] operational error during commit: %s", TAG, e)
        except sqlite3.IntegrityError as e:
            self.logger.info("[%s] integrity error during commit: %s", TAG, e)
        except sqlite3.Error as e:
            self.logger.info("[%s] unknown error during commit: %s", TAG, e)

    def init_db(self):
        self.cur.execute(
            """
            CREATE TABLE IF NOT EXISTS files(
                link TEXT,
                last_modified TEXT,
                md5 TEXT,
                year_month TEXT
            )
            """
        )

        self.commit()

    def add_file(self, link: str, last_modified: str, year_month: str, md5: str):
        self.cur.execute(
            """
            INSERT INTO files(
               link,  last_modified,  md5, year_month
            ) 
            VALUES 
            (
              :link, :last_modified, :md5, :year_month
            )
            """,
            {
                "link": link,
                "last_modified": last_modified,
                "md5": md5,
                "year_month": year_month,
            },
        )

    def get_file(self, link: str, last_modified: str, md5: str = None) -> list:
        self.cur.execute(
            """
            SELECT *
            FROM files
            WHERE (link == :link) AND (md5 == :md5 OR last_modified == :last_modified)
            """,
            {"link": link, "last_modified": last_modified, "md5": md5},
        )

        result = self.cur.fetchall()
        if result:
            return result

    def __del__(self):
        self.logger.info("[%s] closing database", TAG)
        if self.conn:
            self.commit()
            self.conn.close()
