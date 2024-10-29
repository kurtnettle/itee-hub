import argparse
from asyncio import run
from urllib.parse import urlparse

from aiogram import Bot

from itee_hub import LOGGER, TELEGRAM_BOT_TOKEN, db
from itee_hub.link_extractors import extract_result_table_links, extract_table_links
from itee_hub.telegram_bot import TelegramBot
from itee_hub.utils import download, get_web_page_soup, get_year_from_txt

FE_QUES_URL = "https://itpec.org/pastexamqa/fe.html"
IP_QUES_URL = "https://itpec.org/pastexamqa/ip.html"
RESULTS_URL = "https://itpec.org/statsandresults/all-passers.html"


def update_questions(link, refresh_file=False):
    soup = get_web_page_soup(link)
    links = extract_table_links(link, soup)

    for i in links:
        year_month = i[0]
        file_link = i[1]

        file_name = urlparse(file_link).path
        year = get_year_from_txt(file_name)
        if not year:
            LOGGER.error("failed to parse year from: %s", i)
            continue

        try:
            download(
                path_suffix=f"{year}/questions",
                link=file_link,
                year_month=year_month,
                refresh_file=refresh_file,
            )
        except Exception as err:
            LOGGER.error("failed to download: %s reason: %s", file_link, err)


def update_results(link, refresh_file=False):
    soup = get_web_page_soup(link)
    links = extract_result_table_links(link, soup)

    for year, links in links.items():
        for i in links:
            year_month = i[0]
            country = i[1]
            file_link = i[2]
            try:
                download(
                    path_suffix=f"{year}/results",
                    link=file_link,
                    year_month=year_month,
                    file_name_suffix=country,
                    refresh_file=refresh_file,
                )
            except Exception as err:
                LOGGER.error("failed to download: %s reason: %s", file_link, err)


async def main():
    parser = argparse.ArgumentParser(description="ITEE Hub")

    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Refresh the files by redownloading them.",
    )
    parser.add_argument(
        "--update-questions", action="store_true", help="Update the FE and IP questions"
    )
    parser.add_argument(
        "--update-results", action="store_true", help="Update exam results"
    )
    parser.add_argument(
        "--update-telegram", type=str, help="Post updates in telegram chat"
    )

    args = parser.parse_args()

    refresh_file = args.refresh is True

    if args.update_questions:
        update_questions(FE_QUES_URL, refresh_file)
        update_questions(IP_QUES_URL, refresh_file)

    if args.update_results:
        update_results(RESULTS_URL, refresh_file)

    if args.update_telegram:
        async with Bot(token=TELEGRAM_BOT_TOKEN) as bot:
            bot = TelegramBot(db=db, bot=bot)
            await bot.update(args.update_telegram)


if __name__ == "__main__":
    run(main())
