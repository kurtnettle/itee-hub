from pathlib import Path
from urllib.parse import urljoin, urlparse

from itee_hub import LOGGER
from itee_hub.utils import get_year_from_txt

TAG = "extractors"


def is_valid_file_url(url: str):
    """
    Checks if the provided file URL is valid.

    A valid file URL must contain a path with a suffix (file extension).

    Args:
        url (str): The file URL to validate.

    Returns:
        bool: True if the URL is valid, else False.
    """

    url_parts = urlparse(url)
    if not Path(url_parts.path).suffix:
        return False
    return True


def extract_table_links(base_url, soup):
    """
    Extracts zip links from the past FE,IP question table.

    This function retrieves year-month information and corresponding zip file links 
    from the given HTML table, with proper url validation performed.

    Args:
        base_url (str): The base URL to resolve relative links.
        soup (BeautifulSoup): A BeautifulSoup object containing the parsed HTML of the page

    Returns:
        List[Tuple[str, str]]: A sorted list of tuples where each tuple contains the year-month 
            text and the corresponding valid zip file link.
            Returns an empty list if no valid links are found.
    """

    links = set()
    rows = soup.select("table>tr")

    for row in rows:
        if row.select_one("td>span"):
            continue

        year_month = row.select_one("td>div")
        zip_link = row.select_one("td > div > a[href]")

        if not zip_link:
            LOGGER.info("[%s] zip_link elem not found in: %s", TAG, row)
            continue

        if not year_month:
            LOGGER.info("[%s] zip_link elem not found in: %s", TAG, row)
            continue

        year_month_text = year_month.get_text(strip=True)
        zip_link = urljoin(base_url, zip_link["href"])

        if not is_valid_file_url(zip_link):
            LOGGER.info("[%s] invalid file url: %s", TAG, zip_link)
            continue

        links.add((year_month_text, zip_link))

    return sorted(links)


def extract_result_table_links(base_url, soup):
    """
    Extracts file links from the passers information table.

    This function retrieves year-month information, country names, and corresponding zip file links 
    from the result HTML table.

    Args:
        base_url (str): The base URL to resolve relative links.
        soup (BeautifulSoup): A BeautifulSoup object containing the parsed HTML of the page.

    Returns:
        Dict[int, List[Tuple[str, str, str]]]: A dictionary where each key is a year (int), 
            and the value is a list of tuples. Each tuple contains:
                - year-month text (str)
                - country name (str)
                - corresponding valid zip file link (str).
            Returns an empty dictionary if no valid links are found.
    """

    links = {}
    table = soup.select_one("table")
    if not table:
        LOGGER.error("[%s] No result table found.", TAG)
        return links

    country = ""
    for tr in table.find_all("tr"):
        if not tr.select_one("td > div"):
            continue
        if tr.select_one("td[colspan='4']"):
            country = tr.select_one("td[colspan='4']").get_text(strip=True)
            continue

        year_month_element = tr.select_one("td:nth-of-type(1) > div[align=left]")
        if not year_month_element:
            LOGGER.error("[%s] Failed to parse year from: '%s'", TAG, tr)
            continue

        year_month_text = year_month_element.get_text(strip=True)

        zip_links = []
        for i in range(2, 5):
            result_link = tr.select_one(f"td:nth-of-type({i}) > div > a[href]")
            if result_link and result_link.get("href"):
                zip_link = (
                    year_month_text,
                    country,
                    urljoin(base_url, result_link["href"]),
                )
                zip_links.append(zip_link)

        result_year = get_year_from_txt(year_month_text)
        if result_year is None:
            LOGGER.error("[%s] Failed to parse year from: '%s'", TAG, year_month_text)
            continue

        links.setdefault(result_year, []).extend(zip_links)

    return links
